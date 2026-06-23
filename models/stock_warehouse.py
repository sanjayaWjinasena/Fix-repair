# -*- coding: utf-8 -*-
from odoo import fields, models


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    intransit_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='In-transit Warehouse',
        domain="[('company_id', '=', company_id), ('id', '!=', id)]",
        help="Companion warehouse used as the intermediate hop for "
             "send/receive transfers in the repair flow. Auto-created on "
             "first use when blank.",
    )

    def _ensure_intransit_warehouse(self):
        """Return self.intransit_warehouse_id, auto-creating a paired
        IT-<suffix> warehouse when blank.

        Code is capped at the stock.warehouse 5-char limit. Falls back to
        a sequence-style IT### code if the natural suffix is taken.
        """
        self.ensure_one()
        if self.intransit_warehouse_id:
            return self.intransit_warehouse_id

        Wh = self.env['stock.warehouse'].sudo()
        suffix = (self.code or '')[-2:].upper() or 'XX'
        code = f'IT-{suffix}'
        if Wh.search_count([('code', '=', code)]):
            i = 1
            while Wh.search_count([('code', '=', f'IT{i:03d}')]):
                i += 1
            code = f'IT{i:03d}'

        new_wh = Wh.create({
            'name': f'In-transit – {self.name}',
            'code': code,
            'company_id': self.company_id.id,
        })
        self.sudo().write({'intransit_warehouse_id': new_wh.id})
        return new_wh
