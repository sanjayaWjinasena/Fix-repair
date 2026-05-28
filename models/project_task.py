# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.addons.industry_fsm_sale.models.project_task import Task as FsmSaleTask


class ProjectTask(models.Model):
    _inherit = 'project.task'

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

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            # Studio added over-restrictive invisible conditions on the secondary
            # Mark as Done button that hide it for Repair/Credit orders even when
            # the repair work is finished. Restore standard FSM visibility only.
            for btn in arch.xpath(
                "//button[@name='action_fsm_validate'][@class='btn-secondary']"
            ):
                btn.set('invisible', "not display_mark_as_done_secondary")
        return arch, view

    def action_fsm_validate(self, stop_running_timers=False):
        res = super().action_fsm_validate(stop_running_timers=stop_running_timers)
        # Move the linked repair ticket to Repair Completed so the
        # "Send to Sales Centre" button becomes visible on the ticket.
        for task in self:
            ticket = task.helpdesk_ticket_id
            if ticket and ticket.x_studio_rug_repair:
                ticket._move_to_stage('Repair Completed')
        return res
