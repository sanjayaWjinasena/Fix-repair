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

    @api.depends('picking_id', 'ticket_id')
    def _compute_moves_locations(self):
        # Run the full chain (product_return_moves, original_location_id, etc.)
        super()._compute_moves_locations()
        # Override location_id to the Studio-defined suggested repair location.
        # x_studio_suggested_location_id_1 = ticket.x_studio_virtual_location_1 (company 2)
        # x_studio_suggested_location_id   = ticket.x_studio_virtual_location   (company 1)
        # The Studio automation (id 174) validates location_id against these fields —
        # setting them here ensures we pass validation and land on the correct bin.
        # Must be done inside the compute — writing location_id anywhere else
        # triggers a forced re-run of this same compute (Odoo re-syncs all
        # co-computed fields), which would undo the change.
        for wizard in self:
            suggested = (
                wizard.x_studio_suggested_location_id_1
                or wizard.x_studio_suggested_location_id
                or wizard.original_location_id
            )
            if suggested:
                wizard.location_id = suggested
