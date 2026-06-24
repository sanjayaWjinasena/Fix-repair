# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Non-stored Many2one backed by ir.config_parameter (per-company key).
    # Compute reads the current company's value; inverse writes it back.
    # No DB column is created on res_config_settings, so the site stays
    # up even if SH skips a module update on the next deploy.
    factory_repair_location_id = fields.Many2one(
        'stock.location',
        string='Factory Repair Location',
        compute='_compute_factory_repair_location_id',
        inverse='_inverse_factory_repair_location_id',
        domain="[('usage', '=', 'internal'), '|', ('company_id', '=', False), ('company_id', 'in', allowed_company_ids)]",
        help="Internal stock location items land at when a repair ticket "
             "reaches 'Received at Factory'. Stored per company under "
             "ir.config_parameter 'fix_repair.factory_repair_location.<company_id>'.",
    )

    @api.depends_context('company')
    def _compute_factory_repair_location_id(self):
        Param = self.env['ir.config_parameter'].sudo()
        key = f'fix_repair.factory_repair_location.{self.env.company.id}'
        raw = Param.get_param(key)
        loc = self.env['stock.location']
        if raw:
            try:
                loc = self.env['stock.location'].sudo().browse(int(raw)).exists()
            except (TypeError, ValueError):
                pass
        for record in self:
            record.factory_repair_location_id = loc

    def _inverse_factory_repair_location_id(self):
        Param = self.env['ir.config_parameter'].sudo()
        key = f'fix_repair.factory_repair_location.{self.env.company.id}'
        for record in self:
            val = (
                str(record.factory_repair_location_id.id)
                if record.factory_repair_location_id else ''
            )
            Param.set_param(key, val)
