# -*- coding: utf-8 -*-
from lxml import etree
from odoo import api, fields, models
from odoo.exceptions import UserError


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    repair_stage_state = fields.Selection([
        ('new',                          'New'),
        ('sent_to_factory',              'Sent to Factory'),
        ('received_at_factory',          'Received at Factory'),
        ('estimation_sent_to_customer',  'Estimation Sent to Customer'),
        ('repair_completed',             'Repair Completed'),
        ('sent_to_sales_centre',         'Sent to Sales Centre'),
        ('received_at_sales_centre',     'Received at Sales Centre'),
        ('other',                        'Other'),
    ], compute='_compute_repair_stage_state', store=True)

    # Override the Studio-defined x_studio_handed_over compute to:
    #   1. Remove the stage-write side effect (caused timeouts on list views)
    #   2. Remove the user-context company bug (was using allowed_company_ids[0]
    #      instead of rec.company_id, moving company-2 tickets to stage 13)
    # Stage transitions are now handled entirely by stock_picking._action_done.
    x_studio_handed_over = fields.Boolean(
        compute='_compute_x_studio_handed_over',
        store=False,
    )

    # True once the technician clicks Mark as Done on the linked FSM task.
    # Used to gate the Send to Sales Centre button.
    task_done = fields.Boolean(compute='_compute_task_done')

    # True when at least one return/transfer picking already exists on this ticket.
    # Used to relabel the Return button as Dispatch on the second trip.
    has_return_picking = fields.Boolean(compute='_compute_has_return_picking')

    # True when there is a 'Ready' (state='assigned') outgoing-to-customer
    # picking stamped to the ticket — i.e. a dispatch already in progress.
    # Used to hide the Dispatch button so the user can't create a duplicate.
    has_ready_dispatch_picking = fields.Boolean(
        compute='_compute_has_ready_dispatch_picking',
    )

    @api.depends(
        'repair_picking_ids.state',
        'repair_picking_ids.location_dest_id.usage',
    )
    def _compute_has_ready_dispatch_picking(self):
        for ticket in self:
            ticket.has_ready_dispatch_picking = any(
                p.state == 'assigned'
                and p.location_dest_id.usage == 'customer'
                for p in ticket.repair_picking_ids
            )

    # Mirrors the linked SO's invoice_status so it can be used in view expressions.
    so_invoice_status = fields.Selection(related='sale_order_id.invoice_status')

    # True once the repair quotation (SO on the linked FSM task — NOT the
    # ticket's sale_order_id, which points at the original product sale) is
    # fully invoiced AND fully paid. Used to gate the Dispatch button: don't
    # hand the item back until the customer has settled the repair bill.
    so_fully_paid = fields.Boolean(compute='_compute_so_fully_paid')

    # True when any linked FSM task sits on a stage named "Tested OK".
    # Used to bypass the payment gate on Dispatch — Tested OK tickets never
    # produce an invoice so the customer has nothing to pay.
    is_tested_ok = fields.Boolean(compute='_compute_is_tested_ok')

    # True when the repair-task SO is cancelled. Same reason as is_tested_ok:
    # cancelled orders never produce invoices.
    is_so_cancelled = fields.Boolean(compute='_compute_is_so_cancelled')

    # Every stock.picking stamped with x_studio_helpdesk_ticket_id == self.id.
    # Powers the Movements smart button on the ticket form. Source-of-truth
    # for "every transfer that happened for this repair", regardless of
    # whether a sale order was ever linked.
    repair_picking_ids = fields.One2many(
        'stock.picking',
        'x_studio_helpdesk_ticket_id',
        string='Movements',
    )
    repair_picking_count = fields.Integer(compute='_compute_repair_picking_count')

    @api.depends('repair_picking_ids')
    def _compute_repair_picking_count(self):
        for ticket in self:
            ticket.repair_picking_count = len(ticket.repair_picking_ids)

    def action_view_repair_pickings(self):
        self.ensure_one()
        return {
            'name': 'Movements',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'tree,form',
            'domain': [('x_studio_helpdesk_ticket_id', '=', self.id)],
            'context': {'default_x_studio_helpdesk_ticket_id': self.id},
        }

    @api.depends(
        'fsm_task_ids.sale_order_id.invoice_status',
        'fsm_task_ids.sale_order_id.amount_unpaid',
    )
    def _compute_so_fully_paid(self):
        for ticket in self:
            task_sos = ticket.fsm_task_ids.mapped('sale_order_id')
            if not task_sos:
                ticket.so_fully_paid = False
                continue
            ticket.so_fully_paid = all(
                so.invoice_status == 'invoiced' and so.amount_unpaid == 0
                for so in task_sos
            )

    @api.depends(
        'fsm_task_ids.x_studio_quick_repair_status_1',
        'fsm_task_ids.x_studio_end_quick_repair',
    )
    def _compute_is_tested_ok(self):
        # "Tested OK" on a project.task is a Studio selection value
        # x_studio_quick_repair_status_1 == 'Quick Repair' (the label
        # displayed in the UI is "Tested OK"). The Studio automations
        # also flip x_studio_end_quick_repair to True on the same event,
        # so either marker counts.
        for ticket in self:
            ticket.is_tested_ok = any(
                t.x_studio_quick_repair_status_1 == 'Quick Repair'
                or t.x_studio_end_quick_repair
                for t in ticket.fsm_task_ids
            )

    @api.depends('fsm_task_ids.sale_order_id.state')
    def _compute_is_so_cancelled(self):
        for ticket in self:
            sos = ticket.fsm_task_ids.mapped('sale_order_id')
            ticket.is_so_cancelled = bool(sos) and any(
                so.state == 'cancel' for so in sos
            )

    @api.depends('stage_id')
    def _compute_repair_stage_state(self):
        mapping = {
            'New':                          'new',
            'Sent to Factory':              'sent_to_factory',
            'Received at Factory':          'received_at_factory',
            'Estimation Sent to Customer':  'estimation_sent_to_customer',
            'Repair Completed':             'repair_completed',
            'Sent to Sales Centre':         'sent_to_sales_centre',
            'Received at Sales Centre':     'received_at_sales_centre',
        }
        for ticket in self:
            # sudo() so users without perm_read on helpdesk.stage can still
            # read the stage name (the stored value is set here, not exposed raw)
            name = (ticket.sudo().stage_id.name or '').strip()
            ticket.repair_stage_state = mapping.get(name, 'other')

    @api.depends('picking_ids')
    def _compute_x_studio_handed_over(self):
        for rec in self:
            rec.x_studio_handed_over = sum(
                1 for p in rec.picking_ids if p.state == 'done'
            ) > 1

    def _compute_task_done(self):
        for ticket in self:
            ticket.task_done = self.env['project.task'].sudo().search_count([
                ('helpdesk_ticket_id', '=', ticket.id),
                ('is_fsm', '=', True),
                ('fsm_done', '=', True),
            ]) > 0

    @api.depends('picking_ids', 'x_studio_serial_no')
    def _compute_has_return_picking(self):
        for ticket in self:
            if ticket.picking_ids:
                ticket.has_return_picking = True
                continue
            # Without Serial No tickets have no sale order → picking_ids is always
            # empty. Fall back to checking whether the serial has already been
            # collected (incoming move from a customer location, done state).
            serial = ticket.x_studio_serial_no
            if serial and ticket.x_studio_normal_repair_without_serial_no:
                cust_locs = self.env['stock.location'].sudo().search(
                    [('usage', '=', 'customer')]
                )
                collected = self.env['stock.move.line'].sudo().search_count([
                    ('lot_id', '=', serial.id),
                    ('picking_code', '=', 'incoming'),
                    ('location_id', 'in', cust_locs.ids),
                    ('state', '=', 'done'),
                ]) > 0
                ticket.has_return_picking = collected
            else:
                ticket.has_return_picking = False

    @api.onchange('x_studio_serial_no')
    def _onchange_serial_no_product(self):
        if self.x_studio_serial_no and self.x_studio_serial_no.product_id:
            self.product_id = self.x_studio_serial_no.product_id
            self.sale_order_id = self._get_so_from_serial(self.x_studio_serial_no)
        elif not self.x_studio_serial_no:
            self.product_id = False
            self.sale_order_id = False

    def _get_so_from_serial(self, serial):
        """Return the Sale Order that last delivered this serial number to a customer."""
        if not serial:
            return self.env['sale.order']
        cust_locs = self.env['stock.location'].sudo().search([('usage', '=', 'customer')])
        move_line = self.env['stock.move.line'].sudo().search([
            ('product_id', '=', serial.product_id.id),
            ('lot_id', '=', serial.id),
            ('picking_code', '=', 'outgoing'),
            ('location_dest_id', 'in', cust_locs.ids),
            ('state', '=', 'done'),
        ], limit=1, order='date desc')
        if not move_line:
            return self.env['sale.order']
        # Prefer direct FK traversal; fall back to origin string match
        if move_line.move_id.sale_line_id:
            return move_line.move_id.sale_line_id.order_id
        return self.env['sale.order'].sudo().search([
            ('name', '=', move_line.origin),
        ], limit=1)

    def _post_write_serial_product_sync(self, vals):
        """Re-assert product_id and sale_order_id from x_studio_serial_no after
        super().write() runs. Studio automations that clear these fields fire
        inside super().write(), so this overrides them. Context flag prevents
        infinite recursion."""
        if 'x_studio_serial_no' not in vals:
            return
        if self.env.context.get('_syncing_serial_product'):
            return
        for rec in self:
            if not (rec.x_studio_serial_no and rec.x_studio_serial_no.product_id):
                continue
            updates = {}
            if rec.product_id != rec.x_studio_serial_no.product_id:
                updates['product_id'] = rec.x_studio_serial_no.product_id.id
            so = rec._get_so_from_serial(rec.x_studio_serial_no)
            if so and rec.sale_order_id != so:
                updates['sale_order_id'] = so.id
            if updates:
                rec.with_context(_syncing_serial_product=True).sudo().write(updates)

    @api.model
    def _deactivate_clearing_serial_automation(self):
        """Deactivate automation 243 ('RR - Auto Select Product for RUG Repairs-33')
        which unconditionally clears product_id/lot_id/sale_order_id whenever
        x_studio_serial_no changes — even when a valid serial is selected.

        Search by x_studio_serial_no field ID (26809) in on_change_field_ids, NOT
        by name, so renamed copies are also caught. Using field ID avoids
        accidentally deactivating automation 172 ('RR - Auto Select Product for
        RUG Repairs') which triggers on ticket_type_id and correctly auto-populates
        product when the ticket type changes.
        """
        serial_field = self.env['ir.model.fields'].sudo().search([
            ('model', '=', 'helpdesk.ticket'),
            ('name', '=', 'x_studio_serial_no'),
        ], limit=1)
        if not serial_field:
            return

        automations = self.env['base.automation'].sudo().with_context(active_test=False).search([
            ('model_id.model', '=', 'helpdesk.ticket'),
        ])

        to_deactivate = self.env['base.automation'].sudo()
        for auto in automations:
            # Only deactivate automations that fire specifically on x_studio_serial_no.
            # Automation 172 fires on ticket_type_id (field 22830), so it is safe.
            if serial_field.id in auto.on_change_field_ids.ids:
                to_deactivate |= auto

        if to_deactivate:
            to_deactivate.write({'active': False})

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            # Inject computed/Studio fields used in button conditions below
            # that may not already be present in the arch.
            for sheet in arch.xpath("//sheet"):
                for fname in (
                    'has_return_picking',
                    'x_studio_normal_repair_without_serial_no',
                    'x_studio_job_location',
                    'so_fully_paid',
                    'is_tested_ok',
                    'is_so_cancelled',
                    'task_done',
                    'has_ready_dispatch_picking',
                ):
                    if not arch.xpath(f"//field[@name='{fname}']"):
                        fld = etree.Element('field')
                        fld.set('name', fname)
                        fld.set('invisible', '1')
                        sheet.insert(0, fld)
                break

            # product_id: manually selectable (serial-tracked products only) for
            # the "Without Serial No" ticket type; readonly for all other types
            # where product is auto-populated from x_studio_serial_no.
            for field in arch.xpath("//field[@name='product_id']"):
                field.set('readonly', "not x_studio_normal_repair_without_serial_no")
                field.set('domain',
                    "[('tracking', '=', 'serial')] "
                    "if x_studio_normal_repair_without_serial_no else []"
                )

            # Assigned-to user: always readonly. The Assign to Me button is the
            # only way to change it (so reassignment is intentional, not a
            # stray click on the dropdown).
            for field in arch.xpath("//field[@name='user_id']"):
                field.set('readonly', '1')

            # Assign to Me: hide as soon as ANY user is assigned (previously
            # only hidden when assigned to the current user — meaning logged-in
            # users could re-grab a ticket from someone else with one click).
            for btn in arch.xpath("//button[@name='action_assign_to_me']"):
                btn.set('invisible', 'user_id')

            # Required-fields gate (same fields the Return button needs):
            #   • A user must first claim the ticket (Assign to Me) — the
            #     button stays clickable on a brand-new ticket because no
            #     other field is required yet.
            #   • Once assigned (user_id set), ticket_type_id becomes required.
            #   • Once a type is picked, the rest become required so the ticket
            #     can't be saved in a half-filled state that would also leave
            #     the Return button hidden.
            #   • Serial number is NOT required for the Without Serial No
            #     type — that flow generates the serial via the Create Serial
            #     No button, which needs to be clickable before x_studio_serial_no
            #     can be populated.
            #   • Warranty card is required only on RUG-confirmed tickets.
            for field in arch.xpath("//field[@name='ticket_type_id']"):
                field.set('required', 'user_id')
            for fname in (
                'partner_id',
                'x_studio_job_location',
                'x_studio_repair_reason',
                'product_id',
            ):
                for field in arch.xpath(f"//field[@name='{fname}']"):
                    field.set('required', 'ticket_type_id')
            for field in arch.xpath("//field[@name='x_studio_serial_no']"):
                field.set('required',
                    'ticket_type_id and not x_studio_normal_repair_without_serial_no')
            for field in arch.xpath("//field[@name='x_studio_warranty_card']"):
                field.set('required', 'x_studio_rug_confirmed')

            # Create Serial No button — Without Serial No type only, once product is set
            # and no serial has been created yet.
            for header in arch.xpath("//header"):
                btn = etree.Element('button')
                btn.set('name', 'action_create_repair_serial')
                btn.set('string', 'Create Serial No')
                btn.set('type', 'object')
                btn.set('class', 'btn-secondary')
                # Visible only on Without-Serial-No tickets that have a
                # product set AND no serial linked yet. Hides as soon as
                # x_studio_serial_no is populated (after a click).
                btn.set('invisible',
                    "not x_studio_normal_repair_without_serial_no "
                    "or not product_id "
                    "or x_studio_serial_no"
                )
                header.insert(0, btn)
                break

            # Restrict stage selection to the ticket's own company
            for field in arch.xpath("//field[@name='stage_id']"):
                field.set('domain',
                    "[('team_ids', 'in', [team_id]), "
                    "'|', ('x_studio_company_id', '=', company_id), "
                    "('x_studio_company_id', '=', False)]"
                )

            # Return Receipt Location: only show stock.locations where the
            # ticket's Assigned-to user appears in Users (Stock Location).
            # When the ticket is unassigned, show all locations.
            for field in arch.xpath("//field[@name='x_studio_return_receipt_location']"):
                field.set('domain',
                    "[('x_studio_users_stock_location', 'in', user_id)] if user_id else []"
                )

            # Change to RUG: visible on External-not-RUG tickets (rug_repair=True,
            # rug_confirmed=False) that have a serial, at early stages only.
            for header in arch.xpath("//header"):
                btn = etree.Element('button')
                btn.set('name', 'action_change_to_rug')
                btn.set('string', 'Change to RUG')
                btn.set('type', 'object')
                btn.set('class', 'btn-secondary')
                btn.set('invisible',
                    "not x_studio_rug_repair or "
                    "x_studio_rug_confirmed or "
                    "not x_studio_serial_no or "
                    "repair_stage_state not in ('new', 'sent_to_factory', 'received_at_factory')"
                )
                header.append(btn)
                break

            # Send to Sales Centre: visible once Mark as Done has been
            # clicked on the linked FSM task (task_done = True), and only
            # while the ticket hasn't yet reached the Sales Centre. Once
            # the user clicks the button the ticket moves to
            # 'sent_to_sales_centre' and beyond, so we hide it there.
            # Centre Repair still hidden — that flow skips the sales-centre
            # trip entirely. Extra carve-out: when the SO is cancelled the
            # ticket gets stuck at Estimation Sent to Customer, so we let
            # Factory Repair surface the button there too (once Mark as
            # Done is hit); the normal-flow at Estimation Sent to Customer
            # stays hidden because is_so_cancelled is False.
            for btn in arch.xpath("//button[@name='action_send_to_sales_centre']"):
                btn.set('invisible',
                    "not task_done or "
                    "x_studio_job_location == 'Centre Repair' or "
                    "repair_stage_state in ('sent_to_sales_centre', "
                    "'received_at_sales_centre', 'other') or "
                    "(repair_stage_state == 'estimation_sent_to_customer' "
                    " and not is_so_cancelled)"
                )

            # Received at Sales Centre: hide for Centre Repair jobs.
            for btn in arch.xpath("//button[@name='action_received_at_sales_centre']"):
                existing = btn.get('invisible', '')
                btn.set('invisible', f"({existing}) or x_studio_job_location == 'Centre Repair'" if existing else "x_studio_job_location == 'Centre Repair'")

            # Send to Factory: only after collection (has_return_picking) and only
            # for Factory Repair jobs while the ticket is still in New stage.
            for btn in arch.xpath("//button[@name='action_send_to_factory']"):
                btn.set('invisible',
                    "repair_stage_state != 'new' or "
                    "not has_return_picking or "
                    "x_studio_job_location != 'Factory Repair'"
                )

            # Plan Intervention:
            #   Factory Repair → show at Received at Factory (item arrived at factory).
            #   Centre Repair  → show in New stage once the item has been collected
            #                    (has_return_picking), skipping the factory trip entirely.
            # RUG tickets additionally require x_studio_valid_return before proceeding.
            for btn in arch.xpath("//button[@name='action_generate_fsm_task']"):
                btn.set('invisible',
                    "not use_fsm or "
                    "fsm_task_count > 0 or "
                    "(x_studio_rug_repair and not x_studio_valid_return) or "
                    "(x_studio_job_location == 'Factory Repair' and repair_stage_state != 'received_at_factory') or "
                    "(x_studio_job_location == 'Centre Repair' and (repair_stage_state != 'new' or not has_return_picking)) or "
                    "not x_studio_job_location"
                )
            # Return button — same action 195, two distinct popup behaviours:
            #   New stage:                 default_ticket_id=id → wizard shows Sale Order
            #                              group so user selects which delivery to reverse
            #   Received at Sales Centre:  default_picking_id=x_studio_pick_id, no ticket_id
            #                              → Sale Order group hidden, items pre-load from
            #                              the picking; return location defaults to Customers
            cust_loc = self.env.ref('stock.stock_location_customers', raise_if_not_found=False)
            cust_loc_id = cust_loc.id if cust_loc else 5
            # default_location_id (Return Location) → Customer for any
            # hand-back-to-customer scenario:
            #   • Factory Repair  at Received at Sales Centre
            #   • NUW with serial at Received at Sales Centre
            #   • Centre Repair   at Repair Completed (Centre Repair skips
            #     the factory trip — the item is already at the sales centre
            #     by the time the ticket hits Repair Completed, so this is
            #     equivalent to Received at Sales Centre for that flow).
            ship_back_cond = (
                "(repair_stage_state == 'received_at_sales_centre' "
                "or (x_studio_job_location == 'Centre Repair' "
                "and repair_stage_state == 'repair_completed'))"
            )
            btn_context = (
                "{'default_ticket_id': (repair_stage_state == 'new' and id) or False, "
                "'default_picking_id': x_studio_pick_id or False, "
                "'default_partner_id': partner_id, "
                f"'default_location_id': ({ship_back_cond} and {cust_loc_id}) or False, "
                "'default_company_id': company_id}"
            )
            for btn in arch.xpath("//button[@name='195']"):
                btn.set('invisible',
                    "has_return_picking or "
                    "not partner_id or "
                    "not ticket_type_id or "
                    "not x_studio_job_location or "
                    "not x_studio_repair_reason or "
                    "not x_studio_serial_no or "
                    "not product_id or "
                    "(x_studio_rug_confirmed and not x_studio_warranty_card)"
                )
                btn.set('context', btn_context)
                # Add Dispatch sibling — same action, shown once a return picking exists
                dispatch = etree.Element('button')
                dispatch.set('name', '195')
                dispatch.set('string', 'Dispatch')
                dispatch.set('type', 'action')
                dispatch.set('class', btn.get('class', 'btn-secondary'))
                # Dispatch visibility — three checks, all must pass:
                #  1. has_return_picking (the item came in)
                #  2. Payment-or-bypass: so_fully_paid OR is_tested_ok OR
                #     is_so_cancelled (the latter two never invoice, so they
                #     stand in for payment)
                #  3. Stage + job-location match — normal flows plus an
                #     extra Centre Repair case: when the SO is cancelled
                #     the ticket gets stuck at Estimation Sent to Customer,
                #     so Dispatch surfaces there once Mark as Done is hit.
                dispatch.set('invisible',
                    "not has_return_picking or "
                    "has_ready_dispatch_picking or "
                    "(not so_fully_paid "
                    " and not is_tested_ok "
                    " and not is_so_cancelled) or "
                    "not ("
                    "(x_studio_job_location == 'Factory Repair' and repair_stage_state == 'received_at_sales_centre') or "
                    "(x_studio_job_location == 'Centre Repair' and repair_stage_state == 'repair_completed') or "
                    "(x_studio_normal_repair_with_serial_no and repair_stage_state == 'received_at_sales_centre') or "
                    "(x_studio_job_location == 'Centre Repair' and is_so_cancelled and task_done and repair_stage_state == 'estimation_sent_to_customer')"
                    ")"
                )
                dispatch.set('context', btn_context)
                btn.addnext(dispatch)

            # Serial Number: only show lots already issued via a sale order.
            # sale_order_ids is non-stored so domain filters on it are ignored.
            # is_issued is a virtual field with a _search that queries move lines.
            serial_domain = "[('is_issued', '=', True)]"
            serial_options = "{'no_create': True, 'no_quick_create': True}"
            for field in arch.xpath("//field[@name='x_studio_serial_no']"):
                field.set('domain', serial_domain)
                field.set('options', serial_options)
            for field in arch.xpath("//field[@name='lot_id']"):
                field.set('domain', serial_domain)
                field.set('options', serial_options)

            # sale_order_id exists in the arch as invisible="1" (hidden input used
            # by helpdesk_sale onchange machinery). Reposition it to appear right
            # after x_studio_serial_no as a visible readonly field.
            serial_nodes = arch.xpath("//field[@name='x_studio_serial_no']")
            so_nodes = arch.xpath("//field[@name='sale_order_id']")
            if serial_nodes and so_nodes:
                so_node = so_nodes[0]
                so_node.getparent().remove(so_node)
                so_node.set('readonly', '1')
                so_node.set('string', 'Sales Order')
                so_node.attrib.pop('invisible', None)
                so_node.set('invisible', 'not sale_order_id')
                serial_nodes[0].addnext(so_node)
        return arch, view

    def action_change_to_rug(self):
        """Change ticket type from External-not-RUG to RUG (Under Warranty - RUG)."""
        rug_type = self.env['helpdesk.ticket.type'].sudo().search(
            [('name', 'ilike', 'Under Warranty - RUG')], limit=1
        )
        if rug_type:
            self.sudo().write({'ticket_type_id': rug_type.id})

    # ── Button actions ─ Without Serial No flow ──────────────────────────────

    def action_create_repair_serial(self):
        self.ensure_one()
        if not self.product_id:
            raise UserError("Select a product before creating a serial number.")
        # No "already exists" guard — clicking again creates a fresh lot
        # and re-points the ticket to it, so the user can change the
        # serial after the fact.
        lot = self.env['stock.lot'].sudo().create({
            'name': self.name,
            'product_id': self.product_id.id,
            'company_id': self.company_id.id,
        })
        self.write({
            'x_studio_serial_no': lot.id,
            'lot_id': lot.id,
            'x_studio_repair_serial_created': True,
        })

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _get_or_create_stage(self, name, sequence):
        """Find the stage by name scoped to this ticket's team and company."""
        self.ensure_one()
        stage = self.env['helpdesk.stage'].sudo().search([
            ('name', '=', name),
            ('team_ids', 'in', self.team_id.ids),
            '|',
            ('x_studio_company_id', '=', self.company_id.id),
            ('x_studio_company_id', '=', False),
        ], limit=1)
        if not stage:
            stage = self.env['helpdesk.stage'].sudo().create({'name': name, 'sequence': sequence})
        return stage

    def _move_to_stage(self, stage_name):
        """Move each ticket to the named stage, scoped to the ticket's company and team.

        Repair Completed is treated as a one-way milestone: if a ticket has
        ever been at that stage before (per mail.tracking.value history),
        this method silently no-ops for that ticket when the target is
        'Repair Completed'. Prevents downstream stages
        (Sent to Sales Centre / Received at Sales Centre / Handed Over)
        from being clobbered back to Repair Completed by stray automation
        chains.
        """
        for ticket in self:
            if (stage_name == 'Repair Completed'
                    and ticket._has_been_at_stage('Repair Completed')):
                continue
            stage = self.env['helpdesk.stage'].sudo().search([
                ('name', '=', stage_name),
                ('team_ids', 'in', ticket.team_id.ids),
                '|',
                ('x_studio_company_id', '=', ticket.company_id.id),
                ('x_studio_company_id', '=', False),
            ], limit=1)
            if stage:
                ticket.sudo().write({'stage_id': stage.id})

    def _has_been_at_stage(self, stage_name):
        """True iff this ticket has ever been at stage_name, based on
        mail.tracking.value history. Counts the historical milestone
        even if the ticket has since moved on."""
        self.ensure_one()
        return bool(self.env['mail.tracking.value'].sudo().search_count([
            ('mail_message_id.model', '=', 'helpdesk.ticket'),
            ('mail_message_id.res_id', '=', self.id),
            ('field_id.model', '=', 'helpdesk.ticket'),
            ('field_id.name', '=', 'stage_id'),
            ('new_value_char', '=', stage_name),
        ]))

    def write(self, vals):
        """Combined write override:
          1. Repair-Completed regression guard: strip stage_id from writes
             that target 'Repair Completed' on tickets that have already
             been there (one-way milestone).
          2. Serial -> product/SO re-assertion: after super().write runs,
             re-apply product_id and sale_order_id from x_studio_serial_no
             so Studio automations that clear them are overridden.
        """
        # 1. Repair Completed regression guard
        if vals.get('stage_id'):
            try:
                stage_id = int(vals['stage_id'])
            except (TypeError, ValueError):
                stage_id = False
            new_stage = (
                self.env['helpdesk.stage'].sudo().browse(stage_id)
                if stage_id else False
            )
            if new_stage and new_stage.exists() and new_stage.name == 'Repair Completed':
                skip = self.filtered(
                    lambda t: t._has_been_at_stage('Repair Completed')
                )
                if skip:
                    vals_no_stage = {k: v for k, v in vals.items() if k != 'stage_id'}
                    allow = self - skip
                    if allow:
                        super(HelpdeskTicket, allow).write(vals)
                        allow._post_write_serial_product_sync(vals)
                    if vals_no_stage:
                        super(HelpdeskTicket, skip).write(vals_no_stage)
                        skip._post_write_serial_product_sync(vals_no_stage)
                    return True
        result = super().write(vals)
        # 2. Serial -> product/SO re-assert
        self._post_write_serial_product_sync(vals)
        return result

    # ── Button actions ───────────────────────────────────────────────────────

    def action_assign_to_me(self):
        self.write({'user_id': self.env.uid})

    def action_send_to_factory(self):
        for ticket in self:
            ticket._create_send_to_factory_picking()
        stage = self._get_or_create_stage('Sent to Factory', 20)
        self.write({
            'stage_id': stage.id,
            'x_studio_s_shipped_date': fields.Datetime.now(),
            'x_studio_s_shipped_by': self.env.uid,
        })

    def action_received_at_factory(self):
        for ticket in self:
            ticket._create_received_at_factory_picking()
        stage = self._get_or_create_stage('Received at Factory', 30)
        self.write({
            'stage_id': stage.id,
            'x_studio_f_received_date': fields.Datetime.now(),
            'x_studio_f_received_by': self.env.uid,
        })

    # ── Stock movements for factory transit ──────────────────────────────────

    def action_generate_fsm_task(self):
        """After the standard Plan Intervention behaviour runs, move the
        item to the right Repair child location:
          - Centre Repair  -> return_receipt_location.warehouse / Repair
          - Factory Repair -> factory_repair_location.warehouse / Repair
        """
        res = super().action_generate_fsm_task()
        for ticket in self:
            ticket._create_plan_intervention_picking()
        return res

    def _create_mark_as_done_picking(self):
        """After repair completes, take the item from its current location
        to the next step's anchor:
          - Centre Repair  -> centre virtual repair loc (Dispatch source)
          - Factory Repair -> factory_repair_location.warehouse/Intransit
            (item is now bound back to the centre).
        No-op when src == dest or required anchor is missing.
        """
        self.ensure_one()
        src_loc = self._current_item_location()
        if not src_loc:
            return False
        if self.x_studio_job_location == 'Centre Repair':
            dest_loc = (
                self.x_studio_virtual_location_1
                or self.x_studio_virtual_location
            )
        else:
            factory = self._get_factory_repair_location()
            dest_loc = (
                factory.warehouse_id._ensure_intransit_location()
                if factory and factory.warehouse_id else False
            )
        if not dest_loc or src_loc == dest_loc:
            return False
        return self._create_repair_transfer(src_loc, dest_loc)

    def _create_plan_intervention_picking(self):
        self.ensure_one()
        src_loc = self._current_item_location()
        if not src_loc:
            return False

        job_loc = self.x_studio_job_location
        if job_loc == 'Centre Repair':
            anchor = self.x_studio_return_receipt_location
            wh = anchor.warehouse_id if anchor else False
        elif job_loc == 'Factory Repair':
            factory = self._get_factory_repair_location()
            wh = factory.warehouse_id if factory else False
        else:
            return False

        if not wh:
            return False
        dest_loc = wh._ensure_repair_location()
        if not dest_loc or dest_loc == src_loc:
            return False
        return self._create_repair_transfer(src_loc, dest_loc)

    def _current_item_location(self):
        """Where the item physically sits right now: destination of the
        most recent picking stamped to this ticket. Falls back to
        x_studio_repair_location when no movement exists yet (e.g. the
        ticket was opened straight into Send to Factory without a
        prior return)."""
        self.ensure_one()
        last = self.env['stock.picking'].sudo().search(
            [('x_studio_helpdesk_ticket_id', '=', self.id)],
            order='date_done desc, id desc', limit=1,
        )
        return last.location_dest_id or self.x_studio_repair_location

    def _create_send_to_factory_picking(self):
        """current location -> Repair Location's warehouse/Intransit."""
        self.ensure_one()
        src_loc = self._current_item_location()
        repair_loc = self.x_studio_repair_location
        if not (src_loc and repair_loc and repair_loc.warehouse_id):
            return False
        intransit = repair_loc.warehouse_id._ensure_intransit_location()
        return self._create_repair_transfer(src_loc, intransit)

    def _create_send_to_sales_centre_picking(self):
        """current location (factory/Intransit) -> centre/Intransit.

        Centre = x_studio_return_receipt_location.warehouse_id, i.e. the
        warehouse that originally received the customer's item.
        """
        self.ensure_one()
        src_loc = self._current_item_location()
        anchor = self.x_studio_return_receipt_location
        if not (src_loc and anchor and anchor.warehouse_id):
            return False
        intransit = anchor.warehouse_id._ensure_intransit_location()
        if not intransit or src_loc == intransit:
            return False
        return self._create_repair_transfer(src_loc, intransit)

    def _create_received_at_sales_centre_picking(self):
        """current location (factory Intransit) -> centre virtual repair loc."""
        self.ensure_one()
        src_loc = self._current_item_location()
        dest_loc = (
            self.x_studio_virtual_location_1
            or self.x_studio_virtual_location
        )
        if not (src_loc and dest_loc) or src_loc == dest_loc:
            return False
        return self._create_repair_transfer(src_loc, dest_loc)

    def _create_received_at_factory_picking(self):
        """current location (centre/Intransit) -> factory warehouse/Intransit."""
        self.ensure_one()
        src_loc = self._current_item_location()
        if not src_loc:
            return False
        anchor = self._get_factory_repair_location()
        if not anchor or not anchor.warehouse_id:
            raise UserError(
                "Factory Repair Location is not configured for company "
                f"'{self.company_id.name}'. Set it in "
                "Settings → Fix Repair → Factory Repair Location."
            )
        dest_loc = anchor.warehouse_id._ensure_intransit_location()
        if not dest_loc or src_loc == dest_loc:
            return False
        return self._create_repair_transfer(src_loc, dest_loc)

    def _get_factory_repair_location(self):
        """Read the per-company factory repair location from ir.config_parameter.

        Key: fix_repair.factory_repair_location.<company_id>
        Value: stock.location ID (stored as string)
        """
        self.ensure_one()
        key = f'fix_repair.factory_repair_location.{self.company_id.id}'
        raw = self.env['ir.config_parameter'].sudo().get_param(key)
        if not raw:
            return self.env['stock.location']
        try:
            loc_id = int(raw)
        except (TypeError, ValueError):
            return self.env['stock.location']
        return self.env['stock.location'].sudo().browse(loc_id).exists()

    def _create_repair_transfer(self, source_loc, dest_loc):
        """Create a state='done' internal picking for self.product_id +
        self.x_studio_serial_no from source_loc to dest_loc. Stamps the
        picking with x_studio_helpdesk_ticket_id so it surfaces under
        the ticket's Movements smart button. Deliberately does NOT
        write sale_id / sale_line_id / group_id / origin — repair-flow
        pickings live on the ticket, not on the repair sale order.
        """
        self.ensure_one()
        serial = self.x_studio_serial_no
        product = self.product_id or (serial and serial.product_id)
        if not (product and source_loc and dest_loc):
            return False

        # Resolve picking_type by warehouse, preferring the source's
        # warehouse for the picking's name prefix. When source is a
        # virtual / warehouse-less location, fall back to the destination
        # warehouse (still gives a sensible XX-YY prefix) before the
        # generic any-internal-in-this-company fallback.
        PickType = self.env['stock.picking.type'].sudo()
        pick_type = False
        if source_loc.warehouse_id:
            pick_type = PickType.search([
                ('code', '=', 'internal'),
                ('warehouse_id', '=', source_loc.warehouse_id.id),
            ], limit=1)
        if not pick_type and dest_loc.warehouse_id:
            pick_type = PickType.search([
                ('code', '=', 'internal'),
                ('warehouse_id', '=', dest_loc.warehouse_id.id),
            ], limit=1)
        if not pick_type:
            pick_type = PickType.search([
                ('code', '=', 'internal'),
                ('warehouse_id.company_id', '=', self.company_id.id),
            ], limit=1)
        if not pick_type:
            return False

        now = fields.Datetime.now()
        picking = self.env['stock.picking'].sudo().create({
            'partner_id': self.partner_id.id,
            'picking_type_id': pick_type.id,
            'location_id': source_loc.id,
            'location_dest_id': dest_loc.id,
            'company_id': self.company_id.id,
            'date_done': now,
            'x_studio_helpdesk_ticket_id': self.id,
        })
        # Do NOT pass `quantity=1.0` here. In Odoo 17 that field on
        # stock.move auto-materializes a move_line; if we then create
        # our own move_line (to carry lot_id/qty_done), the move ends up
        # with two ML records and move.quantity computes to 2.
        move = self.env['stock.move'].sudo().create({
            'name': product.display_name,
            'product_id': product.id,
            'product_uom_qty': 1.0,
            'product_uom': product.uom_id.id,
            'location_id': source_loc.id,
            'location_dest_id': dest_loc.id,
            'picking_id': picking.id,
            'company_id': self.company_id.id,
            'date': now,
        })
        ml_vals = {
            'picking_id': picking.id,
            'move_id': move.id,
            'product_id': product.id,
            'product_uom_id': product.uom_id.id,
            'qty_done': 1.0,
            'location_id': source_loc.id,
            'location_dest_id': dest_loc.id,
            'company_id': self.company_id.id,
        }
        if serial:
            ml_vals['lot_id'] = serial.id
        self.env['stock.move.line'].sudo().create(ml_vals)
        move.sudo().write({'state': 'done'})
        picking.sudo().write({'state': 'done'})
        return picking

    def action_send_to_sales_centre(self):
        for ticket in self:
            ticket._create_send_to_sales_centre_picking()
        stage = self._get_or_create_stage('Sent to Sales Centre', 100)
        self.write({
            'stage_id': stage.id,
            'x_studio_f_shipped_date': fields.Datetime.now(),
            'x_studio_f_shipped_by': self.env.uid,
        })

    def action_received_at_sales_centre(self):
        for ticket in self:
            ticket._create_received_at_sales_centre_picking()
        stage = self._get_or_create_stage('Received at Sales Centre', 110)
        for ticket in self:
            # Find the most-recent done incoming picking that collected this
            # customer's item to the repair virtual location.  Stored so the
            # "Return to Customer" popup (action 195 at this stage) can
            # pre-load the picking via default_picking_id.
            repair_loc = ticket.x_studio_virtual_location_1 or ticket.x_studio_virtual_location
            domain = [
                ('partner_id', '=', ticket.partner_id.id),
                ('company_id', '=', ticket.company_id.id),
                ('state', '=', 'done'),
                ('picking_type_code', '=', 'incoming'),
            ]
            if repair_loc:
                domain.append(('location_dest_id', '=', repair_loc.id))
            pick = self.env['stock.picking'].sudo().search(
                domain, order='date_done desc', limit=1
            )
            ticket.write({
                'stage_id': stage.id,
                'x_studio_s_received_date': fields.Datetime.now(),
                'x_studio_s_received_by': self.env.uid,
                'x_studio_pick_id': pick.id if pick else 0,
            })
