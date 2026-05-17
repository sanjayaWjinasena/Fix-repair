# -*- coding: utf-8 -*-
from odoo import models


class ProjectTask(models.Model):
    _inherit = 'project.task'

    def action_create_sale_order(self):
        """Keep the generated sale order as a quotation (draft) until manually confirmed.

        Standard industry_fsm_sale auto-confirms the SO right after creation.
        We let super() build all the SO lines, then reset the order back to
        draft so it sits as a quotation — the customer can review it, and the
        user confirms it manually to start the actual sale order.
        """
        result = super().action_create_sale_order()
        for task in self:
            so = task.sale_order_id
            if so and so.state == 'sale':
                so.with_context(disable_cancel_warning=True).action_cancel()
                so.action_draft()
        return result
