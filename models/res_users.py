# -*- coding: utf-8 -*-
"""res.users Studio field declarations moved to
`studio_usermodel_migration` (v0.0.7). This file retains only the
`_migrate_studio_res_users_cluster_to_base` one-shot migration method
because data/fix_repair_data.xml still calls it via <function>.

The method is idempotent -- flips `state='manual' -> 'base'` on the
4 location fields (which now live in SUM). If SUM has already
completed that migration, the search returns nothing and the call
is a no-op. Safe to run on any DB.
"""
from odoo import api, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def _migrate_studio_res_users_cluster_to_base(self):
        """Flip state='manual'->'base' + unlink studio_customization
        pins for the 4 x_studio_* location fields on res.users.
        Idempotent; data preserved. Method stays here for backwards-
        compat with data/fix_repair_data.xml which invokes it as a
        <function>. Actual fields are now declared in
        studio_usermodel_migration.
        """
        cluster = [
            'x_studio_source_location',
            'x_studio_source_location_1',
            'x_studio_virtual_location',
            'x_studio_virtual_location_1',
        ]
        Field = self.env['ir.model.fields'].sudo()
        rows = Field.search([
            ('model', '=', 'res.users'),
            ('name', 'in', cluster),
        ])
        manual_rows = rows.filtered(lambda f: f.state == 'manual')
        if manual_rows:
            manual_rows.write({'state': 'base'})

        ModelData = self.env['ir.model.data'].sudo()
        studio_pins = ModelData.search([
            ('model', '=', 'ir.model.fields'),
            ('res_id', 'in', rows.ids),
            ('module', '=', 'studio_customization'),
        ])
        if studio_pins:
            studio_pins.unlink()
