# -*- coding: utf-8 -*-
from odoo import api, fields, models
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
        serial = ticket.x_studio_serial_no

        if ticket.x_studio_normal_repair_without_serial_no:
            # No historical delivery exists. Create a synthetic done outgoing
            # picking (Repair Loc → Customer) by writing state='done' directly —
            # this bypasses _action_done() entirely so no quants are touched and
            # the serial constraint never fires. The wizard uses this as its
            # "Delivery to Return" and reverses it into the collection picking.
            if serial and ticket.product_id:
                repair_loc = (
                    ticket.x_studio_virtual_location_1
                    or ticket.x_studio_virtual_location
                )
                cust_loc = self.env['stock.location'].sudo().search(
                    [('usage', '=', 'customer')], limit=1
                )
                pick_type_out = self.env['stock.picking.type'].sudo().search([
                    ('code', '=', 'outgoing'),
                    ('company_id', '=', ticket.company_id.id),
                ], order='sequence asc', limit=1)
                if repair_loc and cust_loc and pick_type_out:
                    now = fields.Datetime.now()
                    fake_picking = self.env['stock.picking'].sudo().create({
                        'partner_id': ticket.partner_id.id,
                        'picking_type_id': pick_type_out.id,
                        'location_id': repair_loc.id,
                        'location_dest_id': cust_loc.id,
                        'company_id': ticket.company_id.id,
                        'date_done': now,
                    })
                    fake_move = self.env['stock.move'].sudo().create({
                        'name': ticket.product_id.display_name,
                        'product_id': ticket.product_id.id,
                        'product_uom_qty': 1.0,
                        'product_uom': ticket.product_id.uom_id.id,
                        'location_id': repair_loc.id,
                        'location_dest_id': cust_loc.id,
                        'picking_id': fake_picking.id,
                        'company_id': ticket.company_id.id,
                        'date': now,
                        'quantity': 1.0,
                    })
                    self.env['stock.move.line'].sudo().create({
                        'picking_id': fake_picking.id,
                        'move_id': fake_move.id,
                        'product_id': ticket.product_id.id,
                        'product_uom_id': ticket.product_id.uom_id.id,
                        'lot_id': serial.id,
                        'qty_done': 1.0,
                        'location_id': repair_loc.id,
                        'location_dest_id': cust_loc.id,
                        'company_id': ticket.company_id.id,
                    })
                    # Force state to done AFTER creating related records so
                    # _compute_state sees done moves and stays done.
                    fake_move.sudo().write({'state': 'done'})
                    fake_picking.sudo().write({'state': 'done'})
                    defaults['picking_id'] = fake_picking.id

        elif serial:
            # With Serial No / RUG: product may come from the ticket or from
            # the lot itself (Studio automations sometimes clear ticket.product_id).
            product = ticket.product_id or serial.product_id
            cust_locs = self.env['stock.location'].sudo().search(
                [('usage', '=', 'customer')]
            )
            move_line = False
            if product:
                move_line = self.env['stock.move.line'].sudo().search([
                    ('product_id', '=', product.id),
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
            elif product:
                # No historical delivery found (e.g. item sold outside this
                # system). Create a synthetic done outgoing picking so the
                # wizard has something to reverse — same approach as the
                # Without Serial No flow.
                repair_loc = (
                    ticket.x_studio_virtual_location_1
                    or ticket.x_studio_virtual_location
                )
                if not repair_loc:
                    warehouse = self.env['stock.warehouse'].sudo().search(
                        [('company_id', '=', ticket.company_id.id)], limit=1
                    )
                    repair_loc = warehouse.lot_stock_id if warehouse else False
                cust_loc = cust_locs[:1]
                pick_type_out = self.env['stock.picking.type'].sudo().search([
                    ('code', '=', 'outgoing'),
                    ('company_id', '=', ticket.company_id.id),
                ], order='sequence asc', limit=1)
                if repair_loc and cust_loc and pick_type_out:
                    now = fields.Datetime.now()
                    fake_picking = self.env['stock.picking'].sudo().create({
                        'partner_id': ticket.partner_id.id,
                        'picking_type_id': pick_type_out.id,
                        'location_id': repair_loc.id,
                        'location_dest_id': cust_loc.id,
                        'company_id': ticket.company_id.id,
                        'date_done': now,
                    })
                    fake_move = self.env['stock.move'].sudo().create({
                        'name': product.display_name,
                        'product_id': product.id,
                        'product_uom_qty': 1.0,
                        'product_uom': product.uom_id.id,
                        'location_id': repair_loc.id,
                        'location_dest_id': cust_loc.id,
                        'picking_id': fake_picking.id,
                        'company_id': ticket.company_id.id,
                        'date': now,
                        'quantity': 1.0,
                    })
                    self.env['stock.move.line'].sudo().create({
                        'picking_id': fake_picking.id,
                        'move_id': fake_move.id,
                        'product_id': product.id,
                        'product_uom_id': product.uom_id.id,
                        'lot_id': serial.id,
                        'qty_done': 1.0,
                        'location_id': repair_loc.id,
                        'location_dest_id': cust_loc.id,
                        'company_id': ticket.company_id.id,
                    })
                    fake_move.sudo().write({'state': 'done'})
                    fake_picking.sudo().write({'state': 'done'})
                    defaults['picking_id'] = fake_picking.id

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
                # Delivery to Return is auto-created — lock the field so the
                # user cannot swap it out.
                for field in arch.xpath("//field[@name='picking_id']"):
                    field.set('readonly', '1')

            # Hide the Studio-added duplicate Return button (action 1997) —
            # the standard create_returns button already handles the flow.
            for btn in arch.xpath("//button[@name='1997']"):
                btn.set('invisible', '1')

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
            # Override location_id to the Studio-defined suggested repair location.
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
            self.product_return_moves.write({'quantity': 1})
        new_picking_id, pick_type_id = super()._create_returns()
        if self.ticket_id:
            new_picking = self.env['stock.picking'].browse(new_picking_id)

            # Rename the new picking so its number/prefix matches the Return
            # Receipt Location's warehouse, e.g. BR-AM/Stock → BR-AM/RET/xxxxx.
            # We can't change picking_type_id once the picking is confirmed
            # ("Changing the operation type ... is forbidden"), so we only
            # overwrite the name.
            #
            # Always target a "<WH_CODE>/RET/" sequence. If none exists for
            # the warehouse yet, create it on the fly so every warehouse ends
            # up with a consistent /RET/-style return numbering scheme.
            loc = self.ticket_id.x_studio_return_receipt_location
            wh = loc.warehouse_id if loc else False
            if wh and wh.code:
                ret_prefix = f"{wh.code}/RET/"
                seq = self.env['ir.sequence'].sudo().search([
                    ('prefix', '=', ret_prefix),
                    '|',
                    ('company_id', '=', wh.company_id.id),
                    ('company_id', '=', False),
                ], limit=1)
                if not seq:
                    seq = self.env['ir.sequence'].sudo().create({
                        'name': f"{wh.name} Sequence return",
                        'prefix': ret_prefix,
                        'padding': 5,
                        'number_increment': 1,
                        'number_next': 1,
                        'implementation': 'standard',
                        'company_id': wh.company_id.id,
                    })
                new_picking.sudo().write({'name': seq.next_by_id()})

            new_picking.move_ids.write({
                'to_refund': False,
                'sale_line_id': False,
            })
            serial = self.ticket_id.x_studio_serial_no
            if serial:
                if new_picking.move_line_ids:
                    new_picking.move_line_ids.write({'lot_id': serial.id})
                else:
                    # Incoming picking — move_lines not auto-created until the
                    # user validates. Pre-create them with the serial so the
                    # user just needs to click Validate.
                    for move in new_picking.move_ids:
                        self.env['stock.move.line'].sudo().create({
                            'picking_id': new_picking.id,
                            'move_id': move.id,
                            'product_id': move.product_id.id,
                            'product_uom_id': move.product_uom.id,
                            'lot_id': serial.id,
                            'location_id': move.location_id.id,
                            'location_dest_id': move.location_dest_id.id,
                            'company_id': new_picking.company_id.id,
                        })
        return new_picking_id, pick_type_id
