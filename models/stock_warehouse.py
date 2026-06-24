# -*- coding: utf-8 -*-
from odoo import api, models


# Known per-company defaults for the Factory Repair Location. The first
# entry whose name fragment appears (case-insensitive) in company.name
# wins. Keep this list small and additive — operators can always override
# the seeded value via Settings → Fix Repair → Factory Repair Location.
FACTORY_LOCATION_DEFAULTS = [
    ('Jinasena Agricultural Machinery', 'PW-JM'),
]


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    def _ensure_child_location(self, name, usage):
        """Return self's child stock.location with the given name,
        auto-creating one with the given usage under the warehouse view
        location if missing. complete_name follows the <CODE>/<name>
        convention (e.g. PW-JM/Intransit, PW-JM/Repair).
        """
        self.ensure_one()
        Loc = self.env['stock.location'].sudo()
        parent = self.view_location_id
        if not parent:
            return Loc
        existing = Loc.search([
            ('location_id', '=', parent.id),
            ('name', '=', name),
        ], limit=1)
        if existing:
            return existing
        return Loc.create({
            'name': name,
            'usage': usage,
            'location_id': parent.id,
            'company_id': self.company_id.id,
        })

    def _ensure_intransit_location(self):
        return self._ensure_child_location('Intransit', 'transit')

    def _ensure_repair_location(self):
        return self._ensure_child_location('Repair', 'repair')

    @api.model
    def _seed_intransit_locations(self):
        """For every non-intransit warehouse on every company, ensure a
        child Intransit (usage='transit') location exists under its view.
        Idempotent."""
        skip_prefixes = ('IT-', 'IW-', 'IB-')
        for wh in self.sudo().search([]):
            if not wh.code or wh.code.startswith(skip_prefixes):
                continue
            wh._ensure_intransit_location()

    @api.model
    def _seed_repair_locations(self):
        """For every non-intransit warehouse on every company, ensure a
        child Repair (usage='repair') location exists under its view.
        Idempotent."""
        skip_prefixes = ('IT-', 'IW-', 'IB-')
        for wh in self.sudo().search([]):
            if not wh.code or wh.code.startswith(skip_prefixes):
                continue
            wh._ensure_repair_location()

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
