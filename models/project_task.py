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
        self._sync_quotation_type()
        return self.sale_order_id

    def _sync_quotation_type(self):
        """Set x_studio_quotation_type on the linked SO based on ticket type.

        Called both when a new SO is created (via _fsm_ensure_sale_order) and
        when an existing SO is linked to the task (write). This ensures the
        type is correct regardless of how the SO was created.
        """
        for task in self:
            if not task.helpdesk_ticket_id or not task.sale_order_id:
                continue
            ticket = task.helpdesk_ticket_id
            qtype = 'Repair' if ticket.x_studio_rug_confirmed else 'Not Under Warranty'
            if task.sale_order_id.x_studio_quotation_type == qtype:
                continue
            if qtype == 'Not Under Warranty':
                self.env['sale.order']._ensure_not_under_warranty_selection()
            task.sale_order_id.sudo().write({'x_studio_quotation_type': qtype})

    def write(self, vals):
        result = super().write(vals)
        if 'sale_order_id' in vals and vals.get('sale_order_id'):
            self._sync_quotation_type()
        # Centre Repair: when the technician marks the FSM task done, advance
        # the linked ticket to "Received at Sales Centre" (repair complete at
        # centre, item ready for dispatch).
        if vals.get('fsm_done'):
            for task in self:
                ticket = task.helpdesk_ticket_id
                if ticket and ticket.x_studio_job_location == 'Centre Repair':
                    ticket._move_to_stage('Received at Sales Centre')
        return result

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

            # New Quotation: not used in the repair workflow — hide entirely.
            for btn in arch.xpath("//button[@name='action_fsm_create_quotation']"):
                btn.set('invisible', '1')

            # Products (material) stat button: for repair tickets only show once
            # both the Repair Diagnosis Validation and Image Validation are present.
            # Non-repair FSM tasks keep their original allow_material condition.
            for btn in arch.xpath("//button[@name='action_fsm_view_material']"):
                existing = btn.get('invisible', '')
                extra = "helpdesk_ticket_id and not (x_studio_valid_diagnosis and x_studio_repair_image_01)"
                btn.set('invisible', f"({existing}) or ({extra})" if existing else extra)

            # Mark as Done: show only at the stage where repair is done.
            # Factory Repair tasks are created at received_at_factory → done at repair_completed.
            # Centre Repair tasks are created at new → done at new (no factory trip).
            # Using stage values directly avoids needing a job_location field on the task.
            # Non-repair tasks have no helpdesk_ticket_id so the guard is False → show normally.
            repair_guard = (
                "helpdesk_ticket_id and "
                "ticket_repair_stage_state not in ('repair_completed', 'new')"
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
