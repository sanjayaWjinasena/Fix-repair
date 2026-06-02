# -*- coding: utf-8 -*-
from lxml import etree
from odoo import api, fields, models
from odoo.addons.industry_fsm_sale.models.project_task import Task as FsmSaleTask


class ProjectTask(models.Model):
    _inherit = 'project.task'

    # Mirrors the linked ticket's repair_stage_state so it can be used in
    # view invisible expressions without a full related-model traversal.
    ticket_repair_stage_state = fields.Char(
        compute='_compute_ticket_repair_stage_state',
    )

    def _compute_ticket_repair_stage_state(self):
        for task in self:
            task.ticket_repair_stage_state = (
                task.helpdesk_ticket_id.repair_stage_state or ''
            ) if task.helpdesk_ticket_id else ''

    def _fsm_ensure_sale_order(self):
        """Create the SO if absent, then return it — without confirming.

        industry_fsm_stock overrides this method and calls action_confirm()
        immediately so stock reservations can be made. We bypass that by
        recreating the create-only logic from industry_fsm_sale directly,
        leaving the SO in draft (Quotation) until the user confirms manually.
        """
        if not self.sale_order_id:
            self._fsm_create_sale_order()
            if self.helpdesk_ticket_id and self.sale_order_id:
                ticket = self.helpdesk_ticket_id
                qtype = ('Not Under Warranty'
                         if ticket.x_studio_normal_repair_with_serial_no
                         else 'Repair')
                self.sale_order_id.sudo().write({'x_studio_quotation_type': qtype})
        return self.sale_order_id

    def _fsm_create_sale_order(self):
        """Delegate to industry_fsm_sale's implementation, skipping industry_fsm_stock."""
        FsmSaleTask._fsm_create_sale_order(self)

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            # Inject ticket_repair_stage_state as invisible so it is
            # available in button invisible expressions below.
            targets = arch.xpath("//sheet") or arch.xpath("//form")
            if targets:
                field_el = etree.Element('field')
                field_el.set('name', 'ticket_repair_stage_state')
                field_el.set('invisible', '1')
                targets[0].insert(0, field_el)

            # Mark as Done: only show for repair tickets when the repair is
            # complete (ticket at Repair Completed). Non-repair FSM tasks have
            # no helpdesk_ticket_id so the guard is False and they show normally.
            repair_guard = (
                "helpdesk_ticket_id and "
                "ticket_repair_stage_state != 'repair_completed'"
            )
            for btn in arch.xpath(
                "//button[@name='action_fsm_validate'][@class='btn-primary']"
            ):
                existing = btn.get('invisible', 'False')
                btn.set('invisible', f"({existing}) or ({repair_guard})")

            # Secondary: also remove Studio's over-restrictive Repair/Credit conditions
            for btn in arch.xpath(
                "//button[@name='action_fsm_validate'][@class='btn-secondary']"
            ):
                btn.set('invisible',
                    f"not display_mark_as_done_secondary or ({repair_guard})")

        return arch, view
