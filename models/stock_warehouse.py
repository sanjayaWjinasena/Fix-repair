# -*- coding: utf-8 -*-
from odoo import api, models


# Known per-company defaults for the Factory Repair Location. The first
# entry whose name fragment appears (case-insensitive) in company.name
# wins. Keep this list small and additive — operators can always override
# the seeded value via Settings → Technical → System Parameters.
FACTORY_LOCATION_DEFAULTS = [
    ('Jinasena Agricultural Machinery', 'PW-JM'),
]


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    @api.model
    def _seed_intransit_warehouses(self):
        """For every non-intransit warehouse on every company, ensure a
        paired intransit warehouse exists. Idempotent: skips any source
        whose suffix already resolves to an IT-/IW-/IB- companion.
        Safe to run on every module upgrade.
        """
        skip_prefixes = ('IT-', 'IW-', 'IB-')
        for wh in self.sudo().search([]):
            if not wh.code or wh.code.startswith(skip_prefixes):
                continue
            wh._ensure_intransit_warehouse()

    @api.model
    def _seed_factory_repair_locations(self):
        """Populate ir.config_parameter
        'fix_repair.factory_repair_location.<company_id>' for every
        company with a known default warehouse. Idempotent — skips any
        company whose parameter is already set, so manual overrides are
        preserved across module upgrades.
        """
        Param = self.env['ir.config_parameter'].sudo()
        Wh = self.env['stock.warehouse'].sudo()
        for company in self.env['res.company'].sudo().search([]):
            key = f'fix_repair.factory_repair_location.{company.id}'
            if Param.get_param(key):
                continue
            wh_code = next(
                (code for frag, code in FACTORY_LOCATION_DEFAULTS
                 if frag.lower() in (company.name or '').lower()),
                None,
            )
            if not wh_code:
                continue
            wh = Wh.search([
                ('code', '=', wh_code),
                ('company_id', '=', company.id),
            ], limit=1)
            if wh and wh.lot_stock_id:
                Param.set_param(key, str(wh.lot_stock_id.id))

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
        new_wh = Wh.create({
            'name': f'In-transit – {self.name}',
            'code': code,
            'company_id': self.company_id.id,
        })
        # Standard warehouse creation gives us an internal-usage Stock
        # location. Convert it to a proper Transit location so reports
        # don't count in-flight items as on-hand inventory.
        if new_wh.lot_stock_id:
            new_wh.lot_stock_id.sudo().write({
                'name': 'Intransit',
                'usage': 'transit',
            })
        return new_wh
