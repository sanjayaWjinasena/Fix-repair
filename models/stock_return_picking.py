# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    @api.model
    def _next_warehouse_ret_name(self, warehouse):
        """Return next value from the <WH_CODE>/RET/ sequence for the
        given warehouse. Auto-creates the sequence if it doesn't exist."""
        if not warehouse or not warehouse.code:
            return False
        ret_prefix = f"{warehouse.code}/RET/"
        seq = self.env['ir.sequence'].sudo().search([
            ('prefix', '=', ret_prefix),
            '|',
            ('company_id', '=', warehouse.company_id.id),
            ('company_id', '=', False),
        ], limit=1)
        if not seq:
            seq = self.env['ir.sequence'].sudo().create({
                'name': f"{warehouse.name} Sequence return",
                'prefix': ret_prefix,
                'padding': 5,
                'number_increment': 1,
                'number_next': 1,
                'implementation': 'standard',
                'company_id': warehouse.company_id.id,
            })
        return seq.next_by_id()

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        ticket_id = defaults.get('ticket_id') or self.env.context.get('default_ticket_id')
        if not ticket_id or defaults.get('picking_id'):
            return defaults

        ticket = self.env['helpdesk.ticket'].browse(ticket_id)
        serial = ticket.x_studio_serial_no
        product = ticket.product_id or (serial and serial.product_id)
        if not (serial and product):
            return defaults

        # ALWAYS synthesise the "Delivery to Return" — for every ticket
        # type. We deliberately do NOT look up the historical outgoing
        # delivery / its original sale order: the repair flow doesn't
        # care which sale put the item in the customer's hands. The
        # repair SO that the FSM task creates later is the SO that owns
        # all these movements; project_task._bind_ticket_pickings_to_so
        # re-points them once that SO exists.
        repair_loc = (
            ticket.x_studio_virtual_location_1
            or ticket.x_studio_virtual_location
        )
        if not repair_loc:
            warehouse = self.env['stock.warehouse'].sudo().search(
                [('company_id', '=', ticket.company_id.id)], limit=1
            )
            repair_loc = warehouse.lot_stock_id if warehouse else False
        cust_loc = self.env['stock.location'].sudo().search(
            [('usage', '=', 'customer')], limit=1
        )
        pick_type_out = self.env['stock.picking.type'].sudo().search([
            ('code', '=', 'outgoing'),
            ('company_id', '=', ticket.company_id.id),
        ], order='sequence asc', limit=1)
        if not (repair_loc and cust_loc and pick_type_out):
            return defaults

        now = fields.Datetime.now()
        # Phantom outgoing left intentionally unstamped: it exists only so
        # the wizard has a source to reverse. _bind_ticket_pickings_to_so
        # searches by x_studio_helpdesk_ticket_id, so leaving the stamp off
        # keeps the phantom out of the repair SO's Delivery smart button.
        # The real return picking gets stamped in _create_returns below.
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
        # Force state to done AFTER linking so _compute_state stays done.
        fake_move.sudo().write({'state': 'done'})
        fake_picking.sudo().write({'state': 'done'})

        # Rename to the ticket's Return-Receipt-Location warehouse RET sequence
        rrl = ticket.x_studio_return_receipt_location
        ret_name = self._next_warehouse_ret_name(rrl.warehouse_id if rrl else False)
        if ret_name:
            fake_picking.sudo().write({'name': ret_name})

        defaults['picking_id'] = fake_picking.id
        return defaults

    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            ctx = self.env.context
            ticket_id = ctx.get('default_ticket_id')
            picking_id_ctx = ctx.get('default_picking_id')

            # Detect whether the wizard is opened from a repair ticket. The
            # Return button passes default_ticket_id directly; the Dispatch
            # button passes only default_picking_id, so we follow the picking
            # back to its ticket (via picking_ids m2m or x_studio_pick_id).
            related_ticket = self.env['helpdesk.ticket']
            if ticket_id:
                related_ticket = self.env['helpdesk.ticket'].sudo().browse(ticket_id)
            elif picking_id_ctx:
                related_ticket = self.env['helpdesk.ticket'].sudo().search([
                    '|',
                    ('picking_ids', 'in', [picking_id_ctx]),
                    ('x_studio_pick_id', '=', picking_id_ctx),
                ], limit=1)
            is_repair = bool(related_ticket and related_ticket.exists())

            if is_repair:
                # Sales Order field and Delivery to Return picking field are
                # entirely driven by our backend logic (context defaults +
                # default_get fallbacks). The user has no business editing
                # them, so hide entirely. Their values continue to flow into
                # _create_returns as before.
                for field in arch.xpath("//field[@name='sale_order_id']"):
                    field.set('invisible', '1')
                for field in arch.xpath("//field[@name='picking_id']"):
                    field.set('invisible', '1')
                # The standard arch wraps both fields in a <group
                # invisible="not ticket_id">. For a repair context ticket_id
                # is truthy, so without overriding the group it would render
                # with just the section header. Force the whole group
                # invisible so nothing of that block appears.
                for grp in arch.xpath("//group[@invisible='not ticket_id']"):
                    grp.set('invisible', '1')
            else:
                # Non-repair callers keep the standard sale_order domain.
                for field in arch.xpath("//field[@name='sale_order_id']"):
                    field.set('domain',
                        "[('partner_id', 'child_of', partner_id), "
                        "('state', 'in', ['sale', 'done'])] "
                        "if partner_id else "
                        "[('state', 'in', ['sale', 'done'])]"
                    )

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
        # Look up the related helpdesk ticket. For Return clicks (stage='new')
        # the wizard's ticket_id is set from default_ticket_id in context.
        # For Dispatch clicks (later stages) the button deliberately drops
        # ticket_id from the context, so we fall back to finding the ticket
        # via the picking we're reversing.
        ticket = self.ticket_id
        if not ticket and self.picking_id:
            ticket = self.env['helpdesk.ticket'].sudo().search([
                '|',
                ('picking_ids', 'in', self.picking_id.ids),
                ('x_studio_pick_id', '=', self.picking_id.id),
            ], limit=1)

        if self.ticket_id:
            self.product_return_moves.write({'quantity': 1})
        new_picking_id, pick_type_id = super()._create_returns()
        new_picking = self.env['stock.picking'].browse(new_picking_id)

        # Rename the new picking to <WH_CODE>/RET/xxxxx based on the
        # ticket's Return Receipt Location warehouse — applies to BOTH
        # Return and Dispatch flows so every reverse transfer for a repair
        # ticket uses the consistent <REPAIR_LOC_WH>/RET/ naming. Also
        # stamp the ticket on the picking via the Studio link so we can
        # find every ticket-related picking deterministically later.
        if ticket:
            new_picking.sudo().write({'x_studio_helpdesk_ticket_id': ticket.id})
            if ticket.x_studio_return_receipt_location:
                loc = ticket.x_studio_return_receipt_location
                ret_name = self._next_warehouse_ret_name(loc.warehouse_id)
                if ret_name:
                    new_picking.sudo().write({'name': ret_name})

        if self.ticket_id:
            # Record this collection picking on the ticket so the later
            # Dispatch click can pre-load it via default_picking_id. For
            # Factory Repair this also gets overwritten by
            # action_received_at_sales_centre when that fires, but Centre
            # Repair skips that step — without this write, Centre Repair
            # Dispatch would launch the wizard with no picking_id.
            self.ticket_id.sudo().write({'x_studio_pick_id': new_picking_id})

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
