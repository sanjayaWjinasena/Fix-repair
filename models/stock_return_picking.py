# -*- coding: utf-8 -*-
from lxml import etree
from odoo import api, fields, models
from odoo.exceptions import UserError


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    is_dispatch_wizard = fields.Boolean(default=False)

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if self.env.context.get('default_location_id'):
            defaults['is_dispatch_wizard'] = True
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

        elif serial and serial.product_id:
            # With Serial No / RUG: look up the existing outgoing delivery.
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
                # Hide entirely when opened from the Dispatch button
                existing = field.get('invisible', '')
                field.set('invisible', f"({existing}) or is_dispatch_wizard" if existing else 'is_dispatch_wizard')

            if is_without_serial_no:
                # Delivery to Return is auto-created — lock the field so the
                # user cannot swap it out.
                for field in arch.xpath("//field[@name='picking_id']"):
                    field.set('readonly', '1')

            # Hide Sales Order / Delivery to Return group when dispatch wizard.
            # The group's parent has invisible="not ticket_id"; extend it.
            for group in arch.xpath("//group[.//field[@name='sale_order_id']]"):
                existing = group.get('invisible', '')
                group.set('invisible', f"({existing}) or is_dispatch_wizard" if existing else 'is_dispatch_wizard')
                break

            # Hide Suggested Return Location fields when dispatch wizard.
            for field in arch.xpath(
                "//field[@name='x_studio_suggested_location_id'] | "
                "//field[@name='x_studio_suggested_location_id_1']"
            ):
                existing = field.get('invisible', '')
                field.set('invisible', f"({existing}) or is_dispatch_wizard" if existing else 'is_dispatch_wizard')

            # Inject is_dispatch_wizard as an invisible field so the client
            # can evaluate the readonly expression without a context check.
            # (Context-based _get_view modifications are cached and may be
            #  returned without the modification on subsequent opens.)
            for form in arch.xpath("//form"):
                fld = etree.Element('field')
                fld.set('name', 'is_dispatch_wizard')
                fld.set('invisible', '1')
                form.insert(0, fld)
                break

            # Dispatch from ticket: default_location_id is pre-set to the
            # customer location — lock it so the user can't change it.
            for field in arch.xpath("//field[@name='location_id']"):
                field.set('readonly', 'is_dispatch_wizard')

            # Hide the To Refund column — forced False in _create_returns anyway.
            for refund_field in arch.xpath(
                "//field[@name='product_return_moves']//field[@name='to_refund']"
            ):
                refund_field.set('column_invisible', '1')

        return arch, view

    @api.depends('picking_id', 'ticket_id', 'is_dispatch_wizard')
    def _compute_moves_locations(self):
        super()._compute_moves_locations()
        for wizard in self:
            # When opened from the Dispatch button, location_id is pre-set to
            # the customer location — skip the repair-location override.
            # Use is_dispatch_wizard (not context) because this compute reruns
            # on picking_id change when context no longer carries default_location_id.
            if not wizard.is_dispatch_wizard:
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
        if self.is_dispatch_wizard:
            # Odoo validates that location_id equals original_location_id or is
            # a child of parent_location_id.  For dispatch we move to the customer
            # location which is outside the warehouse tree, so we neutralise both
            # fields to match our chosen location_id before calling super.
            self.original_location_id = self.location_id
            self.parent_location_id = self.location_id
        new_picking_id, pick_type_id = super()._create_returns()
        if self.ticket_id:
            new_picking = self.env['stock.picking'].browse(new_picking_id)
            new_picking.move_ids.write({
                'to_refund': False,
                'sale_line_id': False,
            })
            # Link the picking back to the ticket so the Return to Customer
            # button on the picking form can check the ticket's stage.
            new_picking.sudo().write({'x_studio_helpdesk_ticket_id': self.ticket_id.id})
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
