# -*- coding: utf-8 -*-
from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        res = super()._action_done()

        # Collect unique Repair SOs from the pickings just validated
        repair_so_ids = set()
        for picking in self.filtered(lambda p: p.state == 'done' and p.sale_id):
            if picking.sale_id.x_studio_quotation_type == 'Repair':
                repair_so_ids.add(picking.sale_id.id)

        for so in self.env['sale.order'].sudo().browse(list(repair_so_ids)):
            # At least one picking done → Repair Started
            self.env['sale.order']._move_ticket_to_stage(so, 'Repair Started')

            # All pickings for this SO done → Repair Completed
            all_pickings = self.env['stock.picking'].sudo().search(
                [('sale_id', '=', so.id)]
            )
            if all_pickings and all(p.state in ('done', 'cancel') for p in all_pickings):
                self.env['sale.order']._move_ticket_to_stage(so, 'Repair Completed')

        return res
