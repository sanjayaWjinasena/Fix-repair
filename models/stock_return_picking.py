# -*- coding: utf-8 -*-
from odoo import api, models


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            # When opened from a helpdesk ticket at New stage (no picking yet),
            # suitable_sale_order_ids is empty because there are no pickings to
            # derive SOs from.  Replace the domain with a partner_id filter so
            # the user can pick any confirmed/done SO for that customer.
            for field in arch.xpath("//field[@name='sale_order_id']"):
                field.set('domain',
                    "[('partner_id', 'child_of', partner_id), "
                    "('state', 'in', ['sale', 'done'])] "
                    "if partner_id else "
                    "[('state', 'in', ['sale', 'done'])]"
                )
        return arch, view

    @api.model_create_multi
    def create(self, vals_list):
        # After super().create() all stored computes have run, including
        # _compute_moves_locations which sets location_id to the picking
        # type's default_location_return_id.  We override it here so that
        # Return Location matches Suggested Return Location (original_location_id
        # = picking's source location) when the wizard opens with a pre-set picking.
        records = super().create(vals_list)
        for rec in records:
            if rec.original_location_id:
                rec.location_id = rec.original_location_id
        return records

    @api.onchange('picking_id')
    def _onchange_sync_return_location(self):
        # Handles the case where the user changes the Delivery to Return
        # field (or picking_id cascades from a sale_order_id selection).
        if self.picking_id and self.picking_id.location_id:
            self.location_id = self.picking_id.location_id
