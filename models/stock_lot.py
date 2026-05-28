# -*- coding: utf-8 -*-
from odoo import fields, models


class StockLot(models.Model):
    _inherit = 'stock.lot'

    # Virtual field — not stored, but has a _search so it works in domains.
    # True when the lot has at least one done outgoing move line on a sale order.
    is_issued = fields.Boolean(
        compute='_compute_is_issued',
        search='_search_is_issued',
    )

    def _compute_is_issued(self):
        issued = set(
            self.env['stock.move.line'].sudo().search([
                ('lot_id', 'in', self.ids),
                ('state', '=', 'done'),
                ('picking_id.sale_id', '!=', False),
            ]).mapped('lot_id').ids
        )
        for lot in self:
            lot.is_issued = lot.id in issued

    def _search_is_issued(self, operator, value):
        issued_ids = list(set(
            self.env['stock.move.line'].sudo().search([
                ('state', '=', 'done'),
                ('picking_id.sale_id', '!=', False),
            ]).mapped('lot_id').ids
        ))
        if (operator == '=' and value) or (operator == '!=' and not value):
            return [('id', 'in', issued_ids)]
        return [('id', 'not in', issued_ids)]
