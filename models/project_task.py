# -*- coding: utf-8 -*-
from lxml import etree
from odoo import api, fields, models
from odoo.addons.industry_fsm_sale.models.project_task import Task as FsmSaleTask


class ProjectTask(models.Model):
    _inherit = 'project.task'

    # Mirrors the linked helpdesk ticket's repair stage so form-view invisible
    # conditions on this model can reference it without a custom computed field.
    ticket_repair_stage_state = fields.Selection(
        related='helpdesk_ticket_id.repair_stage_state',
        string='Ticket Repair Stage',
        store=False,
    )

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            # Secondary "Mark as done" button:
            # Studio (view 4620) requires x_studio_valid_invoiced_so=True, which
            # blocks the button on all repair tasks (SO is not yet invoiced at this
            # stage). For Repair tasks we replace that condition: show only when the
            # linked ticket is at 'Repair Completed'; for all other task types keep
            # the original invoice/delivery check.
            for btn in arch.xpath(
                "//button[@name='action_fsm_validate'][contains(@class,'btn-secondary')]"
            ):
                btn.set('invisible',
                    "not display_mark_as_done_secondary or "
                    "(x_studio_quotation_type == 'Repair' and "
                    " ticket_repair_stage_state != 'repair_completed') or "
                    "(x_studio_quotation_type != 'Repair' and "
                    " (x_studio_incomplete_delivery_available or not x_studio_valid_invoiced_so))"
                )
            # Ensure the related field is loaded in the view
            for sheet in arch.xpath("//sheet"):
                fld = etree.SubElement(sheet, 'field')
                fld.set('name', 'ticket_repair_stage_state')
                fld.set('invisible', '1')
                break
        return arch, view

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
                self.sale_order_id.sudo().write({'x_studio_quotation_type': 'Repair'})
        return self.sale_order_id

    def _fsm_create_sale_order(self):
        """Delegate to industry_fsm_sale's implementation, skipping industry_fsm_stock."""
        FsmSaleTask._fsm_create_sale_order(self)
