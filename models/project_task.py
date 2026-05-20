# -*- coding: utf-8 -*-
from odoo import models
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
