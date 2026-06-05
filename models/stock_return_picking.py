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

    @api.onchange('picking_id')
    def _onchange_sync_return_location(self):
        # Mirror the Suggested Return Location (picking's source location)
        # into the Return Location field so the user sees a sensible default.
        # Runs after _compute_moves_locations so it overrides the picking-type
        # default_location_return_id that Odoo would otherwise use.
        if self.picking_id and self.picking_id.location_id:
            self.location_id = self.picking_id.location_id
