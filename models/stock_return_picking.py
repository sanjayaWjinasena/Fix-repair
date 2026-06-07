# -*- coding: utf-8 -*-
from odoo import api, models


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        # When opened from a repair ticket that has a serial number but no
        # pre-selected delivery (New stage, not-under-warranty flow), look up
        # the outgoing delivery that shipped that serial to the customer and
        # pre-populate picking_id and sale_order_id so the user only needs to
        # confirm instead of manually searching.
        ticket_id = defaults.get('ticket_id') or self.env.context.get('default_ticket_id')
        if ticket_id and not defaults.get('picking_id'):
            ticket = self.env['helpdesk.ticket'].browse(ticket_id)
            serial = ticket.x_studio_serial_no
            if serial and serial.product_id:
                cust_locs = self.env['stock.location'].sudo().search(
                    [('usage', '=', 'customer')]
                )
                move_line = self.env['stock.move.line'].sudo().search([
                    ('product_id', '=', serial.product_id.id),
                    ('lot_id', '=', serial.id),
                    ('picking_code', '=', 'outgoing'),
                    ('location_dest_id', 'in', cust_locs.ids),
                    ('state', '=', 'done'),
                ], limit=1, order='date desc')
                if move_line:
                    defaults['picking_id'] = move_line.picking_id.id
                    so = (
                        move_line.move_id.sale_line_id.order_id
                        or self.env['sale.order'].sudo().search(
                            [('name', '=', move_line.origin)], limit=1
                        )
                    )
                    if so:
                        defaults['sale_order_id'] = so.id
        return defaults

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

            # Hide the To Refund column — forced False in _create_returns anyway.
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
        if self.ticket_id:
            # Repair tickets are single-item — enforce qty=1 before creating
            # the return. Done here rather than readonly in the view to avoid
            # the One2many submission dropping the required quantity value.
            self.product_return_moves.write({'quantity': 1})
        new_picking_id, pick_type_id = super()._create_returns()
        if self.ticket_id:
            new_picking = self.env['stock.picking'].browse(new_picking_id)
            # Decouple return moves from the original SO line so the SO's
            # delivered qty is not reduced (repair ≠ commercial return).
            new_picking.move_ids.write({
                'to_refund': False,
                'sale_line_id': False,
            })
            # The return wizard copies the lot from the original delivery, which
            # may differ from the serial number the customer is actually handing
            # back (e.g. the SO delivered BR-EK-0106 but the ticket is for
            # BR-EK-0104). Override the lot on all move lines to match the
            # serial number explicitly selected on the repair ticket.
            serial = self.ticket_id.x_studio_serial_no
            if serial:
                new_picking.move_line_ids.write({'lot_id': serial.id})
        return new_picking_id, pick_type_id
