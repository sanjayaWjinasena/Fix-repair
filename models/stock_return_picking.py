# -*- coding: utf-8 -*-
from odoo import api, models


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        ticket_id = defaults.get('ticket_id') or self.env.context.get('default_ticket_id')
        if not ticket_id or defaults.get('picking_id'):
            return defaults

        ticket = self.env['helpdesk.ticket'].browse(ticket_id)
        serial = ticket.x_studio_serial_no

        if ticket.x_studio_normal_repair_without_serial_no:
            # Without Serial No: no historical delivery exists to reverse.
            # Create a new outgoing picking (Repair Location → Customer, validated)
            # as a "Delivery to Return" so the wizard has a done picking to reverse
            # into the collection picking (incoming: Customer → Repair Location).
            if serial and ticket.product_id:
                repair_loc = ticket.x_studio_virtual_location_1 or ticket.x_studio_virtual_location
                cust_loc = self.env['stock.location'].sudo().search(
                    [('usage', '=', 'customer')], limit=1
                )
                pick_type_out = self.env['stock.picking.type'].sudo().search([
                    ('code', '=', 'outgoing'),
                    ('company_id', '=', ticket.company_id.id),
                ], order='sequence asc', limit=1)
                if repair_loc and cust_loc and pick_type_out:
                    new_picking = self.env['stock.picking'].sudo().create({
                        'partner_id': ticket.partner_id.id,
                        'picking_type_id': pick_type_out.id,
                        'location_id': repair_loc.id,
                        'location_dest_id': cust_loc.id,
                        'company_id': ticket.company_id.id,
                        'move_ids': [(0, 0, {
                            'name': ticket.product_id.display_name,
                            'product_id': ticket.product_id.id,
                            'product_uom_qty': 1.0,
                            'product_uom': ticket.product_id.uom_id.id,
                            'location_id': repair_loc.id,
                            'location_dest_id': cust_loc.id,
                        })],
                    })
                    new_picking.action_confirm()
                    if not new_picking.move_line_ids:
                        self.env['stock.move.line'].sudo().create({
                            'picking_id': new_picking.id,
                            'move_id': new_picking.move_ids[0].id,
                            'product_id': ticket.product_id.id,
                            'product_uom_id': ticket.product_id.uom_id.id,
                            'lot_id': serial.id,
                            'qty_done': 1.0,
                            'location_id': repair_loc.id,
                            'location_dest_id': cust_loc.id,
                        })
                    else:
                        new_picking.move_line_ids.write({
                            'lot_id': serial.id,
                            'qty_done': 1.0,
                        })
                    new_picking.with_context(cancel_backorder=True)._action_done()
                    defaults['picking_id'] = new_picking.id
        elif serial and serial.product_id:
            # With Serial No: look up the existing outgoing delivery for this serial.
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
            ticket_id = self.env.context.get('default_ticket_id')
            is_without_serial_no = False
            if ticket_id:
                ticket = self.env['helpdesk.ticket'].sudo().browse(ticket_id)
                is_without_serial_no = bool(ticket.x_studio_normal_repair_without_serial_no)

            for field in arch.xpath("//field[@name='sale_order_id']"):
                if is_without_serial_no:
                    # No sale order exists for this flow — hide the field entirely.
                    field.set('invisible', '1')
                else:
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
            # Enforce qty=1 before creating the return.
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
            # Override lot to match the serial on the repair ticket — the wizard
            # copies the lot from the original delivery, which may differ.
            serial = self.ticket_id.x_studio_serial_no
            if serial:
                new_picking.move_line_ids.write({'lot_id': serial.id})
        return new_picking_id, pick_type_id
