# -*- coding: utf-8 -*-
from odoo import models


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    def _ensure_intransit_warehouse(self):
        """Return an intransit warehouse paired with self by code,
        creating an IT-<suffix> one if it doesn't exist yet.

        Reuses existing IW-<suffix> / IB-<suffix> warehouses (Jinasena's
        historical naming) before creating a new IT-<suffix>.
        """
        self.ensure_one()
        Wh = self.env['stock.warehouse'].sudo()
        suffix = (self.code or '')[-2:].upper() or 'XX'

        for candidate in (f'IT-{suffix}', f'IW-{suffix}', f'IB-{suffix}'):
            existing = Wh.search([
                ('code', '=', candidate),
                ('company_id', '=', self.company_id.id),
            ], limit=1)
            if existing:
                return existing

        code = f'IT-{suffix}'
        if Wh.search_count([('code', '=', code)]):
            i = 1
            while Wh.search_count([('code', '=', f'IT{i:03d}')]):
                i += 1
            code = f'IT{i:03d}'
        return Wh.create({
            'name': f'In-transit – {self.name}',
            'code': code,
            'company_id': self.company_id.id,
        })
