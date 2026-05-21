# -*- coding: utf-8 -*-
from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self, cancel_backorder=False):
        res = super()._action_done(cancel_backorder=cancel_backorder)
        for picking in self.filtered(lambda p: p.state == 'done' and p.sale_id):
            if picking.sale_id.x_studio_quotation_type == 'Repair':
                self.env['sale.order']._move_ticket_to_stage(
                    picking.sale_id, 'Repair Started'
                )
        return res
