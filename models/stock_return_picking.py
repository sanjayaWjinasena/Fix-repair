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

            # When opened from a repair ticket:
            #   - Lock quantity to 1 (repairs are single-item)
            #   - Hide the To Refund column (we force it False in _create_returns)
            for qty_field in arch.xpath(
                "//field[@name='product_return_moves']//field[@name='quantity']"
            ):
                qty_field.set('readonly', 'ticket_id')

            for refund_field in arch.xpath(
                "//field[@name='product_return_moves']//field[@name='to_refund']"
            ):
                refund_field.set('column_invisible', '1')

        return arch, view

    @api.depends('picking_id', 'ticket_id')
    def _compute_moves_locations(self):
        # Run the full chain (product_return_moves, original_location_id, etc.)
        super()._compute_moves_locations()
        for wizard in self:
            # Override location_id to the Studio-defined suggested repair location.
            # x_studio_suggested_location_id_1 = ticket.x_studio_virtual_location_1 (company 2)
            # x_studio_suggested_location_id   = ticket.x_studio_virtual_location   (company 1)
            # The Studio automation (id 174) validates location_id against these fields —
            # setting them here ensures we pass validation and land on the correct bin.
            # Must be done inside the compute — writing location_id anywhere else
            # triggers a forced re-run of this same compute (Odoo re-syncs all
            # co-computed fields), which would undo the change.
            suggested = (
                wizard.x_studio_suggested_location_id_1
                or wizard.x_studio_suggested_location_id
                or wizard.original_location_id
            )
            if suggested:
                wizard.location_id = suggested

            # Repair tickets are always single-item — cap return qty to 1.
            if wizard.ticket_id:
                for line in wizard.product_return_moves:
                    if line.quantity != 1:
                        line.quantity = 1

    def _create_returns(self):
        new_picking_id, pick_type_id = super()._create_returns()
        if self.ticket_id:
            # Decouple return moves from the original SO line so the SO's
            # delivered qty is not reduced (repair ≠ commercial return).
            new_picking = self.env['stock.picking'].browse(new_picking_id)
            new_picking.move_ids.write({
                'to_refund': False,
                'sale_line_id': False,
            })
        return new_picking_id, pick_type_id
