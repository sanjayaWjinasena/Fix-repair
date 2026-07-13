# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResUsers(models.Model):
    """Studio location fields on res.users migrated to Python.

    helpdesk.ticket.x_studio_source_location / _virtual_location and
    their _1 duplicates are `related='user_id.x_studio_source_location'`
    etc — so these res.users fields are the source of that chain.
    Migrating them completes the location field-graph ownership.
    """
    _inherit = 'res.users'

    x_studio_source_location = fields.Many2one(
        'stock.location',
        string='Source Location',
    )

    # Duplicate slot from an earlier Studio iteration. Kept for schema
    # compatibility (helpdesk.ticket's x_studio_source_location_1
    # related chain walks here).
    x_studio_source_location_1 = fields.Many2one(
        'stock.location',
        string='Source Location',
    )

    x_studio_virtual_location = fields.Many2one(
        'stock.location',
        string='Virtual Location',
    )

    # Duplicate slot (same reason as source_location_1).
    x_studio_virtual_location_1 = fields.Many2one(
        'stock.location',
        string='Virtual Location',
    )

    @api.model
    def _migrate_studio_res_users_cluster_to_base(self):
        """Flip state='manual'→'base' + unlink studio_customization
        pins for the four x_studio_* location fields on res.users.
        Idempotent; data preserved."""
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
