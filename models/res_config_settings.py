# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Non-stored Many2one backed by ir.config_parameter (per-company key).
    # Persistence is driven by get_values / set_values overrides — Save
    # button calls set_values, which writes the current value to
    # ir.config_parameter under fix_repair.factory_repair_location.<company_id>.
    factory_repair_location_id = fields.Many2one(
        'stock.location',
        string='Factory Repair Location',
        domain="[('usage', '=', 'internal'), '|', ('company_id', '=', False), ('company_id', 'in', allowed_company_ids)]",
        help="Internal stock location items land at when a repair ticket "
             "reaches 'Received at Factory'. Stored per company under "
             "ir.config_parameter 'fix_repair.factory_repair_location.<company_id>'.",
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        key = f'fix_repair.factory_repair_location.{self.env.company.id}'
        raw = self.env['ir.config_parameter'].sudo().get_param(key)
        if raw:
            try:
                loc_id = int(raw)
            except (TypeError, ValueError):
                loc_id = False
            if loc_id and self.env['stock.location'].sudo().browse(loc_id).exists():
                res['factory_repair_location_id'] = loc_id
        return res

    def set_values(self):
        super().set_values()
        key = f'fix_repair.factory_repair_location.{self.env.company.id}'
        val = (
            str(self.factory_repair_location_id.id)
            if self.factory_repair_location_id else ''
        )
        self.env['ir.config_parameter'].sudo().set_param(key, val)
