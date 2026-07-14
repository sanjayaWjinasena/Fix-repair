# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


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

    # Two mutually-exclusive super-user permissions read by
    # _super_user_validate below (Studio server action id 2544 native
    # port). Kept as-is from Studio: plain stored booleans, no compute
    # or default, copy=True.
    x_studio_super_user = fields.Boolean(
        string='Super User (All Items)',
        copy=True,
    )
    x_studio_super_user_melt_items = fields.Boolean(
        string='Super User (Melt Items)',
        copy=True,
    )

    def _super_user_validate(self):
        """Studio server action id 2544 native port. Guards that a
        single user cannot hold BOTH x_studio_super_user_melt_items
        and x_studio_super_user permissions simultaneously."""
        for record in self:
            if record.x_studio_super_user_melt_items and record.x_studio_super_user:
                raise UserError(
                    'Both the super user permissions can not be assigned to a single user.'
                )

    @api.model_create_multi
    def create(self, vals_list):
        """Replaces automation 250 'Super User Validate' — create branch."""
        records = super().create(vals_list)
        records._super_user_validate()
        return records

    def write(self, vals):
        """Replaces automation 250 'Super User Validate' — write branch."""
        result = super().write(vals)
        self._super_user_validate()
        return result

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
