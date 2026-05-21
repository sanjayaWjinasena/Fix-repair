# -*- coding: utf-8 -*-
from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def write(self, vals):
        res = super().write(vals)
        if vals.get('state') == 'done':
            for picking in self:
                if not picking.sale_id:
                    continue
                if picking.sale_id.x_studio_quotation_type != 'Repair':
                    continue
                self.env['sale.order']._move_ticket_to_stage(
                    picking.sale_id, 'Repair Started'
                )
        return res
