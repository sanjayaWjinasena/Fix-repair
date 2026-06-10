# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.exceptions import UserError


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        ticket_id = defaults.get('ticket_id') or self.env.context.get('default_ticket_id')
        if not ticket_id or defaults.get('picking_id'):
            return defaults

        ticket = self.env['helpdesk.ticket'].browse(ticket_id)

        if ticket.x_studio_normal_repair_without_serial_no:
            # No historical delivery exists. Leave picking_id empty — the wizard
            # lines will be populated by _compute_moves_locations from the ticket,
            # and _create_returns will build the collection picking directly.
            pass

        elif ticket.x_studio_serial_no and ticket.x_studio_serial_no.product_id:
            # With Serial No / RUG: look up the existing outgoing delivery for
            # this serial and pre-populate the wizard.
            serial = ticket.x_studio_serial_no
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
                    field.set('invisible', '1')
                else:
                    field.set('domain',
                        "[('partner_id', 'child_of', partner_id), "
                        "('state', 'in', ['sale', 'done'])] "
                        "if partner_id else "
                        "[('state', 'in', ['sale', 'done'])]"
                    )

            if is_without_serial_no:
                # No "Delivery to Return" exists for this flow — hide the picking
                # selector so the wizard looks clean.
                for field in arch.xpath("//field[@name='picking_id']"):
                    field.set('invisible', '1')

            # Hide the To Refund column — forced False in _create_returns anyway.
            for refund_field in arch.xpath(
                "//field[@name='product_return_moves']//field[@name='to_refund']"
            ):
                refund_field.set('column_invisible', '1')

        return arch, view

    @api.depends('picking_id', 'ticket_id')
    def _compute_moves_locations(self):
        super()._compute_moves_locations()
        for wizard in self:
            if (not wizard.picking_id
                    and wizard.ticket_id
                    and wizard.ticket_id.x_studio_normal_repair_without_serial_no):
                # super() cleared product_return_moves (no picking). Manually
                # populate one line from the ticket so the wizard shows the product.
                ticket = wizard.ticket_id
                repair_loc = (
                    ticket.x_studio_virtual_location_1
                    or ticket.x_studio_virtual_location
                )
                if ticket.product_id:
                    wizard.product_return_moves = [(0, 0, {
                        'product_id': ticket.product_id.id,
                        'quantity': 1.0,
                        'uom_id': ticket.product_id.uom_id.id,
                        'move_id': False,
                    })]
                if repair_loc:
                    wizard.location_id = repair_loc
                continue

            # For all other tickets (With Serial No / RUG): override location_id
            # to the Studio-defined suggested repair location.
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
        if (self.ticket_id
                and self.ticket_id.x_studio_normal_repair_without_serial_no
                and not self.picking_id):
            # Without Serial No: no "Delivery to Return" exists. Create the
            # collection picking directly (incoming: Customer → Repair Loc).
            # A fresh serial (created via "Create Serial No") has no quants
            # anywhere, so only one positive quant is created (at repair_loc)
            # — the serial constraint never fires.
            ticket = self.ticket_id
            serial = ticket.x_studio_serial_no
            repair_loc = self.location_id
            cust_loc = self.env['stock.location'].sudo().search(
                [('usage', '=', 'customer')], limit=1
            )
            pick_type_in = self.env['stock.picking.type'].sudo().search([
                ('code', '=', 'incoming'),
                ('company_id', '=', ticket.company_id.id),
            ], order='sequence asc', limit=1)
            if not repair_loc or not cust_loc or not pick_type_in:
                raise UserError(
                    "Could not find required repair location or incoming picking type."
                )
            new_picking = self.env['stock.picking'].sudo().create({
                'partner_id': ticket.partner_id.id,
                'picking_type_id': pick_type_in.id,
                'location_id': cust_loc.id,
                'location_dest_id': repair_loc.id,
                'company_id': ticket.company_id.id,
                'move_ids': [(0, 0, {
                    'name': ticket.product_id.display_name,
                    'product_id': ticket.product_id.id,
                    'product_uom_qty': 1.0,
                    'product_uom': ticket.product_id.uom_id.id,
                    'location_id': cust_loc.id,
                    'location_dest_id': repair_loc.id,
                    'to_refund': False,
                })],
            })
            new_picking.action_confirm()
            # Pre-fill the serial on move_lines so the user just clicks Validate.
            if new_picking.move_line_ids:
                if serial:
                    new_picking.move_line_ids.write({'lot_id': serial.id})
            elif serial:
                self.env['stock.move.line'].sudo().create({
                    'picking_id': new_picking.id,
                    'move_id': new_picking.move_ids[0].id,
                    'product_id': ticket.product_id.id,
                    'product_uom_id': ticket.product_id.uom_id.id,
                    'lot_id': serial.id,
                    'location_id': cust_loc.id,
                    'location_dest_id': repair_loc.id,
                })
            return new_picking.id, pick_type_in.id

        # Standard path for With Serial No / RUG.
        if self.ticket_id:
            self.product_return_moves.write({'quantity': 1})
        new_picking_id, pick_type_id = super()._create_returns()
        if self.ticket_id:
            new_picking = self.env['stock.picking'].browse(new_picking_id)
            new_picking.move_ids.write({
                'to_refund': False,
                'sale_line_id': False,
            })
            serial = self.ticket_id.x_studio_serial_no
            if serial:
                new_picking.move_line_ids.write({'lot_id': serial.id})
        return new_picking_id, pick_type_id
