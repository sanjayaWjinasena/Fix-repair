# -*- coding: utf-8 -*-
import datetime
import json

from lxml import etree
from odoo import api, fields, models
from odoo.exceptions import UserError


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    # v245: Default 'New' on the required 'name' field so:
    #   1. Save doesn't fail with "Invalid fields: Subject" when a
    #      user creates a ticket without typing a Subject.
    #   2. _repair_seq_no_on_create_or_write() has its sentinel value
    #      to detect (see method below — it looks for name == 'New' OR
    #      empty and then assigns from ir.sequence 'repair.seq').
    # Mirrors Clear-DB's ir.default id=301 (json_value='"New"').
    # Cross-checked with the field's default= on the Fix-repair port
    # only; base helpdesk keeps 'name' required with no default, so
    # this ir.default equivalent is our contribution.
    name = fields.Char(default='New')

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

    # ─────────────────────────────────────────────────────────────────
    # Cluster 1 — RUG (warranty) cycle
    # ─────────────────────────────────────────────────────────────────
    # Migrated from Studio to Python. Field names and behaviour are
    # preserved exactly — downstream code, views, and automations that
    # reference these fields by name continue to work unchanged.
    # Ownership moves from Studio's ir.model.fields state='manual' rows
    # to native class-defined fields; Python takes precedence at
    # runtime, and Studio UI can no longer edit their definitions.
    # DB columns and existing data are preserved throughout.

    # Repair Under Warranty — read from the ticket type's warranty flag.
    # True when the ticket type is configured as an under-warranty repair.
    x_studio_rug_repair = fields.Boolean(
        string='Repair Under Warranty',
        related='ticket_type_id.x_studio_rug',
        store=True,
        readonly=True,
    )

    # RUG Confirmed — read from the ticket type's rug_confirmed flag.
    # True once the ticket type's RUG has been confirmed at setup time.
    x_studio_rug_confirmed = fields.Boolean(
        string='RUG Confirmed',
        related='ticket_type_id.x_studio_rug_confirmed',
        store=True,
        readonly=True,
    )

    # RUG Approved — set to True by the "Approve RUG" flow on the linked
    # sale.order (action_approve_rug_direct on Fix-repair sale.order).
    x_studio_rug_approved = fields.Boolean(
        string='RUG Approved',
    )

    # RUG Request Sent — set to True when the salesperson clicks "Request
    # RUG Approval" on the linked sale.order.
    x_studio_rug_request_sent = fields.Boolean(
        string='RUG Request Sent',
    )

    # Normal Repair (With Serial No) — related from the ticket type.
    x_studio_normal_repair_with_serial_no = fields.Boolean(
        string='Normal Repair (With Serial No)',
        related='ticket_type_id.x_studio_with_serial_no',
        store=True,
        readonly=True,
    )

    # Normal Repair (Without Serial No) — related from the ticket type.
    x_studio_normal_repair_without_serial_no = fields.Boolean(
        string='Normal Repair (Without Serial No)',
        related='ticket_type_id.x_studio_without_serial_no',
        store=True,
        readonly=True,
    )

    # RUG Approval Status — computed from the linked sale order's rug
    # flags. Selection values kept as literal strings (not (key,label)
    # tuples with distinct keys) because Studio's compute wrote the
    # human-readable strings directly, and downstream references
    # (search filters, view invisible expressions) match by string.
    x_studio_rug_approval_status = fields.Selection(
        selection=[
            ('Pending RUG Approval', 'Pending RUG Approval'),
            ('RUG Approved', 'RUG Approved'),
            ('RUG Rejected', 'RUG Rejected'),
        ],
        string='RUG Approval Status',
        compute='_compute_x_studio_rug_approval_status',
    )

    @api.depends('fsm_task_ids.sale_order_id.x_studio_rug_approved',
                 'fsm_task_ids.sale_order_id.x_studio_rug_rejected')
    def _compute_x_studio_rug_approval_status(self):
        # Preserves Studio's original iteration behaviour: iterates all
        # linked fsm tasks and updates val for each task that has an SO.
        # No `break`, so if multiple tasks exist the LAST one determines
        # the outcome. Kept exact so migration is behaviour-preserving.
        for ticket in self:
            val = 'Pending RUG Approval'
            for task in ticket.fsm_task_ids:
                so = task.sale_order_id
                if so:
                    if so.x_studio_rug_approved:
                        val = 'RUG Approved'
                    elif so.x_studio_rug_rejected:
                        val = 'RUG Rejected'
            ticket.x_studio_rug_approval_status = val

    # ─────────────────────────────────────────────────────────────────
    # Cluster 2 — Repair location / stock
    # ─────────────────────────────────────────────────────────────────
    # Migrated from Studio to Python. Same names, same behaviour.
    # Related chains against user_id.x_studio_* remain Studio-owned on
    # res.users for now — those get migrated in a later pass. The
    # related= chain resolves regardless.

    # Repair Location — where the repair physically happens. Set by
    # RR-Auto Populate Repair Location automation (or user-editable).
    # For centre repairs it's the branch's stock location.
    x_studio_repair_location = fields.Many2one(
        'stock.location',
        string='Repair Location',
    )

    # Return Receipt Location — where returned items are received back
    # after a repair round-trip (used by the Return picking flow).
    x_studio_return_receipt_location = fields.Many2one(
        'stock.location',
        string='Return Receipt Location',
    )

    # Source Location — mirrored from the assigned user's home stock
    # location (per-user default source for repair pickings).
    x_studio_source_location = fields.Many2one(
        'stock.location',
        string='Source Location',
        related='user_id.x_studio_source_location',
        store=True,
        readonly=True,
    )

    # Source Location (duplicate slot — appears to be a Studio-created
    # copy from an earlier iteration). Kept for schema compatibility;
    # currently reads from user_id.x_studio_source_location_1 which is
    # itself a Studio-owned res.users field.
    x_studio_source_location_1 = fields.Many2one(
        'stock.location',
        string='Source Location',
        related='user_id.x_studio_source_location_1',
        store=True,
        readonly=True,
    )

    # Virtual Location — mirrored from the assigned user. Used as the
    # in-transit / staging location for repair pickings on the user's
    # branch.
    x_studio_virtual_location = fields.Many2one(
        'stock.location',
        string='Virtual Location',
        related='user_id.x_studio_virtual_location',
        store=True,
        readonly=True,
    )

    # Virtual Location (duplicate slot — Studio copy).
    x_studio_virtual_location_1 = fields.Many2one(
        'stock.location',
        string='Virtual Location',
        related='user_id.x_studio_virtual_location_1',
        store=True,
        readonly=True,
    )

    # Virtual Location Id — integer form of the virtual location's id,
    # used by legacy Studio automations that expect an integer rather
    # than a Many2one recordset.
    x_studio_virtual_location_id = fields.Integer(
        string='Virtual Location Id',
        related='user_id.x_studio_virtual_location.id',
        store=True,
        readonly=True,
    )

    # Pick Id — integer FK to a stock.picking. Historically kept as
    # integer (not a Many2one) by Studio for reasons lost to time.
    # The Many2one variant lives in x_studio_picking_id below.
    x_studio_pick_id = fields.Integer(
        string='Pick Id',
    )

    # Picking Id — proper Many2one to the linked stock.picking. Written
    # by the Fix-repair picking-creation flow.
    x_studio_picking_id = fields.Many2one(
        'stock.picking',
        string='Picking Id',
    )

    # ─────────────────────────────────────────────────────────────────
    # Cluster 3 — Cancel / Reopen lifecycle
    # ─────────────────────────────────────────────────────────────────
    # Migrated from Studio to Python. Same names, same behaviour.
    # Selection values preserved as string identifiers ('None' /
    # 'Cancelled' / 'Reopened') so downstream references match.

    # Cancelled flag — set to True by Studio's cancel automation when
    # a ticket is moved to a cancelled stage.
    x_studio_cancelled = fields.Boolean(
        string='Cancelled',
    )

    # Cancelled (duplicate slot — Studio-created copy). Kept for
    # schema compatibility.
    x_studio_cancelled_2 = fields.Boolean(
        string='Cancelled-2',
    )

    # Cancel Reason — free-text explanation entered by the user
    # closing the ticket.
    x_studio_cancel_reason = fields.Text(
        string='Cancel Reason',
    )

    # Cancel Status — selection flag surfaced on the ticket list view.
    # Two values: 'None' (default) and 'Cancelled'.
    x_studio_cancel_status = fields.Selection(
        selection=[
            ('None', 'None'),
            ('Cancelled', 'Cancelled'),
        ],
        string='Cancel Status',
    )

    # Cancelled By — user who initiated the cancellation.
    x_studio_cancelled_by = fields.Many2one(
        'res.users',
        string='Cancelled By',
    )

    # Cancelled Date — timestamp of the cancellation action.
    x_studio_cancelled_date = fields.Datetime(
        string='Cancelled Date',
    )

    # Cancelled Stage Id — the helpdesk stage the ticket was in when
    # it got cancelled (so reopen can restore it).
    x_studio_cancelled_stage_id = fields.Many2one(
        'helpdesk.stage',
        string='Cancelled Stage Id',
    )

    # Reopened flag — set to True when a cancelled ticket is
    # reactivated.
    x_studio_reopened = fields.Boolean(
        string='Reopened',
    )

    # Reopen Status — selection flag surfaced on list view.
    # Two values: 'None' (default) and 'Reopened'.
    x_studio_reopen_status = fields.Selection(
        selection=[
            ('None', 'None'),
            ('Reopened', 'Reopened'),
        ],
        string='Reopen Status',
    )

    # Reopened By — user who reopened the ticket.
    x_studio_reopened_by = fields.Many2one(
        'res.users',
        string='Reopened By',
    )

    # Reopened Date — timestamp of the reopen action.
    x_studio_reopened_date = fields.Datetime(
        string='Reopened Date',
    )

    # ─────────────────────────────────────────────────────────────────
    # Cluster 4 — Stage-transition markers
    # ─────────────────────────────────────────────────────────────────
    # Boolean flags that flip to True once the ticket has passed the
    # corresponding stage transition. Read by Fix-repair's stage
    # advancement guards (stock_picking._action_done, project_task
    # auto-sync) to avoid re-firing a transition that already ran.
    # x_studio_handed_over is not here — it's already Python-defined
    # earlier in this class (compute, store=False) and gets folded
    # into the migration function below for state-flip safety.

    # Send to Factory — set when the ticket is dispatched to the
    # factory for repair (transition from Diagnosis onwards).
    x_studio_send_to_factory = fields.Boolean(
        string='Send to Factory',
    )

    # Receive at Factory — set when the factory acknowledges receipt.
    x_studio_receive_at_factory = fields.Boolean(
        string='Receive at Factory',
    )

    # Send to Centre — set when the repaired item is dispatched back
    # from the factory to the sales centre.
    x_studio_send_to_centre = fields.Boolean(
        string='Send to Centre',
    )

    # Receive at Centre — set when the sales centre acknowledges
    # receiving the item back from the factory.
    x_studio_receive_at_centre = fields.Boolean(
        string='Receive at Centre',
    )

    # Estimation Sent Stage Updated — set once the ticket has moved
    # to 'Estimation Sent to Customer' stage. Prevents the transition
    # firing twice for the same SO.
    x_studio_estimation_sent_stage_updated = fields.Boolean(
        string='Estimation Sent Stage Updated',
    )

    # Estimation Approved Stage Updated — set once the ticket has
    # moved to 'Estimation Approval Received' stage.
    x_studio_estimation_approved_stage_updated = fields.Boolean(
        string='Estimation Approved Stage Updated',
    )

    # Invoice Stage Updated — set once the invoice-related stage
    # transition has fired.
    x_studio_invoice_stage_updated = fields.Boolean(
        string='Invoice Stage Updated',
    )

    # Repair Started Stage Updated — set once the ticket has moved
    # to 'Repair Started' stage.
    x_studio_repair_started_stage_updated = fields.Boolean(
        string='Repair Started Stage Updated',
    )

    # Repair Complete Stage Updated — set once the ticket has moved
    # to 'Repair Completed' stage.
    x_studio_repair_complete_stage_updated = fields.Boolean(
        string='Repair Complete Stage Updated',
    )

    # ─────────────────────────────────────────────────────────────────
    # Cluster 5 — Stage-validation computes
    # ─────────────────────────────────────────────────────────────────
    # Verbatim ports of the Studio compute strings. Side effects
    # preserved exactly: stage writes, audit-slot writes,
    # datetime.datetime.now() usage, self._uid audit, and the
    # x_studio_items / x_studio_qty / x_studio_sales_price copy-out
    # pattern in the delivered/task-status flows. Behaviour identical
    # to Studio; only ownership moves to Python.

    x_studio_fsm_task_done = fields.Boolean(
        string='FSM Task Done',
        compute='_compute_x_studio_fsm_task_done',
        store=False,
        readonly=True,
    )

    @api.depends('fsm_task_ids')
    def _compute_x_studio_fsm_task_done(self):
        for rec in self:
            task_status = False
            for line in rec.fsm_task_ids:
                if line.fsm_done == True:
                    task_status = True
                if line.x_studio_end_quick_repair == True:
                    task_status = True
            rec['x_studio_fsm_task_done'] = task_status

    x_studio_fully_paid_so = fields.Boolean(
        string='Fully Paid SO',
        compute='_compute_x_studio_fully_paid_so',
        store=False,
        readonly=True,
    )

    @api.depends('fsm_task_ids')
    def _compute_x_studio_fully_paid_so(self):
        for rec in self:
            valid = False
            for invoices in rec.fsm_task_ids:
                if invoices.x_studio_fully_invoiced_so == True:
                    valid = True
                if invoices.x_studio_end_quick_repair == True:
                    valid = True
            rec['x_studio_fully_paid_so'] = valid

    x_studio_valid_confirm_return = fields.Boolean(
        string='Valid Confirm Return',
        compute='_compute_x_studio_valid_confirm_return',
        store=False,
        readonly=True,
    )

    @api.depends('picking_ids')
    def _compute_x_studio_valid_confirm_return(self):
        for rec in self:
            valid = False
            for line in rec.picking_ids:
                if line.state == 'done':
                    valid = True
            rec['x_studio_valid_confirm_return'] = valid

    x_studio_valid_return = fields.Boolean(
        string='Valid Return',
        compute='_compute_x_studio_valid_return',
        store=False,
        readonly=True,
    )

    @api.depends('picking_ids')
    def _compute_x_studio_valid_return(self):
        for rec in self:
            valid = False
            for line in rec.picking_ids:
                if line.state != 'cancel':
                    valid = True
            rec['x_studio_valid_return'] = valid

    x_studio_user_location_validation = fields.Boolean(
        string='User Location Validation',
        compute='_compute_x_studio_user_location_validation',
        store=False,
        readonly=True,
    )

    @api.depends('x_studio_return_receipt_location')
    def _compute_x_studio_user_location_validation(self):
        for rec in self:
            valid = False
            if rec.x_studio_return_receipt_location:
                loc = self.env['stock.location'].search([
                    ('id', '=', rec.x_studio_return_receipt_location.id),
                    ('x_studio_users_stock_location', 'ilike', self._uid),
                    ('active', '=', True),
                ], limit=1)
                if loc:
                    valid = False
                else:
                    valid = True
            rec['x_studio_user_location_validation'] = valid

    x_studio_valid_confirmed_so = fields.Boolean(
        string='Valid Confirmed SO',
        compute='_compute_x_studio_valid_confirmed_so',
        store=False,
        readonly=True,
    )

    @api.depends('fsm_task_ids')
    def _compute_x_studio_valid_confirmed_so(self):
        for rec in self:
            company_ids = rec.env.context.get('allowed_company_ids', [rec.env.user.company_id.id])
            company = self.env['res.company'].browse(company_ids[0])
            valid = False
            for invoices in rec.fsm_task_ids:
                if invoices.x_studio_valid_confirm_so == True:
                    valid = True
            if valid == True:
                if rec.x_studio_estimation_sent_stage_updated == False:
                    rec['x_studio_estimation_sent_stage_updated'] = True
                    if company.id == 1:
                        rec['stage_id'] = 10
                    else:
                        rec['stage_id'] = 29
                    rec['x_studio_stage_date'] = datetime.datetime.now()
                    rec['x_studio_created_by_4'] = self._uid
                    rec['x_studio_created_on_4'] = datetime.datetime.now()
            rec['x_studio_valid_confirmed_so'] = valid

    x_studio_valid_confirmed2_so = fields.Boolean(
        string='Valid Confirmed2 SO',
        compute='_compute_x_studio_valid_confirmed2_so',
        store=False,
        readonly=True,
    )

    @api.depends('fsm_task_ids')
    def _compute_x_studio_valid_confirmed2_so(self):
        for rec in self:
            company_ids = rec.env.context.get('allowed_company_ids', [rec.env.user.company_id.id])
            company = self.env['res.company'].browse(company_ids[0])
            valid = False
            for invoices in rec.fsm_task_ids:
                if invoices.x_studio_valid_confirm2_so == True:
                    valid = True
            if valid == True:
                if rec.x_studio_estimation_approved_stage_updated == False:
                    rec['x_studio_estimation_approved_stage_updated'] = True
                    if company.id == 1:
                        rec['stage_id'] = 12
                    else:
                        rec['stage_id'] = 31
                    rec['x_studio_stage_date'] = datetime.datetime.now()
                    rec['x_studio_created_by_5'] = self._uid
                    rec['x_studio_created_on_5'] = datetime.datetime.now()
            rec['x_studio_valid_confirmed2_so'] = valid

    x_studio_valid_invoiced_so = fields.Boolean(
        string='Valid Invoiced SO',
        compute='_compute_x_studio_valid_invoiced_so',
        store=False,
        readonly=True,
    )

    @api.depends('fsm_task_ids')
    def _compute_x_studio_valid_invoiced_so(self):
        for rec in self:
            company_ids = rec.env.context.get('allowed_company_ids', [rec.env.user.company_id.id])
            company = self.env['res.company'].browse(company_ids[0])
            valid = False
            for invoices in rec.fsm_task_ids:
                if invoices.sale_order_id.x_studio_order_payment_method == 'Credit':
                    valid = False
                else:
                    if invoices.x_studio_valid_invoiced_so == True:
                        valid = True
            if valid == True:
                if rec.x_studio_repair_complete_stage_updated == False:
                    if rec.x_studio_invoice_stage_updated == False:
                        if company.id == 1:
                            rec['stage_id'] = 3
                        else:
                            rec['stage_id'] = 22
                        rec['x_studio_stage_date'] = datetime.datetime.now()
                        rec['x_studio_created_by_6'] = self._uid
                        rec['x_studio_created_on_6'] = datetime.datetime.now()
                        rec['x_studio_invoice_stage_updated'] = True
            rec['x_studio_valid_invoiced_so'] = valid

    x_studio_valid_delivered_so = fields.Boolean(
        string='Valid Delivered SO',
        compute='_compute_x_studio_valid_delivered_so',
        store=False,
        readonly=True,
    )

    @api.depends('fsm_task_ids')
    def _compute_x_studio_valid_delivered_so(self):
        for rec in self:
            company_ids = rec.env.context.get('allowed_company_ids', [rec.env.user.company_id.id])
            company = self.env['res.company'].browse(company_ids[0])
            valid = False
            valid2 = False
            for invoices in rec.fsm_task_ids:
                if invoices.x_studio_valid_delivered_so == True:
                    valid = True
                if invoices.x_studio_valid_delivered_so2 == True:
                    valid2 = True
            if valid2 == True:
                if rec.x_studio_repair_complete_stage_updated == False:
                    if company.id == 1:
                        rec['stage_id'] = 9
                    else:
                        rec['stage_id'] = 28
                    rec['x_studio_stage_date'] = datetime.datetime.now()
                    rec['x_studio_created_by_8'] = self._uid
                    rec['x_studio_created_on_8'] = datetime.datetime.now()
                    rec['x_studio_repair_complete_stage_updated'] = True

                    so_items = self.env['sale.order.line'].search([
                        ('order_id', '=', rec.x_studio_sale_order.id),
                    ])
                    if so_items:
                        tot_item_ids = []
                        qty = []
                        prices = []
                        for items in so_items:
                            if items.product_uom_qty > 0:
                                tot_item_ids.append(items.product_id.id)
                                qty.append(items.product_uom_qty)
                                prices.append(items.price_unit)
                        rec['x_studio_items'] = [(6, 0, tot_item_ids)]
                        rec['x_studio_qty'] = qty
                        rec['x_studio_sales_price'] = prices
            else:
                if valid == True:
                    if rec.x_studio_repair_started_stage_updated == False:
                        if company.id == 1:
                            rec['stage_id'] = 11
                        else:
                            rec['stage_id'] = 30
                        rec['x_studio_stage_date'] = datetime.datetime.now()
                        rec['x_studio_created_by_7'] = self._uid
                        rec['x_studio_created_on_7'] = datetime.datetime.now()
                        rec['x_studio_repair_started_stage_updated'] = True
            rec['x_studio_valid_delivered_so'] = valid

    x_studio_task_status = fields.Boolean(
        string='Task Status',
        compute='_compute_x_studio_task_status',
        store=False,
        readonly=True,
    )

    @api.depends('fsm_task_ids')
    def _compute_x_studio_task_status(self):
        for rec in self:
            company_ids = rec.env.context.get('allowed_company_ids', [rec.env.user.company_id.id])
            company = self.env['res.company'].browse(company_ids[0])
            task_status = False
            for line in rec.fsm_task_ids:
                if line.fsm_done == True:
                    task_status = True
                if line.x_studio_end_quick_repair == True:
                    task_status = True

            if task_status == False:
                if rec.x_studio_sale_order == True:
                    if rec.x_studio_sale_order.state == 'cancel':
                        task_status = True
                    else:
                        delivery1 = self.env['stock.picking'].search([
                            ('sale_id', '=', rec.x_studio_sale_order.id),
                        ], limit=1)
                        if delivery1:
                            delivery = self.env['stock.picking'].search([
                                ('sale_id', '=', rec.x_studio_sale_order.id),
                                ('state', 'not in', ['done', 'cancel']),
                            ], limit=1)
                            if delivery:
                                task_status = False
                            else:
                                task_status = True
                        else:
                            task_status = False

            if task_status == True:
                if rec.x_studio_repair_complete_stage_updated == False:
                    if company.id == 1:
                        rec['stage_id'] = 9
                    else:
                        rec['stage_id'] = 28
                    rec['x_studio_stage_date'] = datetime.datetime.now()
                    rec['x_studio_created_by_8'] = self._uid
                    rec['x_studio_created_on_8'] = datetime.datetime.now()
                    rec['x_studio_repair_complete_stage_updated'] = True

                    so_items = self.env['sale.order.line'].search([
                        ('order_id', '=', rec.x_studio_sale_order.id),
                    ])
                    if so_items:
                        tot_item_ids = []
                        qty = []
                        prices = []
                        for items in so_items:
                            if items.product_uom_qty > 0:
                                tot_item_ids.append(items.product_id.id)
                                qty.append(items.product_uom_qty)
                                prices.append(items.price_unit)
                        rec['x_studio_items'] = [(6, 0, tot_item_ids)]
                        rec['x_studio_qty'] = qty
                        rec['x_studio_sales_price'] = prices

            rec['x_studio_task_status'] = task_status

    # ─────────────────────────────────────────────────────────────────
    # Cluster 6 — Audit slots
    # ─────────────────────────────────────────────────────────────────
    # Ten numbered created_by / created_on pairs (one per stage
    # transition), plus stage_date and the factory/sales-centre
    # shipment audit fields. All simple writable stored fields —
    # populated by the Cluster 5 compute side-effects and by Studio
    # automations elsewhere. Kept as-is (numbered slots are ugly but
    # Studio's automations reference them by name).

    x_studio_stage_date = fields.Datetime(string='Stage Date')

    x_studio_created_by_1 = fields.Many2one('res.users', string='Created By 1')
    x_studio_created_on_1 = fields.Datetime(string='Created On 1')
    x_studio_created_by_2 = fields.Many2one('res.users', string='Created By 2')
    x_studio_created_on_2 = fields.Datetime(string='Created On 2')
    x_studio_created_by_3 = fields.Many2one('res.users', string='Created By 3')
    x_studio_created_on_3 = fields.Datetime(string='Created On 3')
    x_studio_created_by_4 = fields.Many2one('res.users', string='Created By 4')
    x_studio_created_on_4 = fields.Datetime(string='Created On 4')
    x_studio_created_by_5 = fields.Many2one('res.users', string='Created By 5')
    x_studio_created_on_5 = fields.Datetime(string='Created On 5')
    x_studio_created_by_6 = fields.Many2one('res.users', string='Created By 6')
    x_studio_created_on_6 = fields.Datetime(string='Created On 6')
    x_studio_created_by_7 = fields.Many2one('res.users', string='Created By 7')
    x_studio_created_on_7 = fields.Datetime(string='Created On 7')
    x_studio_created_by_8 = fields.Many2one('res.users', string='Created By 8')
    x_studio_created_on_8 = fields.Datetime(string='Created On 8')
    x_studio_created_by_9 = fields.Many2one('res.users', string='Created By 9')
    x_studio_created_on_9 = fields.Datetime(string='Created On 9')
    x_studio_created_by_10 = fields.Many2one('res.users', string='Created By 10')
    x_studio_created_on_10 = fields.Datetime(string='Created On 10')

    # Factory shipment audit (sent to factory / received at factory)
    x_studio_f_shipped_by = fields.Many2one('res.users', string='Shipped By')
    x_studio_f_shipped_date = fields.Datetime(string='Shipped Date')
    x_studio_f_received_by = fields.Many2one('res.users', string='Received By')
    x_studio_f_received_date = fields.Datetime(string='Received Date')

    # Sales-centre shipment audit (sent from factory / received at centre)
    x_studio_s_shipped_by = fields.Many2one('res.users', string='Shipped By')
    x_studio_s_shipped_date = fields.Datetime(string='Shipped Date')
    x_studio_s_received_by = fields.Many2one('res.users', string='Received By')
    x_studio_s_received_date = fields.Datetime(string='Received Date')

    # ─────────────────────────────────────────────────────────────────
    # Cluster 7 — Serial number / product
    # ─────────────────────────────────────────────────────────────────
    # Serial-lot references, repair reasons, and the product/qty/
    # price snapshot fields that Cluster 5's task_status compute
    # writes to. Duplicate slots preserved for schema compatibility.
    # Related chains walk through x_studio_sale_order (Studio-owned
    # until Cluster 8) — Odoo resolves the chain at runtime by field
    # name, so the migration order is irrelevant.

    # Serial Number — primary lot/serial for the item under repair.
    x_studio_serial_no = fields.Many2one(
        'stock.lot',
        string='Serial Number',
    )

    # Serial Number-11 — duplicate slot from an earlier Studio
    # iteration. Kept for schema compatibility.
    x_studio_serial_number = fields.Many2one(
        'stock.lot',
        string='Serial Number-11',
    )

    # SN Updated — flag set to True once the serial number has been
    # confirmed / edited by the repair user.
    x_studio_sn_updated = fields.Boolean(
        string='SN Updated',
    )

    # Repair Serial Created — flag set when a new stock.lot has been
    # created as part of the repair flow.
    x_studio_repair_serial_created = fields.Boolean(
        string='Repair Serial Created',
    )

    # Repair Reason — many-to-many onto the Studio-managed
    # x_repair_reason_custom catalogue.
    x_studio_repair_reason = fields.Many2many(
        'x_repair_reason_custom',
        string='Repair Reason',
    )

    # Materials Used — first product from the linked SO's first
    # order line. Related chain walks Many2one -> One2many -> M2o;
    # Odoo returns the first match (Studio's semantics).
    x_studio_materials_used = fields.Many2one(
        'product.product',
        string='Materials Used ',
        related='x_studio_sale_order.order_line.product_id',
        store=True,
        readonly=True,
    )

    # Quantity — first order line's product_uom_qty (same chain).
    x_studio_quantity = fields.Float(
        string='Quantity',
        related='x_studio_sale_order.order_line.product_uom_qty',
        store=True,
        readonly=True,
    )

    # Unit Price — Studio related to pricelist's item prices (also
    # traverses O2M via first record). Stored as Char in Studio's
    # schema despite the source being Float; kept as Char here for
    # 1:1 compatibility.
    x_studio_unit_price = fields.Char(
        string='Unit Price',
        related='x_studio_sale_order.pricelist_id.item_ids.price',
        store=False,
        readonly=True,
    )

    # Items — Many2many snapshot of all products on the linked SO.
    # Written by the Cluster 5 task_status / valid_delivered_so
    # compute side effects.
    x_studio_items = fields.Many2many(
        'product.product',
        string='Items',
    )

    # Qty — Char snapshot of the SO lines' quantities. Written by
    # Cluster 5 as the string representation of a Python list of
    # floats (e.g. "[1.0, 2.0]") — Studio behaviour preserved.
    x_studio_qty = fields.Char(
        string='Qty',
    )

    # Sales Price — Char snapshot of the SO lines' unit prices.
    # Same Python-list-as-string pattern as x_studio_qty.
    x_studio_sales_price = fields.Char(
        string='Sales Price',
    )

    # ─────────────────────────────────────────────────────────────────
    # Cluster 8 — Diagnostic / misc (final cluster)
    # ─────────────────────────────────────────────────────────────────
    # Final 20 remaining Studio fields on helpdesk.ticket. Includes
    # useful diagnostic fields (branch, city, driver_name, warranty
    # card, sale_order compute, re-estimate flags), Studio-related
    # utility fields (stage_name, tracking, cccc/cccc3 auto-renames),
    # and the double-x-prefix picking count field. All preserved
    # 1:1 with Studio names, ttypes, selections, and compute logic.

    x_studio_balance_due = fields.Float(
        string='Balance Due',
    )

    x_studio_branch = fields.Selection(
        selection=[
            ('Colombo', 'Colombo'),
            ('Gampah', 'Gampah'),
        ],
        string='Branch',
    )

    # CCCC — related from ticket_type_id.name. Studio auto-generated
    # name suggests it was a test / rename artefact. Kept for schema
    # compatibility.
    x_studio_cccc = fields.Char(
        string='CCCC',
        related='ticket_type_id.name',
        store=True,
        readonly=True,
    )

    # CCCC3 — Studio auto-generated related to stage_id.
    x_studio_cccc3 = fields.Many2one(
        'helpdesk.stage',
        string='CCCC3',
        related='stage_id',
        store=True,
        readonly=True,
    )

    x_studio_city = fields.Selection(
        selection=[
            ('Gampaha', 'Gampaha'),
            ('Colombo', 'Colombo'),
            ('Yakkala', 'Yakkala'),
        ],
        string='City',
    )

    x_studio_driver_name = fields.Char(
        string='Driver Name',
    )

    x_studio_job_location = fields.Selection(
        selection=[
            ('Centre Repair', 'Centre Repair'),
            ('Factory Repair', 'Factory Repair'),
        ],
        string='Job Location',
    )

    x_studio_material_availability = fields.Selection(
        selection=[
            ('Material Not Ready', 'Material Not Ready'),
            ('Material Ready', 'Material Ready'),
        ],
        string='Material Availability',
        compute='_compute_x_studio_material_availability',
        store=False,
        readonly=True,
    )

    @api.depends('fsm_task_ids')
    def _compute_x_studio_material_availability(self):
        for rec in self:
            val = 'Material Not Ready'
            for invoices in rec.fsm_task_ids:
                val = invoices.x_studio_material_availability
            rec['x_studio_material_availability'] = val

    # Tested OK — Studio-defined selection with 'Quick Repair' key
    # mapped to 'Tested OK' display. Studio row has an empty compute
    # string; effectively a stored readonly field with no auto-compute.
    x_studio_quick_repair_status = fields.Selection(
        selection=[
            ('None', 'None'),
            ('Quick Repair', 'Tested OK'),
        ],
        string='Tested OK',
        store=True,
        readonly=True,
    )

    x_studio_re_estimate_count = fields.Integer(
        string='Re-estimate Count',
        compute='_compute_x_studio_re_estimate_count',
        store=False,
        readonly=True,
    )

    @api.depends('fsm_task_ids')
    def _compute_x_studio_re_estimate_count(self):
        for rec in self:
            val = 0
            for invoices in rec.fsm_task_ids:
                val = invoices.sale_order_id.x_studio_re_estimate_count
            rec['x_studio_re_estimate_count'] = val

    x_studio_re_estimate_status = fields.Selection(
        selection=[
            ('None', 'None'),
            ('Re-estimated', 'Re-estimated'),
        ],
        string='Re-estimate Status',
        compute='_compute_x_studio_re_estimate_status',
        store=False,
        readonly=True,
    )

    @api.depends('fsm_task_ids')
    def _compute_x_studio_re_estimate_status(self):
        for rec in self:
            val = 'None'
            for invoices in rec.fsm_task_ids:
                if invoices.sale_order_id.x_studio_re_estimate_count > 0:
                    val = 'Re-estimated'
            rec['x_studio_re_estimate_status'] = val

    # Studio-generated "New Related Field" one2many — related to
    # project_id.task_ids. Auto-named by Studio (FNjnC / QuqN1
    # suffixes are UUID fragments).
    x_studio_related_field_FNjnC = fields.One2many(
        'project.task',
        string='New Related Field',
        related='project_id.task_ids',
        store=False,
        readonly=True,
    )

    x_studio_related_field_QuqN1 = fields.Integer(
        string='New Related Field',
        related='project_id.task_ids.helpdesk_ticket_id.id',
        store=True,
        readonly=True,
    )

    x_studio_related_information = fields.Binary(
        string='Related Information',
    )

    # Sales Order — first non-empty sale_order_id found across the
    # linked fsm tasks (Studio's LAST-match semantics preserved:
    # loop overwrites `so` each iteration, so the last task with an
    # SO wins).
    x_studio_sale_order = fields.Many2one(
        'sale.order',
        string='Sales Order',
        compute='_compute_x_studio_sale_order',
        store=False,
        readonly=True,
    )

    @api.depends('fsm_task_ids')
    def _compute_x_studio_sale_order(self):
        for rec in self:
            so = False
            for invoices in rec.fsm_task_ids:
                if invoices.sale_order_id != False:
                    so = invoices.sale_order_id.id
            rec['x_studio_sale_order'] = so

    x_studio_stage_name = fields.Char(
        string='Stage Name',
        related='stage_id.name',
        store=True,
        readonly=True,
    )

    x_studio_tracking = fields.Selection(
        selection=[
            ('serial', 'By Unique Serial Number'),
            ('lot', 'By Lots'),
            ('none', 'No Tracking'),
        ],
        string='Tracking',
        related='product_id.tracking',
        store=False,
        readonly=True,
    )

    x_studio_vehicle_details = fields.Char(
        string='Vehicle Details',
    )

    x_studio_warranty_card = fields.Binary(
        string='Warranty Card',
    )

    # Double-x-prefix Studio field (Odoo added an extra `x_` at some
    # rename step; the field name is now literally `x_x_studio_...`).
    # Counts stock.picking records that reference this ticket via
    # x_studio_created_from_help_ticket. Compute preserved verbatim.
    x_x_studio_created_from_help_ticket_stock_picking_count = fields.Integer(
        string='Created from Help Ticket count',
        compute='_compute_x_x_studio_created_from_help_ticket_stock_picking_count',
        store=False,
    )

    def _compute_x_x_studio_created_from_help_ticket_stock_picking_count(self):
        for record in self:
            record['x_x_studio_created_from_help_ticket_stock_picking_count'] = \
                self.env['stock.picking'].search_count([
                    ('x_studio_created_from_help_ticket', '=', record.id),
                ])

    @api.model
    def _migrate_studio_rug_cluster_to_base(self):
        """Complete the Cluster 1 (RUG) migration by transferring
        ir.model.fields ownership from Studio to this module.

        After the Python class defines these fields (v129+), Python
        already owns runtime behaviour — but the ir.model.fields rows
        still show state='manual' and modules contain
        'studio_customization', so Studio's UI treats them as
        Studio-managed. This one-shot migration:

          1. Flips state='manual' → state='base' on the seven RUG
             cluster fields so Studio recognises them as base fields.
          2. Removes the Studio ir.model.data records that link these
             field rows to the studio_customization module, so
             uninstalling studio_customization can't drop them.

        Does NOT delete any ir.model.fields row and does NOT drop any
        DB column. Existing field values are fully preserved.
        Idempotent: subsequent runs find nothing to update.
        """
        cluster1 = [
            'x_studio_rug_repair',
            'x_studio_rug_confirmed',
            'x_studio_rug_approved',
            'x_studio_rug_request_sent',
            'x_studio_normal_repair_with_serial_no',
            'x_studio_normal_repair_without_serial_no',
            'x_studio_rug_approval_status',
        ]
        Field = self.env['ir.model.fields'].sudo()
        rows = Field.search([
            ('model', '=', 'helpdesk.ticket'),
            ('name', 'in', cluster1),
        ])
        manual_rows = rows.filtered(lambda f: f.state == 'manual')
        if manual_rows:
            manual_rows.write({'state': 'base'})

        # Drop the Studio ir.model.data pins so studio_customization
        # doesn't claim ownership of these rows anymore.
        ModelData = self.env['ir.model.data'].sudo()
        studio_pins = ModelData.search([
            ('model', '=', 'ir.model.fields'),
            ('res_id', 'in', rows.ids),
            ('module', '=', 'studio_customization'),
        ])
        if studio_pins:
            studio_pins.unlink()

    @api.model
    def _migrate_studio_location_cluster_to_base(self):
        """Cluster 2 (Repair location / stock) counterpart of the RUG
        migration: transfer ir.model.fields ownership of the nine
        location/stock helpdesk.ticket fields from Studio to Python.

        Same idempotent pattern:
          1. state 'manual' → 'base' on all nine cluster rows
          2. drop studio_customization ir.model.data pins

        Data / DB columns preserved.
        """
        cluster2 = [
            'x_studio_repair_location',
            'x_studio_return_receipt_location',
            'x_studio_source_location',
            'x_studio_source_location_1',
            'x_studio_virtual_location',
            'x_studio_virtual_location_1',
            'x_studio_virtual_location_id',
            'x_studio_pick_id',
            'x_studio_picking_id',
        ]
        Field = self.env['ir.model.fields'].sudo()
        rows = Field.search([
            ('model', '=', 'helpdesk.ticket'),
            ('name', 'in', cluster2),
        ])
        manual_rows = rows.filtered(lambda f: f.state == 'manual')
        if manual_rows:
            manual_rows.write({'state': 'base'})

        ModelData = self.env['ir.model.data'].sudo()
        studio_pins = ModelData.search([
            ('model', '=', 'ir.model.fields'),
            ('res_id', 'in', rows.ids),
            ('module', '=', 'studio_customization'),
        ])
        if studio_pins:
            studio_pins.unlink()

    @api.model
    def _migrate_studio_stage_marker_cluster_to_base(self):
        """Cluster 4 (Stage-transition markers) migration. Ten
        Boolean flags including x_studio_handed_over (which was
        already Python-defined earlier for its compute override —
        listed here so its ir.model.fields row also flips to
        state='base').

        Same idempotent pattern as previous clusters:
          1. state 'manual' → 'base' on all ten rows
          2. drop studio_customization ir.model.data pins
        """
        cluster4 = [
            'x_studio_send_to_factory',
            'x_studio_receive_at_factory',
            'x_studio_send_to_centre',
            'x_studio_receive_at_centre',
            'x_studio_estimation_sent_stage_updated',
            'x_studio_estimation_approved_stage_updated',
            'x_studio_invoice_stage_updated',
            'x_studio_repair_started_stage_updated',
            'x_studio_repair_complete_stage_updated',
            'x_studio_handed_over',
        ]
        Field = self.env['ir.model.fields'].sudo()
        rows = Field.search([
            ('model', '=', 'helpdesk.ticket'),
            ('name', 'in', cluster4),
        ])
        manual_rows = rows.filtered(lambda f: f.state == 'manual')
        if manual_rows:
            manual_rows.write({'state': 'base'})

        ModelData = self.env['ir.model.data'].sudo()
        studio_pins = ModelData.search([
            ('model', '=', 'ir.model.fields'),
            ('res_id', 'in', rows.ids),
            ('module', '=', 'studio_customization'),
        ])
        if studio_pins:
            studio_pins.unlink()

    @api.model
    def _migrate_studio_stage_validation_cluster_to_base(self):
        """Cluster 5 (Stage-validation computes) migration. Ten
        computed Boolean fields whose compute strings were ported
        verbatim from Studio, including the side-effecting stage
        writes and audit-slot writes.

        Same idempotent pattern as previous clusters:
          1. state 'manual' → 'base' on all ten cluster rows
          2. drop studio_customization ir.model.data pins
        """
        cluster5 = [
            'x_studio_fsm_task_done',
            'x_studio_fully_paid_so',
            'x_studio_valid_confirm_return',
            'x_studio_valid_return',
            'x_studio_user_location_validation',
            'x_studio_valid_confirmed_so',
            'x_studio_valid_confirmed2_so',
            'x_studio_valid_invoiced_so',
            'x_studio_valid_delivered_so',
            'x_studio_task_status',
        ]
        Field = self.env['ir.model.fields'].sudo()
        rows = Field.search([
            ('model', '=', 'helpdesk.ticket'),
            ('name', 'in', cluster5),
        ])
        manual_rows = rows.filtered(lambda f: f.state == 'manual')
        if manual_rows:
            manual_rows.write({'state': 'base'})

        ModelData = self.env['ir.model.data'].sudo()
        studio_pins = ModelData.search([
            ('model', '=', 'ir.model.fields'),
            ('res_id', 'in', rows.ids),
            ('module', '=', 'studio_customization'),
        ])
        if studio_pins:
            studio_pins.unlink()

    @api.model
    def _migrate_studio_audit_cluster_to_base(self):
        """Cluster 6 (Audit slots) migration. 29 simple writable
        stored fields: 10 numbered created_by pairs + 10 created_on
        pairs, x_studio_stage_date, and the four factory + four
        sales-centre shipment audit fields.

        Same idempotent pattern as previous clusters:
          1. state 'manual' → 'base' on all 29 cluster rows
          2. drop studio_customization ir.model.data pins
        """
        cluster6 = [
            'x_studio_stage_date',
            'x_studio_created_by_1', 'x_studio_created_on_1',
            'x_studio_created_by_2', 'x_studio_created_on_2',
            'x_studio_created_by_3', 'x_studio_created_on_3',
            'x_studio_created_by_4', 'x_studio_created_on_4',
            'x_studio_created_by_5', 'x_studio_created_on_5',
            'x_studio_created_by_6', 'x_studio_created_on_6',
            'x_studio_created_by_7', 'x_studio_created_on_7',
            'x_studio_created_by_8', 'x_studio_created_on_8',
            'x_studio_created_by_9', 'x_studio_created_on_9',
            'x_studio_created_by_10', 'x_studio_created_on_10',
            'x_studio_f_shipped_by', 'x_studio_f_shipped_date',
            'x_studio_f_received_by', 'x_studio_f_received_date',
            'x_studio_s_shipped_by', 'x_studio_s_shipped_date',
            'x_studio_s_received_by', 'x_studio_s_received_date',
        ]
        Field = self.env['ir.model.fields'].sudo()
        rows = Field.search([
            ('model', '=', 'helpdesk.ticket'),
            ('name', 'in', cluster6),
        ])
        manual_rows = rows.filtered(lambda f: f.state == 'manual')
        if manual_rows:
            manual_rows.write({'state': 'base'})

        ModelData = self.env['ir.model.data'].sudo()
        studio_pins = ModelData.search([
            ('model', '=', 'ir.model.fields'),
            ('res_id', 'in', rows.ids),
            ('module', '=', 'studio_customization'),
        ])
        if studio_pins:
            studio_pins.unlink()

    @api.model
    def _migrate_studio_serial_product_cluster_to_base(self):
        """Cluster 7 (Serial number / product) migration. Eleven
        fields: serial-lot refs (primary + duplicate + sn_updated +
        serial_created), repair reason M2M, and the four
        product/qty/price snapshot fields Cluster 5 writes to.

        Same idempotent pattern.
        """
        cluster7 = [
            'x_studio_serial_no',
            'x_studio_serial_number',
            'x_studio_sn_updated',
            'x_studio_repair_serial_created',
            'x_studio_repair_reason',
            'x_studio_materials_used',
            'x_studio_quantity',
            'x_studio_unit_price',
            'x_studio_items',
            'x_studio_qty',
            'x_studio_sales_price',
        ]
        Field = self.env['ir.model.fields'].sudo()
        rows = Field.search([
            ('model', '=', 'helpdesk.ticket'),
            ('name', 'in', cluster7),
        ])
        manual_rows = rows.filtered(lambda f: f.state == 'manual')
        if manual_rows:
            manual_rows.write({'state': 'base'})

        ModelData = self.env['ir.model.data'].sudo()
        studio_pins = ModelData.search([
            ('model', '=', 'ir.model.fields'),
            ('res_id', 'in', rows.ids),
            ('module', '=', 'studio_customization'),
        ])
        if studio_pins:
            studio_pins.unlink()

    @api.model
    def _migrate_studio_misc_cluster_to_base(self):
        """Cluster 8 (Diagnostic / misc) — the final cluster. 20
        remaining Studio fields on helpdesk.ticket including the
        double-x-prefix picking count field.

        Same idempotent pattern as previous clusters.
        """
        cluster8 = [
            'x_studio_balance_due',
            'x_studio_branch',
            'x_studio_cccc',
            'x_studio_cccc3',
            'x_studio_city',
            'x_studio_driver_name',
            'x_studio_job_location',
            'x_studio_material_availability',
            'x_studio_quick_repair_status',
            'x_studio_re_estimate_count',
            'x_studio_re_estimate_status',
            'x_studio_related_field_FNjnC',
            'x_studio_related_field_QuqN1',
            'x_studio_related_information',
            'x_studio_sale_order',
            'x_studio_stage_name',
            'x_studio_tracking',
            'x_studio_vehicle_details',
            'x_studio_warranty_card',
            'x_x_studio_created_from_help_ticket_stock_picking_count',
        ]
        Field = self.env['ir.model.fields'].sudo()
        rows = Field.search([
            ('model', '=', 'helpdesk.ticket'),
            ('name', 'in', cluster8),
        ])
        manual_rows = rows.filtered(lambda f: f.state == 'manual')
        if manual_rows:
            manual_rows.write({'state': 'base'})

        ModelData = self.env['ir.model.data'].sudo()
        studio_pins = ModelData.search([
            ('model', '=', 'ir.model.fields'),
            ('res_id', 'in', rows.ids),
            ('module', '=', 'studio_customization'),
        ])
        if studio_pins:
            studio_pins.unlink()

    @api.model
    def _migrate_studio_cancel_cluster_to_base(self):
        """Cluster 3 (Cancel / Reopen lifecycle) counterpart of the
        earlier cluster migrations: transfer ir.model.fields ownership
        of the eleven cancel/reopen helpdesk.ticket fields from Studio
        to Python.

        Same idempotent pattern:
          1. state 'manual' → 'base' on all eleven cluster rows
          2. drop studio_customization ir.model.data pins

        Data / DB columns preserved.
        """
        cluster3 = [
            'x_studio_cancelled',
            'x_studio_cancelled_2',
            'x_studio_cancel_reason',
            'x_studio_cancel_status',
            'x_studio_cancelled_by',
            'x_studio_cancelled_date',
            'x_studio_cancelled_stage_id',
            'x_studio_reopened',
            'x_studio_reopen_status',
            'x_studio_reopened_by',
            'x_studio_reopened_date',
        ]
        Field = self.env['ir.model.fields'].sudo()
        rows = Field.search([
            ('model', '=', 'helpdesk.ticket'),
            ('name', 'in', cluster3),
        ])
        manual_rows = rows.filtered(lambda f: f.state == 'manual')
        if manual_rows:
            manual_rows.write({'state': 'base'})

        ModelData = self.env['ir.model.data'].sudo()
        studio_pins = ModelData.search([
            ('model', '=', 'ir.model.fields'),
            ('res_id', 'in', rows.ids),
            ('module', '=', 'studio_customization'),
        ])
        if studio_pins:
            studio_pins.unlink()

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

    # Legacy field kept on the model to avoid view-load crashes on
    # databases whose helpdesk.ticket form inheritance was applied while
    # this field existed (v90/v91). The button + UI references have been
    # removed; this exists only so old view arch resolves cleanly. Safe
    # to drop after module upgrade has reapplied the v93+ view XML.
    can_re_estimate = fields.Boolean(
        compute='_compute_can_re_estimate',
    )

    def _compute_can_re_estimate(self):
        for ticket in self:
            ticket.can_re_estimate = False


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

    # True as soon as any picking linked to this ticket transitions
    # to state='done' — i.e. the first movement (send-to-factory,
    # receive-at-factory, dispatch, etc.) has been validated.
    # Downstream _get_view uses this to mark every field on the
    # ticket form readonly. Data captured before the first movement
    # (Customer, Product, Priority, Job Location, Warranty details,
    # etc.) becomes locked so a completed physical movement can't
    # be paired with silently rewritten intake data.
    x_ticket_locked = fields.Boolean(
        compute='_compute_x_ticket_locked',
        help='True once at least one linked movement transfer has been '
             'validated. Freezes the ticket form so the intake data '
             'stays a truthful record of the state at first movement.',
    )

    @api.depends('repair_picking_ids.state')
    def _compute_x_ticket_locked(self):
        for ticket in self:
            ticket.x_ticket_locked = any(
                p.state == 'done'
                for p in ticket.repair_picking_ids
            )

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

    def fix_repair_action_direct_return(self):
        """One-click Return: skip the stock.return.picking wizard popup.

        Everything the wizard needed the user to click through is already
        deterministic for a repair ticket — default_get on
        stock.return.picking (our override in stock_return_picking.py)
        synthesises the phantom source picking, product_return_moves is
        auto-computed from that source, and quantity is capped at 1
        because a repair ticket is always a single-item flow. There is
        no decision left for the user to make on the wizard, so opening
        it and asking them to click Return again is pure friction.

        This method builds the wizard record in-memory with the same
        defaults the header button's context previously passed, then
        calls the wizard's public create_returns() — which invokes our
        _create_returns() override (renames to <WH>/RET/xxxxx, stamps
        the ticket, forces to_refund=False, pre-populates the serial)
        and returns the ir.actions.act_window opening the new return
        picking. The end user experiences: click Return → land on the
        new RET picking.
        """
        self.ensure_one()
        # Rebuild the context the header button used to pass. Preserve
        # any values already in env.context so future callers (test
        # fixtures, an alternate button, etc.) can override.
        ctx = dict(self.env.context)

        # Strip default_location_id from the inherited context.
        # The header button's `context` attribute — carried over from
        # the v199 action-195 setup for backward compatibility with the
        # Dispatch sibling that still opens the standard wizard — sets
        # `default_location_id: (ship_back_cond and cust_loc_id) or
        # False`, which evaluates to `False` in the New stage. Passing
        # `default_location_id: False` through to
        # stock.return.picking.create({}) makes Odoo treat location_id
        # as "user-provided" and SKIP _compute_moves_locations entirely,
        # leaving product_return_moves empty and location_id at False —
        # which then trips automation 174 with
        #     "Return Location should be equal to Suggested Return
        #      Location."
        # (This is exactly the failure the user hit through the UI on
        # v212 — RPC calls without the button context worked fine
        # because they never carried default_location_id at all.)
        # Removing the key lets the compute run in full and set
        # location_id to the correct suggested value.
        ctx.pop('default_location_id', None)

        ctx.setdefault(
            'default_ticket_id',
            (self.repair_stage_state == 'new' and self.id) or False,
        )
        # x_studio_pick_id is an integer on helpdesk.ticket (Studio),
        # NOT a many2one — carries the raw picking id (0 when unset).
        # The v199 header-button context passed it as `x_studio_pick_id
        # or False`, treating the integer 0 as falsy. Mirror that here.
        ctx.setdefault(
            'default_picking_id',
            self.x_studio_pick_id or False,
        )
        ctx.setdefault('default_partner_id', self.partner_id.id)
        ctx.setdefault('default_company_id', self.company_id.id)

        # Deliberately do NOT set default_location_id here — Odoo's
        # ORM interprets a value in vals for a stored @api.depends
        # compute field as "already provided" and SKIPS the whole
        # compute method. That's fine for location_id itself, but
        # _compute_moves_locations is a multi-field compute that also
        # populates product_return_moves (the o2m of return lines).
        # Skipping it leaves product_return_moves empty and downstream
        # create_returns raises "Please specify at least one non-zero
        # quantity". Let the compute run in full — its override in
        # stock_return_picking.py sets location_id to the
        # company-appropriate suggested location, matching what
        # automation 174 → server action 1991 validates against.

        # Instantiate the wizard.
        # IMPORTANT: use with_context(ctx) POSITIONALLY — this REPLACES
        # env.context entirely with our sanitised dict. The kwargs form
        # `.with_context(**ctx)` MERGES ctx over env.context, which
        # means the `default_location_id: False` we just popped from
        # ctx gets reintroduced from env.context during the merge. That
        # was the actual v213 bug: my pop was a no-op through the merge
        # because env.context still carried the button-supplied False.
        # Positional replacement is the fix.
        wizard = (
            self.env['stock.return.picking']
                .with_context(ctx)
                .create({})
        )
        # create_returns() is the standard public button handler. It
        # calls _create_returns() (our override rewrites the picking's
        # name and stamps the ticket) and returns the act_window
        # navigating to the new RET picking.
        return wizard.create_returns()

    def fix_repair_action_direct_dispatch(self):
        """One-click Dispatch: skip the stock.return.picking wizard.

        Symmetric to fix_repair_action_direct_return but for the
        item-back-to-customer step. In the interactive Dispatch flow
        the header button deliberately drops default_ticket_id from the
        wizard's context — this makes Studio automation 174's guard
        (`if record.ticket_id`) fail, silently skipping the
        "Return Location should be equal to Suggested Return Location"
        check. We mirror that here: ticket_id is left unset on the
        wizard, and our _create_returns override finds the ticket via
        its picking_id → x_studio_pick_id fallback so the resulting
        picking still gets renamed to <WH>/RET/xxxxx and stamped.

        Precondition: the ticket must already have a stored return
        picking (x_studio_pick_id set to the earlier RET). Without one,
        there's nothing to reverse.
        """
        self.ensure_one()
        if not self.x_studio_pick_id:
            raise UserError(_(
                "Dispatch requires the item to have been collected "
                "first. No return picking is stored on this ticket."
            ))

        ctx = dict(self.env.context)
        # Strip both leaked-from-button keys; we control these explicitly
        # below. default_location_id: False from the button also breaks
        # the compute (same skip-the-compute trap as the Return path).
        ctx.pop('default_location_id', None)
        # Deliberately DO NOT set default_ticket_id — leaving it out
        # keeps automation 174's guard from firing. This mirrors the
        # interactive Dispatch button's context, which also passed
        # default_ticket_id: False for stage != 'new'.
        ctx.pop('default_ticket_id', None)
        ctx.setdefault('default_picking_id', self.x_studio_pick_id)
        ctx.setdefault('default_partner_id', self.partner_id.id)
        ctx.setdefault('default_company_id', self.company_id.id)

        # Use positional with_context to REPLACE env.context (the
        # kwargs form would re-introduce the popped keys via merge).
        wizard = (
            self.env['stock.return.picking']
                .with_context(ctx)
                .create({})
        )
        return wizard.create_returns()

    @api.depends(
        'fsm_task_ids.sale_order_id.invoice_ids.state',
        'fsm_task_ids.sale_order_id.invoice_ids.payment_state',
    )
    def _compute_so_fully_paid(self):
        """True when every linked repair-task SO carries at least one
        non-cancelled invoice AND every non-cancelled invoice on those
        SOs is state='posted' with payment_state in ('in_payment',
        'paid'). Used to gate the Dispatch button — don't hand the
        item back until the customer has settled the repair bill.

        We accept 'in_payment' alongside 'paid' because the customer
        has already handed over the money at that point; bank
        reconciliation is a downstream accounting step that shouldn't
        block operations.

        Prior implementation checked invoice_status == 'invoiced' AND
        amount_unpaid == 0. That combo produced false positives after
        the v163 single-full-invoice flow landed: creating the invoice
        sets qty_invoiced = product_uom_qty on every line so
        invoice_status flips to 'invoiced' immediately, and
        amount_unpaid's compute only sums residuals on POSTED invoices
        — a fresh draft is excluded entirely. So the moment the draft
        invoice existed, so_fully_paid = True and Dispatch appeared
        before the customer had paid anything.

        Checking payment_state directly ties the gate to an event
        that actually reflects money changing hands.
        """
        for ticket in self:
            task_sos = ticket.fsm_task_ids.mapped('sale_order_id')
            if not task_sos:
                ticket.so_fully_paid = False
                continue
            all_paid = True
            for so in task_sos:
                invoices = so.invoice_ids.filtered(lambda i: i.state != 'cancel')
                if not invoices:
                    all_paid = False
                    break
                if not all(
                    inv.state == 'posted'
                    and inv.payment_state in ('in_payment', 'paid')
                    for inv in invoices
                ):
                    all_paid = False
                    break
            ticket.so_fully_paid = all_paid

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
            #
            # Every field referenced in a client-side `invisible=` /
            # `readonly=` / `required=` modifier expression MUST also
            # exist as a <field> element in the view — otherwise the
            # client evaluator raises "Name '<field>' is not defined"
            # at render time. On Jinasena production those fields are
            # visible via Studio's own view inherits; on stand-alone
            # installs the base helpdesk.ticket arch doesn't include
            # them, so we inject invisible sentinels here.
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
                    # v1 on Fields-disable branch: x_ticket_locked
                    # flips True once any repair-flow picking on this
                    # ticket has been validated (state='done'). Used
                    # by the readonly loop below to freeze every
                    # editable field on the form so the intake data
                    # captured before first movement stays a truthful
                    # record.
                    'x_ticket_locked',
                    # v232: fields referenced by the header-button
                    # invisible= expressions written further down.
                    # Client-side modifier eval requires these to
                    # appear in the view so their values are fetched.
                    'x_studio_rug_repair',
                    'x_studio_rug_confirmed',
                    'x_studio_valid_return',
                    'x_studio_serial_no',
                    'x_studio_repair_reason',
                    'x_studio_warranty_card',
                    'x_studio_pick_id',
                    'repair_stage_state',
                    'use_fsm',
                    'fsm_task_count',
                ):
                    if not arch.xpath(f"//field[@name='{fname}']"):
                        fld = etree.Element('field')
                        fld.set('name', fname)
                        fld.set('invisible', '1')
                        sheet.insert(0, fld)
                break

            # Recolour Return (action 195) and Plan Intervention
            # (action_generate_fsm_task) buttons to primary purple.
            # Done here in Python instead of in the XML inherit
            # because both buttons live in downstream inherits
            # (helpdesk_stock adds 195, helpdesk_fsm adds
            # action_generate_fsm_task) — not the direct parent view
            # helpdesk_ticket_views.xml points at. XML xpath fails
            # install-time validation for buttons not in the direct
            # parent; the _get_view Python path operates on the
            # fully-merged arch so the buttons are always resolvable.
            for btn_name in ('195', 'action_generate_fsm_task'):
                for btn_el in arch.xpath(f"//button[@name='{btn_name}']"):
                    btn_el.set('class', 'btn-primary')

            # Freeze all form fields once the first repair movement
            # is done. The workflow buttons in the header (Send to
            # Factory / Received at Factory / etc.), smart buttons
            # (Tasks / Movements), Print gear, and Back / × close
            # actions all stay live because they're not <field>
            # elements. Only data fields get the readonly gate.
            #
            # Preserves any existing readonly expression per field
            # via "(existing) or x_ticket_locked" so field-specific
            # readonly gates (Studio's own, or product_id /
            # user_id above) keep firing before the ticket-level
            # freeze kicks in.
            #
            # xpath scope: direct fields inside <sheet> only, NOT
            # fields nested in another field's embedded view (one2many
            # sub-lists for messages, followers, fsm_task_ids etc.).
            # Subrecords are on other models that don't have
            # x_ticket_locked — stamping the expression on them would
            # raise "Name not defined" when Odoo's ListRenderer
            # evaluates it per-cell (owl lifecycle crash).
            for field_el in arch.xpath(
                    "//sheet//field[not(ancestor::field)]"):
                # Skip fields we've injected purely as markers
                # (invisible=1 with no display) — no user
                # interaction on them, no point stamping readonly.
                if field_el.get('invisible') == '1':
                    continue
                existing = field_el.get('readonly', '')
                extra = 'x_ticket_locked'
                field_el.set(
                    'readonly',
                    f"({existing}) or {extra}" if existing else extra,
                )

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

            # Ticket ID (`name` — displays as REPAIR/YYYY/NNNNN): always
            # readonly. The sequence-based name is assigned by
            # _repair_seq_no_on_create_or_write when the record hits
            # create(), so there's no legitimate reason for the operator
            # to type anything in the title field. Leaving it editable
            # meant a stray keystroke on the New ticket form would
            # override the sequence hook (which only fires when the
            # value is 'New' or empty) and freeze the ticket with an
            # arbitrary human-typed name. Readonly on the arch is
            # simpler and safer than adding create/write guards.
            for field in arch.xpath("//field[@name='name']"):
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
                # Primary purple to match the rest of the repair header
                # buttons (Assign to Me, Return, Dispatch, Plan
                # Intervention, Mark as Done). btn-primary keeps this
                # button visually in the same tier — it's part of the
                # stage-progression flow, not a secondary utility.
                btn.set('class', 'btn-primary')
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
                # Retarget the Return button from action 195 (which opens
                # the stock.return.picking wizard modal) to our own
                # helpdesk.ticket method that runs the wizard flow
                # server-side and returns the act_window landing on the
                # freshly-created RET picking. One click, no popup.
                #
                # Only the Return button is retargeted here — the
                # Dispatch sibling created below still points at action
                # 195 (kept as a fallback for that flow; the wizard
                # opens with a real source picking already selected,
                # which is a slightly different UX shape).
                btn.set('type', 'object')
                btn.set('name', 'fix_repair_action_direct_return')
                # Add Dispatch sibling — bound to our own direct-Dispatch
                # method so the wizard popup is skipped for that step too.
                # v215 change: was action 195 (opens the standard wizard);
                # now points at fix_repair_action_direct_dispatch which
                # reproduces the interactive Dispatch context (ticket_id
                # unset, picking_id = x_studio_pick_id, location_id
                # deferred to super's compute = Customers) programmatically.
                dispatch = etree.Element('button')
                dispatch.set('name', 'fix_repair_action_direct_dispatch')
                dispatch.set('string', 'Dispatch')
                dispatch.set('type', 'object')
                # Match the Return / Assign to Me / Plan Intervention
                # header buttons — all primary purple accent — instead of
                # inheriting whatever class the Return button happens to
                # carry at this point. Fixes a subtle fragility: if a
                # future edit removes v200's Return recolour above,
                # Dispatch would silently regress to whatever class
                # Studio left on the base Return.
                dispatch.set('class', 'btn-primary')
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

        v273: same-warehouse fallback (see
        _create_received_at_factory_picking for full rationale). When
        centre == factory, centre.Intransit collides with the current
        source. Fall back to centre.warehouse.lot_stock_id so the
        movement is still recorded.
        """
        self.ensure_one()
        src_loc = self._current_item_location()
        anchor = self.x_studio_return_receipt_location
        if not (src_loc and anchor and anchor.warehouse_id):
            return False
        wh = anchor.warehouse_id
        dest_loc = wh._ensure_intransit_location()
        if not dest_loc or src_loc == dest_loc:
            dest_loc = wh.lot_stock_id
        if not dest_loc or src_loc == dest_loc:
            return False
        return self._create_repair_transfer(src_loc, dest_loc)

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
        """current location (centre/Intransit) -> factory warehouse/Intransit.

        v273: same-warehouse fallback. When the centre and factory
        resolve to the same warehouse (common on dev / demo envs with a
        single Jinasena-style warehouse), factory.Intransit collides
        with the current source (already at centre.Intransit from
        Send to Factory). Falling back to factory.warehouse.lot_stock_id
        preserves the movement log so the ticket's Movements smart
        button shows all buttons' pickings. Clear-DB (centre != factory
        always) never triggers the fallback.
        """
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
        wh = anchor.warehouse_id
        dest_loc = wh._ensure_intransit_location()
        if not dest_loc or src_loc == dest_loc:
            dest_loc = wh.lot_stock_id
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
        #
        # v272: active_test=False. Bare Odoo installs sometimes ship
        # the default warehouse's Internal Transfers picking type in
        # an inactive state — the ORM's implicit active=True filter
        # would then hide it and every repair-flow picking would
        # silently no-op. activate_internal_picking_types(env) in
        # hooks.py also flips those types active=True at install /
        # upgrade time, so both layers are covered.
        PickType = self.env['stock.picking.type'].sudo().with_context(
            active_test=False,
        )
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
        # industry_fsm_stock auto-sets group_id on stock.move when a task
        # is active in context (e.g. inside action_fsm_validate). That
        # makes the picking show up on the task's SO Delivery smart
        # button, which we don't want — repair-flow pickings live on the
        # ticket via x_studio_helpdesk_ticket_id, not on the SO.
        # Strip default_group_id from the env so the auto-binding hook
        # has nothing to use.
        env_no_group = self.env(
            context={**self.env.context, 'default_group_id': False}
        )
        picking = env_no_group['stock.picking'].sudo().create({
            'partner_id': self.partner_id.id,
            'picking_type_id': pick_type.id,
            'location_id': source_loc.id,
            'location_dest_id': dest_loc.id,
            'company_id': self.company_id.id,
            'date_done': now,
            'x_studio_helpdesk_ticket_id': self.id,
            'group_id': False,
        })
        # Do NOT pass `quantity=1.0` here. In Odoo 17 that field on
        # stock.move auto-materializes a move_line; if we then create
        # our own move_line (to carry lot_id/qty_done), the move ends up
        # with two ML records and move.quantity computes to 2.
        move = env_no_group['stock.move'].sudo().create({
            'name': product.display_name,
            'product_id': product.id,
            'product_uom_qty': 1.0,
            'product_uom': product.uom_id.id,
            'location_id': source_loc.id,
            'location_dest_id': dest_loc.id,
            'picking_id': picking.id,
            'company_id': self.company_id.id,
            'date': now,
            'group_id': False,
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
        # Defensive re-clear: if any cascade between create and now set
        # group_id (e.g. via an inverse on a related field), strip it
        # before state='done' so picking.sale_id stays False and the SO
        # never sees this picking on its Delivery smart button.
        if picking.group_id:
            picking.sudo().write({'group_id': False})
        if move.group_id:
            move.sudo().write({'group_id': False})
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

    # ─────────────────────────────────────────────────────────────────
    # Studio server actions — Python delegations (Tier 1: automations)
    # ─────────────────────────────────────────────────────────────────
    # Native Python ports of the four base-automation-triggered
    # Studio server actions on helpdesk.ticket. The
    # `_delegate_studio_server_actions_to_native` migration rewrites
    # each ir.actions.server.code string to a one-line delegation
    # into these methods, so:
    #   1. base.automation → ir.actions.server relationship
    #      preserved (no changes to automation records)
    #   2. safe_eval is called only on the one-line delegation,
    #      not on the full logic — biggest perf win for hot-path
    #      automations (on_create_or_write, on_change, on_unlink)
    #   3. The logic runs at native Python speed, is testable,
    #      and lives in version control.
    #
    # Behaviour ported verbatim from Studio's code strings; only
    # `env` → `self.env`, `record` → `self`, and `record['x'] =`
    # → `self.x =` style adaptations.

    def _repair_seq_no_on_create_or_write(self):
        """Replaces server action id 1976 (automation 171
        'JIN-Helpdesk(Repair) Seq.No'). Assigns a sequence number to
        newly-created tickets whose name is still the sentinel 'New'
        OR empty (missing).

        v220 broadened the trigger from just == 'New' to also catch
        empty names. The paired _get_view change makes the name field
        readonly on the form, so the user can no longer type a value
        into it — which means new tickets arrive at create() with
        whatever the default provides (empty, in the absence of a
        Studio default). Without this broadening, those would slip
        past the sequence assignment and land with a blank name.
        """
        for record in self:
            if not record.name or record.name == 'New':
                seq = self.env['ir.sequence'].next_by_code('repair.seq')
                if seq:
                    record.write({'name': seq})

    def _repair_populate_repair_location(self):
        """Replaces server action id 2000 (automation 178
        'RR - Auto Populate Repair Location'). Mirrors
        x_studio_return_receipt_location onto x_studio_repair_location.
        """
        for record in self:
            if record.x_studio_return_receipt_location:
                record.x_studio_repair_location = record.x_studio_return_receipt_location
            else:
                record.x_studio_repair_location = False

    def _repair_validate_cancelled_on_unlink(self):
        """Replaces server action id 2222 (automation 201
        'RR - Validate Cancelled Tickets'). Blocks unlink on
        tickets flagged as cancelled.
        """
        for record in self:
            if record.x_studio_cancelled:
                raise UserError('Cancelled tickets can not be deleted.')

    def _repair_auto_select_product_for_rug(self):
        """Replaces server action id 1989 (automation 172
        'RR - Auto Select Product for RUG Repairs').

        When a serial number is set on the ticket, look up the
        outgoing move-line that shipped that serial to a customer,
        pull the source Sales Order + picking, and populate the
        ticket's sale_order_id / picking refs / product / lot.
        Behaviour ported verbatim from Studio.
        """
        for record in self:
            if record.x_studio_serial_no:
                company_id = self.env.context.get(
                    'allowed_company_ids', [self.env.user.company_id.id]
                )[0]
                company = self.env['res.company'].browse(company_id)

                cust_location = self.env['stock.location'].search([
                    ('usage', '=', 'customer'),
                ], limit=1)
                trans_line = self.env['stock.move.line'].search([
                    ('product_id', '=', record.x_studio_serial_no.product_id.id),
                    ('lot_id', '=', record.x_studio_serial_no.id),
                    ('picking_code', '=', 'outgoing'),
                    ('location_dest_id', '=', cust_location.id),
                    ('company_id', '=', company.id),
                ], limit=1)
                if trans_line:
                    so = self.env['sale.order'].search([
                        ('name', '=', trans_line.origin),
                        ('company_id', '=', company.id),
                    ], limit=1)
                    if so:
                        record.sale_order_id = so.id
                        record.x_studio_picking_id = trans_line.picking_id.id
                        record.x_studio_pick_id = trans_line.picking_id.id

                record.product_id = record.x_studio_serial_no.product_id.id
                record.lot_id = record.x_studio_serial_no.id

                if record.x_studio_normal_repair_without_serial_no:
                    record.sale_order_id = False
            else:
                if record.x_studio_normal_repair_without_serial_no:
                    record.sale_order_id = False
                    record.x_studio_picking_id = False
                    record.x_studio_pick_id = False
                    record.lot_id = False
                else:
                    record.sale_order_id = False
                    record.x_studio_picking_id = False
                    record.x_studio_pick_id = False
                    record.product_id = False
                    record.lot_id = False

    # ─────────────────────────────────────────────────────────────────
    # Studio server actions — Python delegations (Tier 2: buttons)
    # ─────────────────────────────────────────────────────────────────
    # Six button-triggered Studio server actions for the core repair
    # workflow (Send/Receive Factory/Centre + Cancel/Reopen). These
    # buttons live on Studio's helpdesk.ticket form arch and are
    # attached to `ir_actions_server` records via type="action"
    # name="<action_id>".
    #
    # Note: Fix-repair already has native action_* methods for
    # send/receive factory/centre that ALSO create stock pickings.
    # Those are called from Fix-repair's own buttons (added via
    # view inheritance). The Studio buttons DON'T create pickings;
    # they only flip flags + stage + audit timestamps. Keeping the
    # two paths distinct (Studio button = audit only; Fix-repair
    # button = full workflow) preserves the original behaviour.

    def _repair_studio_send_to_factory(self):
        """Studio server action id 2001 native port."""
        for record in self:
            if not record.id:
                continue
            company_id = self.env.context.get(
                'allowed_company_ids', [self.env.user.company_id.id]
            )[0]
            company = self.env['res.company'].browse(company_id)
            factory_location = self.env['stock.location'].search([
                ('x_studio_repair_factory_location', '=', True),
            ], limit=1)
            if not factory_location:
                raise UserError(
                    "Setup Repair Factory Location in stock locations to proceed."
                )
            now = datetime.datetime.now()
            record.write({
                'x_studio_repair_location': factory_location.id,
                'x_studio_send_to_factory': True,
                'x_studio_s_shipped_date': now,
                'x_studio_s_shipped_by': self.env.uid,
                'x_studio_stage_date': now,
                'x_studio_created_by_1': self.env.uid,
                'x_studio_created_on_1': now,
                'stage_id': 5 if company.id == 1 else 24,
            })

    def _repair_studio_receive_at_factory(self):
        """Studio server action id 2002 native port."""
        for record in self:
            if not record.id:
                continue
            company_id = self.env.context.get(
                'allowed_company_ids', [self.env.user.company_id.id]
            )[0]
            company = self.env['res.company'].browse(company_id)
            now = datetime.datetime.now()
            record.write({
                'x_studio_receive_at_factory': True,
                'x_studio_f_received_date': now,
                'x_studio_f_received_by': self.env.uid,
                'x_studio_stage_date': now,
                'x_studio_created_by_2': self.env.uid,
                'x_studio_created_on_2': now,
                'stage_id': 6 if company.id == 1 else 25,
            })

    def _repair_studio_send_to_sales_centre(self):
        """Studio server action id 2007 native port."""
        for record in self:
            if not record.id:
                continue
            company_id = self.env.context.get(
                'allowed_company_ids', [self.env.user.company_id.id]
            )[0]
            company = self.env['res.company'].browse(company_id)
            now = datetime.datetime.now()
            record.write({
                'x_studio_send_to_centre': True,
                'x_studio_f_shipped_date': now,
                'x_studio_f_shipped_by': self.env.uid,
                'x_studio_stage_date': now,
                'x_studio_created_by_9': self.env.uid,
                'x_studio_created_on_9': now,
                'stage_id': 7 if company.id == 1 else 26,
            })

    def _repair_studio_receive_at_sales_centre(self):
        """Studio server action id 2006 native port."""
        for record in self:
            if not record.id:
                continue
            company_id = self.env.context.get(
                'allowed_company_ids', [self.env.user.company_id.id]
            )[0]
            company = self.env['res.company'].browse(company_id)
            now = datetime.datetime.now()
            record.write({
                'x_studio_receive_at_centre': True,
                'x_studio_s_received_date': now,
                'x_studio_s_received_by': self.env.uid,
                'x_studio_stage_date': now,
                'x_studio_created_by_10': self.env.uid,
                'x_studio_created_on_10': now,
                'stage_id': 8 if company.id == 1 else 27,
            })

    def _repair_studio_cancel_repair(self):
        """Studio server action id 2220 native port."""
        for record in self:
            if not record.id:
                continue
            company_id = self.env.context.get(
                'allowed_company_ids', [self.env.user.company_id.id]
            )[0]
            company = self.env['res.company'].browse(company_id)
            if not record.x_studio_cancel_reason:
                raise UserError('Cancel reason must be specified.')
            record.write({
                'x_studio_cancelled_stage_id': record.stage_id.id,
                'stage_id': 4 if company.id == 1 else 23,
                'x_studio_cancelled': True,
                'x_studio_reopened': False,
                'x_studio_cancelled_by': self.env.uid,
                'x_studio_cancelled_date': datetime.datetime.now(),
                'x_studio_cancel_status': 'Cancelled',
            })

    def _repair_studio_reopen_repair(self):
        """Studio server action id 2221 native port."""
        for record in self:
            if not record.id:
                continue
            record.write({
                'stage_id': record.x_studio_cancelled_stage_id.id,
                'x_studio_cancelled': False,
                'x_studio_reopened': True,
                'x_studio_cancelled_stage_id': False,
                'x_studio_reopened_by': self.env.uid,
                'x_studio_reopened_date': datetime.datetime.now(),
                'x_studio_reopen_status': 'Reopened',
            })

    # ─────────────────────────────────────────────────────────────────
    # Studio server actions — Python delegations (Tier 3: heavy)
    # ─────────────────────────────────────────────────────────────────
    # The two biggest Studio server actions: Auto Create Repair Route
    # (id 1993, ~3.1 KB) and Auto Create Repair Serial Nos (id 1994,
    # ~3.3 KB). Both create a done "return to customer" stock.picking
    # with a linked stock.move + stock.move.line. The Serial Nos
    # variant additionally allocates a new stock.lot via the
    # 'repair.serial.seq' sequence.
    #
    # Both actions raise UserError early if the user's virtual /
    # source location isn't configured (company-specific fields:
    # _virtual_location / _source_location for company 1;
    # _virtual_location_1 / _source_location_1 for others).

    def _repair_studio_auto_create_repair_route(self):
        """Studio server action id 1993 native port."""
        for record in self:
            if not record.id:
                continue
            company_id = self.env.context.get(
                'allowed_company_ids', [self.env.user.company_id.id]
            )[0]
            company = self.env['res.company'].browse(company_id)

            if company.id == 1:
                if not record.x_studio_virtual_location:
                    raise UserError(
                        'Virtual Location must be setup for Current Logged in User.'
                    )
                if not record.x_studio_source_location:
                    raise UserError(
                        'Source Location must be setup for Current Logged in User.'
                    )
                virtual_loc = record.x_studio_virtual_location.id
                source_loc = record.x_studio_source_location.id
            else:
                if not record.x_studio_virtual_location_1:
                    raise UserError(
                        'Virtual Location must be setup for Current Logged in User.'
                    )
                if not record.x_studio_source_location_1:
                    raise UserError(
                        'Source Location must be setup for Current Logged in User.'
                    )
                virtual_loc = record.x_studio_virtual_location_1.id
                source_loc = record.x_studio_source_location_1.id

            record.x_studio_repair_serial_created = True
            dest_loc = self.env['stock.location'].search([
                ('usage', '=', 'customer'),
            ], limit=1)
            if not dest_loc:
                continue

            opt_type = self.env['stock.picking.type'].search([
                ('default_location_src_id', '=',
                    record.x_studio_return_receipt_location.id),
                ('code', '=', 'outgoing'),
                ('company_id', '=', company.id),
            ], limit=1)
            if not opt_type:
                raise UserError('The selected return receipt location is not correct.')

            prod_move = self.env['stock.picking'].create({
                'x_studio_created_from_help_ticket': record.id,
                'x_studio_helpdesk_ticket_id': record.id,
                'picking_type_id': opt_type.id,
                'location_id': source_loc,
                'location_dest_id': dest_loc.id,
                'company_id': company.id,
                # v255: stamp the ticket's partner so helpdesk_stock's
                # has_partner_picking compute (used to gate the Return
                # button) treats this synthetic delivery as a real
                # prior delivery to the partner. Clear-DB masks the
                # absence of this because their cash-customer partner
                # has thousands of pre-existing done deliveries — on
                # standalone we can't lean on that.
                'partner_id': record.partner_id.id if record.partner_id else False,
            })
            update_prod_move = self.env['stock.picking'].search([
                ('id', '=', prod_move.id),
                ('company_id', '=', company.id),
            ], limit=1)
            if update_prod_move:
                stock_move = self.env['stock.move'].create({
                    'picking_id': update_prod_move.id,
                    'name': 'New Move:' + record.product_id.name,
                    'reference': update_prod_move.name,
                    'picking_type_id': update_prod_move.picking_type_id.id,
                    'product_id': record.product_id.id,
                    'location_id': update_prod_move.location_id.id,
                    'location_dest_id': update_prod_move.location_dest_id.id,
                    'product_uom_qty': 1.00,
                    'product_uom': record.product_id.uom_id.id,
                    'state': 'done',
                    'company_id': company.id,
                })
                self.env['stock.move.line'].create({
                    'move_id': stock_move.id,
                    'picking_id': update_prod_move.id,
                    'picking_type_id': update_prod_move.picking_type_id.id,
                    'product_id': record.product_id.id,
                    'product_uom_id': record.product_id.uom_id.id,
                    'location_id': update_prod_move.location_id.id,
                    'location_dest_id': update_prod_move.location_dest_id.id,
                    'qty_done': 1.00,
                    'company_id': company.id,
                })
                update_prod_move.write({'state': 'done'})

            record.x_studio_picking_id = prod_move.id
            record.x_studio_pick_id = prod_move.id

    # ─────────────────────────────────────────────────────────────────
    # Studio server actions — Python delegations (Tier 4: emails)
    # ─────────────────────────────────────────────────────────────────
    # Five email actions (Customer Letter + 4 Final Notice variants).
    # All share the same pattern: guard on stage_id == 13
    # (Handed Over to Customer), search the mail.template by id,
    # send with recipient = partner, log message. Only the template
    # id varies (56, 66, 67, 69, 70).
    #
    # The 'Repair Customer Letter has been sent to customer:'
    # message body is the same string across all five actions in
    # Studio — semantically inaccurate for the Final Notice variants
    # but preserved verbatim per the migration rule.

    def _repair_send_stage13_email(self, template_id):
        """Shared helper for the five 'send letter at stage=13' actions."""
        for record in self:
            if record.stage_id.id != 13:
                raise UserError(
                    'The repaired item should be handed over to customer to send the report.'
                )
            template = self.env['mail.template'].search([
                ('id', '=', template_id),
            ], limit=1)
            if template:
                template.send_mail(record.id, force_send=True, email_values={
                    'recipient_ids': [record.partner_id.id],
                })
                record.message_post(
                    body='Repair Customer Letter has been sent to customer: '
                         + str(record.partner_id.name)
                )

    def _repair_send_customer_letter(self):
        """Studio server action id 2269 native port (template 56)."""
        self._repair_send_stage13_email(56)

    def _repair_send_final_notice(self):
        """Studio server action id 2308 native port (template 66)."""
        self._repair_send_stage13_email(66)

    def _repair_send_final_notice_estimated(self):
        """Studio server action id 2309 native port (template 67)."""
        self._repair_send_stage13_email(67)

    def _repair_send_final_notice_scrappage(self):
        """Studio server action id 2310 native port (template 69)."""
        self._repair_send_stage13_email(69)

    def _repair_send_reminding_letter(self):
        """Studio server action id 2311 native port (template 70)."""
        self._repair_send_stage13_email(70)

    # ─────────────────────────────────────────────────────────────────
    # Studio server actions — Python delegations (Tier 5: variants)
    # ─────────────────────────────────────────────────────────────────
    # Remaining actions: RUG "Auto Select" duplicates (1989 variants),
    # Cancel Repair-2 variant of 2220, Change Repair Type to RUG,
    # User Location Validation, and the object_write action 1998.

    def _repair_auto_select_product_for_rug_no_company(self, sn_updated=False):
        """Shared helper for Studio server actions 1990 and 2450.
        Both are variants of 1989 that drop the ('company_id', ...)
        filter from the outgoing stock.move.line search domain.
        2450 additionally flips x_studio_sn_updated=True at the end.
        """
        for record in self:
            if record.x_studio_serial_no:
                company_id = self.env.context.get(
                    'allowed_company_ids', [self.env.user.company_id.id]
                )[0]
                company = self.env['res.company'].browse(company_id)

                cust_location = self.env['stock.location'].search([
                    ('usage', '=', 'customer'),
                ], limit=1)
                trans_line = self.env['stock.move.line'].search([
                    ('product_id', '=', record.x_studio_serial_no.product_id.id),
                    ('lot_id', '=', record.x_studio_serial_no.id),
                    ('picking_code', '=', 'outgoing'),
                    ('location_dest_id', '=', cust_location.id),
                ], limit=1)
                if trans_line:
                    so = self.env['sale.order'].search([
                        ('name', '=', trans_line.origin),
                        ('company_id', '=', company.id),
                    ], limit=1)
                    if so:
                        record.sale_order_id = so.id
                        record.x_studio_picking_id = trans_line.picking_id.id
                        record.x_studio_pick_id = trans_line.picking_id.id

                record.product_id = record.x_studio_serial_no.product_id.id
                record.lot_id = record.x_studio_serial_no.id

                if record.x_studio_normal_repair_without_serial_no:
                    record.sale_order_id = False
            else:
                if record.x_studio_normal_repair_without_serial_no:
                    record.sale_order_id = False
                    record.x_studio_picking_id = False
                    record.x_studio_pick_id = False
                    record.lot_id = False
                else:
                    record.sale_order_id = False
                    record.x_studio_picking_id = False
                    record.x_studio_pick_id = False
                    record.product_id = False
                    record.lot_id = False

            if sn_updated:
                record.x_studio_sn_updated = True

    def _repair_auto_select_product_for_rug_2(self):
        """Studio server action id 1990 native port."""
        self._repair_auto_select_product_for_rug_no_company(sn_updated=False)

    def _repair_auto_select_product_for_rug_22(self):
        """Studio server action id 2450 native port."""
        self._repair_auto_select_product_for_rug_no_company(sn_updated=True)

    def _repair_auto_select_product_for_rug_33(self):
        """Studio server action id 2451 native port. Unconditionally
        clears sale_order_id + picking refs + product + lot +
        sn_updated flag."""
        for record in self:
            record.write({
                'sale_order_id': False,
                'x_studio_picking_id': False,
                'x_studio_pick_id': False,
                'product_id': False,
                'lot_id': False,
                'x_studio_sn_updated': False,
            })

    def _repair_auto_select_product_for_rug_4(self):
        """Studio server action id 1992 native port. Clears
        sale_order_id + picking refs + product + lot + serial_no
        when ticket_type_id is set."""
        for record in self:
            if record.ticket_type_id:
                record.write({
                    'sale_order_id': False,
                    'x_studio_picking_id': False,
                    'x_studio_pick_id': False,
                    'product_id': False,
                    'lot_id': False,
                    'x_studio_serial_no': False,
                })

    def _repair_studio_cancel_repair_2(self):
        """Studio server action id 2343 native port. Variant of
        Cancel Repair (2220) that flips repair_complete_stage_updated
        and moves to stage 9/28 (Repair Completed per company) using
        audit slot 8 — semantically a 'cancel + close as completed'."""
        for record in self:
            if not record.id:
                continue
            company_id = self.env.context.get(
                'allowed_company_ids', [self.env.user.company_id.id]
            )[0]
            company = self.env['res.company'].browse(company_id)
            if not record.x_studio_cancel_reason:
                raise UserError('Cancel reason must be specified.')
            now = datetime.datetime.now()
            record.write({
                'x_studio_repair_complete_stage_updated': True,
                'stage_id': 9 if company.id == 1 else 28,
                'x_studio_stage_date': now,
                'x_studio_created_by_8': self.env.uid,
                'x_studio_created_on_8': now,
                'x_studio_cancelled_2': True,
                'x_studio_cancel_status': 'Cancelled',
            })

    def _repair_studio_change_repair_type_to_rug(self):
        """Studio server action id 2159 native port. Requires the
        warranty card to be uploaded, rewrites each linked SO line's
        price_unit to the product's standard_price (saving the
        original in x_studio_price_unit_original), and flips
        ticket_type_id to 1 (the RUG type)."""
        for record in self:
            if not record.x_studio_warranty_card:
                raise UserError('Warranty Card Document must be Uploaded!')
            for sos in record.fsm_task_ids:
                so = self.env['sale.order'].search([
                    ('id', '=', sos.sale_order_id.id),
                ], limit=1)
                if so:
                    for so_line in so.order_line:
                        original_price = so_line.price_unit
                        so_line.write({
                            'price_unit': so_line.product_template_id.standard_price,
                            'x_studio_price_unit_original': original_price,
                        })
            record.write({'ticket_type_id': 1})

    def _repair_studio_user_location_validation(self):
        """Studio server action id 2558 native port. Guards that the
        current user has access to the ticket's return-receipt
        location. Raises UserError with details of allowed warehouses
        (or a distinct message when none are permitted) if access is
        denied. Admin (uid=1) is exempted."""
        for record in self:
            if self.env.uid == 1:
                continue
            if record.x_studio_user_location_validation:
                warehouse = str(record.x_studio_return_receipt_location.complete_name)
                loc = self.env['stock.location'].search([
                    ('x_studio_users_stock_location', 'ilike', self.env.uid),
                    ('active', '=', True),
                ])
                if loc:
                    locations = ''
                    for locs in loc:
                        locations += str(locs.complete_name + '\n')
                    raise UserError(
                        'The current logged-in user does not have access to below listed warehouse.'
                        + '\n\n' + 'Repair Location:' + '\n' + warehouse
                        + '\n\n' + 'Only the below listed stock warehouses are permitted for the current logged-in user for repair module.'
                        + '\n\n' + locations
                    )
                else:
                    raise UserError(
                        'The current logged-in user does not have access to below listed warehouse.'
                        + '\n\n' + 'Repair Location:' + '\n' + warehouse
                        + '\n\n' + 'There are no permitted stock warehouses set up for the current logged-in user for repair module.'
                    )

    def _repair_studio_update_rug_approval_in_pipeline(self):
        """Studio server action id 1998 native port. Originally
        state='object_write' with an empty code body — the action's
        actual behaviour is defined by the ir.actions.server's
        update_field_id / update_related_model_id / value columns
        (native ORM write, no safe_eval). Providing a Python
        placeholder here so any code that may reference this
        method by name resolves, and in case the object_write config
        needs a code-equivalent in the future.

        No-op by default. If/when the object_write config's target
        + value are known, replicate them here as a record.write().
        """
        return

    # ─────────────────────────────────────────────────────────────────
    # Studio automations — Python model hooks
    # ─────────────────────────────────────────────────────────────────
    # Convert the four helpdesk.ticket base.automations to native
    # Python create/write/unlink/onchange overrides on the model.
    # Each hook calls the same _repair_* method the base.automation
    # already delegates to via its server action, so behaviour is
    # preserved 1:1. The automations themselves get deactivated by
    # _deactivate_migrated_ticket_automations so they don't fire in
    # parallel with the Python hooks.

    @api.model_create_multi
    def create(self, vals_list):
        """Replaces automation 171 'JIN-Helpdesk(Repair) Seq.No'
        (on_create_or_write, trigger_field_ids=[create_date]).

        `on_create_or_write` with a trigger_field of create_date is
        effectively a fire-on-create-only pattern — create_date
        never changes after creation. Native equivalent: run the
        seq assignment on create only.
        """
        records = super().create(vals_list)
        records._repair_seq_no_on_create_or_write()
        return records

    def unlink(self):
        """Replaces automation 201 'RR - Validate Cancelled Tickets'
        (on_unlink, filter_domain=[('x_studio_cancelled','=',True)]).

        The _repair_validate_cancelled_on_unlink method already
        checks x_studio_cancelled per-record, so the filter domain
        guard is implicit — non-cancelled tickets pass through.
        """
        self._repair_validate_cancelled_on_unlink()
        return super().unlink()

    @api.onchange('ticket_type_id', 'x_studio_serial_number')
    def _onchange_repair_auto_select_product_for_rug(self):
        """Replaces automation 172 'RR - Auto Select Product for RUG
        Repairs' (on_change, on_change_field_ids=[ticket_type_id,
        x_studio_serial_number]).

        Note: the automation triggers on x_studio_serial_number
        (the duplicate slot), but the underlying logic reads
        x_studio_serial_no (the primary field). Both are preserved
        verbatim from Studio.
        """
        self._repair_auto_select_product_for_rug()

    @api.onchange('x_studio_return_receipt_location')
    def _onchange_repair_populate_repair_location(self):
        """Replaces automation 178 'RR - Auto Populate Repair
        Location' (on_change, on_change_field_ids=[
        x_studio_return_receipt_location]).
        """
        self._repair_populate_repair_location()

    @api.model
    def _deactivate_migrated_ticket_automations(self):
        """Deactivate the four base.automation records whose
        behaviour has moved into native Python create/write/unlink/
        onchange overrides on helpdesk.ticket. Idempotent — skips
        automations that are already inactive.

        The base.automation records + their ir.actions.server records
        are NOT deleted — kept for reference so anyone tracing the
        old trigger flow can see the linkage. Only `active` gets
        flipped to False.

        Automations deactivated:
          171 'JIN-Helpdesk(Repair) Seq.No'         → create() hook
          172 'RR - Auto Select Product for RUG'    → onchange hook
          178 'RR - Auto Populate Repair Location'  → onchange hook
          201 'RR - Validate Cancelled Tickets'     → unlink() hook
        """
        Automation = self.env['base.automation'].sudo()
        ids_to_deactivate = [171, 172, 178, 201]
        autos = Automation.browse(ids_to_deactivate).exists()
        active_autos = autos.filtered(lambda a: a.active)
        if active_autos:
            active_autos.write({'active': False})

    @api.model
    def _deactivate_migrated_other_automations(self):
        """Deactivate the remaining 8 base.automation records that
        target models other than helpdesk.ticket. Each one now has a
        corresponding native Python create/write hook on its target
        model.

        Automations deactivated:
          329 'JIN Company Id in Helpdesk Stage'    → helpdesk.stage.create()
          331 'JIN Company Id in Repair Accounts'   → x_repair_accounts.create()
          302 'JIN Company Id in Repair Reason'     → x_repair_reason.create()
          303 'JIN Company Id in Repair Reason - Customer'
                                                    → x_repair_reason_custom.create()
          306 'JIN Company Id in Repair Stages'     → x_repair_stages.create()
          304 'JIN Company Id in Repair Sub Reason' → x_repair_sub_reason.create()
          179 'RR Auto Update Helpdesk Pipeline Status - 1'
                                                    → project.task.create()
          250 'Super User Validate'                 → res.users.create()/write()
        """
        Automation = self.env['base.automation'].sudo()
        ids_to_deactivate = [329, 331, 302, 303, 306, 304, 179, 250]
        autos = Automation.browse(ids_to_deactivate).exists()
        active_autos = autos.filtered(lambda a: a.active)
        if active_autos:
            active_autos.write({'active': False})

    @api.model
    def _migrate_studio_leftover_repair_fields(self):
        """v159 → v162. Complete the leftover-field ownership
        migration, this time with Python declarations backing it.

        v159/v160 flipped state='manual' → 'base' on these 11
        fields but never added the corresponding fields.X(...)
        declarations in Fix-repair models — so Odoo's registry
        loader looked for state='base' Python definitions and
        found none, dropping the fields from the model and
        breaking every view that referenced them. v161 rolled
        state back to 'manual' as a hotfix.

        v162 adds real Python declarations in res_users.py and
        project_task.py (ttype, related chain, store, selection
        choices, and the two @api.depends computes for
        x_studio_valid_diagnosis and
        x_studio_incomplete_delivery_available, ported from
        Studio's compute strings), so the state flip below now
        resolves cleanly.

        Same idempotent shape as Cluster 1–8:
          - Flip ir.model.fields.state 'manual' → 'base' via SQL
            (ORM write is blocked by @api.constrains on some
            configurations — same reason we used SQL for
            ir.model.state during the catalogue migration).
          - Data columns untouched.
          - Studio pins on these fields were already unlinked in
            v159; harmless if a stale row survives, so no cleanup
            needed here.

        Rows already state='base' are skipped.
        """
        clusters = {
            'res.users': (
                'x_studio_super_user',
                'x_studio_super_user_melt_items',
            ),
            'project.task': (
                'x_studio_cancelled',
                'x_studio_created_date',
                'x_studio_diagnosis_ids',
                'x_studio_incomplete_delivery_available',
                'x_studio_priority',
                'x_studio_quotation_type',
                'x_studio_related_information',
                'x_studio_valid_diagnosis',
                'x_studio_warranty_card',
            ),
        }
        Field = self.env['ir.model.fields'].sudo()
        Data = self.env['ir.model.data'].sudo()
        for model, names in clusters.items():
            rows = Field.search([
                ('model', '=', model),
                ('name', 'in', list(names)),
            ])
            manual_rows = rows.filtered(lambda f: f.state == 'manual')
            if manual_rows:
                self.env.cr.execute(
                    "UPDATE ir_model_fields SET state = 'base' "
                    "WHERE id IN %s",
                    (tuple(manual_rows.ids),),
                )
                manual_rows.invalidate_recordset(['state'])
            studio_pins = Data.search([
                ('model', '=', 'ir.model.fields'),
                ('res_id', 'in', rows.ids),
                ('module', '=', 'studio_customization'),
            ])
            if studio_pins:
                studio_pins.unlink()

    @api.model
    def _repin_delegated_server_actions_to_native(self):
        """v159 — companion to _delegate_studio_server_actions_to_native.

        The delegation table rewrote each action's `code` to a one-
        line native Python call, but left the record's ir.model.data
        pin under module='studio_customization'. Studio's UI still
        shows these actions as its own even though every line of
        their code lives in Fix-repair Python.

        Repin the 9 delegated action records that are still Studio-
        pinned (Repair Seq No, Super User Validate, User Location
        Validation, and the 6 'JIN Company Id' catalogue actions).
        Same shape as the view / report repins: keep the record id,
        change the pin's module to 'Fix-repair', give it a stable
        deterministic slug so the migration is idempotent.

        Idempotent — pins already under 'Fix-repair' are skipped.
        """
        delegated_action_ids = (
            1976,  # RR Repair Seq No
            2544,  # Super User Validate
            2558,  # User Location Validation
            2666,  # JIN Company Id in Repair Reason
            2667,  # JIN Company Id in Repair Reason - Customer
            2668,  # JIN Company Id in Repair Sub Reason
            2670,  # JIN Company Id in Repair Stages
            2760,  # JIN Company Id in Helpdesk Stage
            2790,  # JIN Company Id in Repair Accounts
        )
        Data = self.env['ir.model.data'].sudo()
        pins = Data.search([
            ('model', '=', 'ir.actions.server'),
            ('module', '=', 'studio_customization'),
            ('res_id', 'in', list(delegated_action_ids)),
        ])
        if not pins:
            return
        for pin in pins:
            slug = 'action_%s' % pin.res_id
            # Guard: already migrated on a prior run.
            existing = Data.search([
                ('module', '=', 'Fix-repair'),
                ('name', '=', slug),
                ('model', '=', 'ir.actions.server'),
            ], limit=1)
            if existing:
                pin.unlink()
                continue
            pin.write({
                'module': 'Fix-repair',
                'name': slug,
                'noupdate': True,
            })

    @api.model
    def _sanitize_broken_studio_task_form_xpath(self):
        """v155–v157 hotfix, iterated. Studio's arch on view 3019
        (Odoo Studio: project.task.form customization, Fix-repair-
        owned since v152) uses fragile positional xpaths and two
        sibling-chain button targets. web_studio's _get_view
        override silently swallowed the failures; under Fix-repair
        ownership every raise propagates and blocks task-form
        loads *and* module upgrades.

        Iterating one broken xpath at a time turned into a losing
        game (v155 caught action_fsm_create_quotation, v156 caught
        action_fsm_view_material, upgrade then surfaced the
        positional sale_order_id xpath, and there are more
        positional ones queued behind it). Rewrite the whole
        arch_db in one pass with robust name-based xpaths, dropping
        the two sibling-chain button changes that project_task.py
        _get_view already replicates.

        Uses raw SQL to bypass ir.ui.view.write()'s _check_xml
        validator — the validator combines the *live* combined
        arch during the upgrade transaction, which can transiently
        reference not-yet-migrated views and raise on unrelated
        state. Once the SQL update lands and we invalidate the
        cached arch, the next combine sees only clean name-based
        xpaths and every task-form load succeeds.

        Semantics preserved:
          - The 3 repair-workflow buttons (View Repair Diagnosis
            Validation, View Repair Image Validation, Tested OK)
            still get injected after //field[@name=
            'personal_stage_type_id'].
          - user_ids → 'Assignees' rename and helpdesk_ticket_id /
            x_studio_created_date / x_studio_repair_reason fields
            still land after //field[@name='user_ids'].
          - sale_order_id visibility flip + 'Sales Orderr' label +
            the x_studio_priority / x_studio_quotation_type /
            x_studio_material_availability trio still land after
            //field[@name='sale_order_id'].
          - The 3 Studio notebook pages (Repair Image, Warranty
            Card, Repair Diagnosis) still land inside //notebook.

        Dropped:
          - //button[@name='action_fsm_create_quotation']
            attribute change  →  already unconditionally hidden by
            project_task.py._get_view.
          - //button[@name='action_fsm_view_material']
            attribute change  →  already amended in place by
            project_task.py._get_view.

        Idempotent — a marker on the second line of arch_db lets
        subsequent runs skip the rewrite.
        """
        view = self.env['ir.ui.view'].sudo().browse(3019).exists()
        if not view:
            return
        current = view.arch_db or ''
        marker = '<!-- fix_repair:sanitized-v190 -->'
        if marker in current:
            return

        clean_arch = '''<data>
  <!-- fix_repair:sanitized-v190 -->
  <xpath expr="//field[@name='personal_stage_type_id']" position="after">
    <button type="action" name="2316" string="Tested OK" class="btn-primary" invisible="material_line_product_count &gt; 0 or x_studio_cancelled == True or not helpdesk_ticket_id or x_studio_end_quick_repair == True"/>
  </xpath>
  <xpath expr="//field[@name='user_ids']" position="attributes">
    <attribute name="string">Assignees</attribute>
  </xpath>
  <xpath expr="//field[@name='user_ids']" position="after">
    <field name="helpdesk_ticket_id" string="Help Desk Ticket"/>
    <field name="x_studio_created_date"/>
    <field name="x_studio_repair_reason" invisible="True"/>
  </xpath>
  <xpath expr="//field[@name='sale_order_id']" position="attributes">
    <attribute name="invisible">False</attribute>
    <attribute name="string">Sales Orderr</attribute>
  </xpath>
  <xpath expr="//field[@name='sale_order_id']" position="after">
    <field name="x_studio_priority"/>
    <field name="x_studio_quotation_type"/>
    <field name="x_studio_material_availability"/>
  </xpath>
  <xpath expr="//notebook" position="inside">
    <page string="Repair Image" name="studio_page_8ci_1ik1qk8tm">
      <group name="studio_group_8ci">
        <group name="studio_group_8ci_left">
          <field name="x_studio_repair_image_01" widget="tablet_image"/>
        </group>
        <group name="studio_group_8ci_right">
          <field name="x_studio_repair_image_02" widget="tablet_image"/>
        </group>
      </group>
    </page>
    <page string="Warranty Card" name="studio_page_8db_1ik1r0ore">
      <group name="studio_group_8db">
        <group name="studio_group_8db_left">
          <field name="x_studio_warranty_card" widget="image"/>
        </group>
        <group name="studio_group_8db_right">
          <field name="x_studio_related_information" widget="image"/>
        </group>
      </group>
    </page>
    <page string="Repair Diagnosis" name="studio_page_M5qFQ" invisible="helpdesk_ticket_id == False">
      <field name="x_studio_diagnosis_ids" force_save="True" required="helpdesk_ticket_id != False">
        <tree editable="bottom">
          <field name="x_studio_sequence" widget="handle"/>
          <field name="x_name" column_invisible="True"/>
          <field name="x_studio_condition" optional="show" column_invisible="True"/>
          <field name="x_studio_symptom_area" optional="show" column_invisible="True"/>
          <field name="x_studio_symptom_code" optional="show" column_invisible="True"/>
          <field name="x_studio_description" optional="show"/>
          <field name="x_studio_diagnosis_area" optional="show" required="1"/>
          <field name="x_studio_diagnosis_code" optional="show" required="1" domain="[[&quot;x_studio_diagnosis_area_1&quot;,&quot;=&quot;,x_studio_diagnosis_area]]"/>
          <field name="x_studio_reason" optional="show" required="1"/>
          <field name="x_studio_sub_reason" optional="show" required="1" domain="[[&quot;x_studio_reason_code&quot;,&quot;=&quot;,x_studio_reason]]"/>
          <field name="x_studio_resolution" optional="show" required="1"/>
          <field name="x_studio_repair_stage" optional="show" required="1"/>
          <field optional="show" name="x_studio_task_id" string="Task Id" invisible="1" column_invisible="True"/>
        </tree>
      </field>
    </page>
  </xpath>
</data>
'''
        # Raw SQL bypasses ir.ui.view.write()'s _check_xml validator
        # (which combines the live arch during the upgrade
        # transaction and can raise on unrelated in-flight state).
        #
        # arch_db is a jsonb column in Odoo 17 with per-language keys;
        # a bare XML string errors with "invalid input syntax for
        # type json". Merge the clean arch into the existing lang
        # dict so any non-default translation survives.
        self.env.cr.execute(
            "SELECT arch_db FROM ir_ui_view WHERE id = %s", (view.id,)
        )
        row = self.env.cr.fetchone()
        existing = row[0] if row else None
        if isinstance(existing, str):
            try:
                existing = json.loads(existing)
            except ValueError:
                existing = None
        if not isinstance(existing, dict) or not existing:
            existing = {'en_US': ''}
        payload = {lang: clean_arch for lang in existing.keys()}
        self.env.cr.execute(
            "UPDATE ir_ui_view SET arch_db = %s::jsonb WHERE id = %s",
            (json.dumps(payload), view.id),
        )
        view.invalidate_recordset(['arch_db'])

    @api.model
    def _fix_studio_report_template_keys(self):
        """v154 hotfix for the v153 report ownership migration.

        v153 rewrote ir.actions.report.report_name from
        'studio_customization.<tail>' to 'Fix-repair.<tail>' but left
        the underlying QWeb template's `key` field unchanged.

        Odoo's website.ir_ui_view._get_view_id() (used at report
        render time whenever a website_id is in context) resolves
        templates by matching the `key` field against the incoming
        xml_id string verbatim — it does not fall back to
        ir.model.data. Result: after v153 all 17 helpdesk-repair
        reports 500'd with 'View %r in website 1 not found'.

        This method walks every Fix-repair-owned ir.actions.report on
        the repair scope, resolves its template via the still-Studio
        `key` field, and rewrites the key to the Fix-repair prefix.
        Also ensures an ir.model.data pin exists so env.ref() also
        finds the record, and rewrites any t-call="<studio prefix>"
        occurrences inside arch_db of the migrated templates so
        chained inheritance keeps resolving.

        Idempotent — rows whose key already begins with 'Fix-repair.'
        are skipped.
        """
        scope_models = (
            'helpdesk.ticket',
            'helpdesk.ticket.type',
            'helpdesk.stage',
            'project.task',
            'res.users',
            'x_repair_accounts',
            'x_repair_reason',
            'x_repair_reason_custom',
            'x_repair_stages',
            'x_repair_sub_reason',
        )
        Data = self.env['ir.model.data'].sudo()
        Report = self.env['ir.actions.report'].sudo()
        View = self.env['ir.ui.view'].sudo()

        reports = Report.search([('model', 'in', scope_models)])
        if not reports:
            return

        # Pass 1 — collect (tail, template_view) for every Fix-repair-
        # owned report. Look up the template by its current key
        # (which may still be under studio_customization, or already
        # under Fix-repair from a prior run).
        migrated = []
        migrated_tails = set()
        for report in reports:
            pin = Data.search([
                ('model', '=', 'ir.actions.report'),
                ('res_id', '=', report.id),
            ], limit=1)
            if not pin or pin.module != 'Fix-repair':
                continue
            rname = report.report_name or ''
            if not rname.startswith('Fix-repair.'):
                continue
            tail = rname.split('.', 1)[1]

            studio_key = 'studio_customization.' + tail
            fix_key = 'Fix-repair.' + tail
            template = View.search([('key', '=', studio_key)], limit=1)
            if not template:
                template = View.search([('key', '=', fix_key)], limit=1)
            if not template:
                # Template genuinely missing — skip. Nothing to migrate.
                continue
            migrated.append((tail, template, studio_key, fix_key))
            migrated_tails.add(tail)

        # Pass 2 — rewrite key + ensure pin.
        for tail, template, studio_key, fix_key in migrated:
            if template.key == studio_key:
                template.write({'key': fix_key})
            existing_pin = Data.search([
                ('module', '=', 'Fix-repair'),
                ('name', '=', tail),
                ('model', '=', 'ir.ui.view'),
            ], limit=1)
            if not existing_pin:
                Data.create({
                    'module': 'Fix-repair',
                    'name': tail,
                    'model': 'ir.ui.view',
                    'res_id': template.id,
                    'noupdate': True,
                })

        # Pass 3 — rewrite t-call / t-inherit references inside
        # arch_db so chained templates resolve. Only rewrite
        # occurrences whose tail is in our migrated set (so we don't
        # accidentally break references to Studio templates outside
        # the repair scope).
        for tail, template, _sk, _fk in migrated:
            arch = template.arch_db or ''
            new_arch = arch
            for other_tail in migrated_tails:
                new_arch = new_arch.replace(
                    'studio_customization.' + other_tail,
                    'Fix-repair.' + other_tail,
                )
            if new_arch != arch:
                template.write({'arch_db': new_arch})

    @api.model
    def _migrate_studio_reports_to_native(self):
        """Repin every Studio-authored ir.actions.report on the repair
        scope + its underlying QWeb template ir.ui.view rows from
        module='studio_customization' to module='Fix-repair'.

        Two-step ownership transfer per report:

          1. Rewrite ir.actions.report.report_name from
             'studio_customization.<slug>' to 'Fix-repair.<slug>' —
             this is the string env.ref() uses to resolve the QWeb
             template at render time.
          2. Repin the ir.model.data row that owns the QWeb template
             ir.ui.view record (module column only — xml_id kept
             verbatim so no cross-reference breaks).
          3. Repin the ir.model.data row that owns the report action
             record itself.

        Arch of every report / template stays byte-identical; only
        the ownership marker moves. Studio's UI stops treating these
        as its own so future edits go into the module.

        Idempotent — reruns find no studio_customization pins in
        scope and no-op.
        """
        scope_models = (
            'helpdesk.ticket',
            'helpdesk.ticket.type',
            'helpdesk.stage',
            'project.task',
            'res.users',
            'x_repair_accounts',
            'x_repair_reason',
            'x_repair_reason_custom',
            'x_repair_stages',
            'x_repair_sub_reason',
        )
        Data = self.env['ir.model.data'].sudo()
        Report = self.env['ir.actions.report'].sudo()

        reports = Report.search([('model', 'in', scope_models)])
        if not reports:
            return

        report_pins = Data.search([
            ('model', '=', 'ir.actions.report'),
            ('module', '=', 'studio_customization'),
            ('res_id', 'in', reports.ids),
        ])
        if not report_pins:
            return

        # Pass 1 — collect template xml_ids that the Studio reports
        # reference via report_name, so we can migrate their pins too.
        template_xmlids = set()
        report_name_updates = []
        for pin in report_pins:
            report = Report.browse(pin.res_id)
            if not report.exists():
                continue
            rname = report.report_name or ''
            if rname.startswith('studio_customization.'):
                _module, tail = rname.split('.', 1)
                template_xmlids.add(tail)
                report_name_updates.append((report, tail))

        # Pass 2 — move the template pins (module only, keep name).
        if template_xmlids:
            template_pins = Data.search([
                ('model', '=', 'ir.ui.view'),
                ('module', '=', 'studio_customization'),
                ('name', 'in', list(template_xmlids)),
            ])
            already_fixrepair = set(Data.search([
                ('module', '=', 'Fix-repair'),
                ('name', 'in', list(template_xmlids)),
            ]).mapped('name'))
            for tp in template_pins:
                if tp.name in already_fixrepair:
                    # Prior run already migrated this pin — drop the
                    # dangling studio row.
                    tp.unlink()
                    continue
                tp.write({
                    'module': 'Fix-repair',
                    'noupdate': True,
                })

        # Pass 3 — rewrite report_name references so env.ref() lands
        # on the new Fix-repair.<tail> address.
        for report, tail in report_name_updates:
            new_ref = 'Fix-repair.%s' % tail
            if report.report_name != new_ref:
                report.write({'report_name': new_ref})

        # Pass 4 — move the report action pins (module only, keep
        # name for the same "no cross-reference breaks" reason).
        report_action_names = report_pins.mapped('name')
        already_fixrepair_actions = set(Data.search([
            ('module', '=', 'Fix-repair'),
            ('name', 'in', report_action_names),
        ]).mapped('name'))
        for pin in report_pins:
            if pin.name in already_fixrepair_actions:
                pin.unlink()
                continue
            pin.write({
                'module': 'Fix-repair',
                'noupdate': True,
            })

    @api.model
    def _migrate_studio_views_to_native(self):
        """Repin every Studio-authored ir.ui.view on the repair scope
        from module='studio_customization' to module='Fix-repair'.
        Arch stays verbatim on the DB row; only the ownership marker
        moves.

        Scope covers the 11 models we've already migrated the field
        graph for. Views on models outside this scope are left alone
        so unrelated Studio customizations remain untouched.

        Idempotent: rows whose module is already 'Fix-repair' are
        skipped. New xml_id is a stable deterministic slug so re-runs
        find the same record.
        """
        scope_models = (
            'helpdesk.ticket',
            'helpdesk.ticket.type',
            'helpdesk.stage',
            'project.task',
            'res.users',
            'res.config.settings',
            'x_repair_accounts',
            'x_repair_reason',
            'x_repair_reason_custom',
            'x_repair_stages',
            'x_repair_sub_reason',
        )
        Data = self.env['ir.model.data'].sudo()
        View = self.env['ir.ui.view'].sudo()

        studio_pins = Data.search([
            ('model', '=', 'ir.ui.view'),
            ('module', '=', 'studio_customization'),
        ])
        if not studio_pins:
            return
        views = View.browse(studio_pins.mapped('res_id')).exists()
        in_scope_ids = set(
            views.filtered(lambda v: v.model in scope_models).ids
        )
        pins_in_scope = studio_pins.filtered(
            lambda p: p.res_id in in_scope_ids
        )
        if not pins_in_scope:
            return

        for pin in pins_in_scope:
            view = View.browse(pin.res_id)
            if not view.exists():
                continue
            slug = 'view_%s_%s_%s' % (
                view.model.replace('.', '_'),
                view.type,
                view.id,
            )
            # Guard: if Fix-repair already owns a view with this slug,
            # this pin has already been migrated on a prior run. Just
            # drop the stale studio_customization row.
            existing = Data.search([
                ('module', '=', 'Fix-repair'),
                ('name', '=', slug),
            ], limit=1)
            if existing:
                pin.unlink()
                continue
            pin.write({
                'module': 'Fix-repair',
                'name': slug,
                'noupdate': True,
            })

    def _repair_studio_auto_create_repair_serial_nos(self):
        """Studio server action id 1994 native port.

        Same shape as _repair_studio_auto_create_repair_route above,
        but additionally creates a new stock.lot from the
        'repair.serial.seq' sequence and attaches it as
        x_studio_serial_no / lot_id on the ticket + as lot_id on
        the created stock.move.line.
        """
        for record in self:
            if not record.id:
                continue
            company_id = self.env.context.get(
                'allowed_company_ids', [self.env.user.company_id.id]
            )[0]
            company = self.env['res.company'].browse(company_id)

            if company.id == 1:
                if not record.x_studio_virtual_location:
                    raise UserError(
                        'Virtual Location must be setup for Current Logged in User.'
                    )
                if not record.x_studio_source_location:
                    raise UserError(
                        'Source Location must be setup for Current Logged in User.'
                    )
                virtual_loc = record.x_studio_virtual_location.id
                source_loc = record.x_studio_source_location.id
            else:
                if not record.x_studio_virtual_location_1:
                    raise UserError(
                        'Virtual Location must be setup for Current Logged in User.'
                    )
                if not record.x_studio_source_location_1:
                    raise UserError(
                        'Source Location must be setup for Current Logged in User.'
                    )
                virtual_loc = record.x_studio_virtual_location_1.id
                source_loc = record.x_studio_source_location_1.id

            seq = self.env['ir.sequence'].with_context(
                company_id=company.id
            ).next_by_code('repair.serial.seq')

            rep_serial = self.env['stock.lot'].create({
                'name': seq,
                'product_id': record.product_id.id,
                'company_id': company.id,
            })
            record.x_studio_serial_no = rep_serial.id
            record.lot_id = rep_serial.id
            record.x_studio_repair_serial_created = True

            dest_loc = self.env['stock.location'].search([
                ('usage', '=', 'customer'),
            ], limit=1)
            if not dest_loc:
                continue

            opt_type = self.env['stock.picking.type'].search([
                ('default_location_src_id', '=',
                    record.x_studio_return_receipt_location.id),
                ('code', '=', 'outgoing'),
                ('company_id', '=', company.id),
            ], limit=1)
            if not opt_type:
                raise UserError('The selected return receipt location is not correct.')

            prod_move = self.env['stock.picking'].create({
                'x_studio_created_from_help_ticket': record.id,
                'x_studio_helpdesk_ticket_id': record.id,
                'picking_type_id': opt_type.id,
                'location_id': source_loc,
                'location_dest_id': dest_loc.id,
                'company_id': company.id,
                # v255: stamp the ticket's partner so helpdesk_stock's
                # has_partner_picking compute (used to gate the Return
                # button) treats this synthetic delivery as a real
                # prior delivery to the partner. Clear-DB masks the
                # absence of this because their cash-customer partner
                # has thousands of pre-existing done deliveries — on
                # standalone we can't lean on that.
                'partner_id': record.partner_id.id if record.partner_id else False,
            })
            update_prod_move = self.env['stock.picking'].search([
                ('id', '=', prod_move.id),
                ('company_id', '=', company.id),
            ], limit=1)
            if update_prod_move:
                stock_move = self.env['stock.move'].create({
                    'picking_id': update_prod_move.id,
                    'name': 'New Move:' + record.product_id.name,
                    'reference': update_prod_move.name,
                    'picking_type_id': update_prod_move.picking_type_id.id,
                    'product_id': record.product_id.id,
                    'location_id': update_prod_move.location_id.id,
                    'location_dest_id': update_prod_move.location_dest_id.id,
                    'product_uom_qty': 1.00,
                    'product_uom': record.product_id.uom_id.id,
                    'state': 'done',
                    'company_id': company.id,
                })
                self.env['stock.move.line'].create({
                    'move_id': stock_move.id,
                    'picking_id': update_prod_move.id,
                    'picking_type_id': update_prod_move.picking_type_id.id,
                    'product_id': record.product_id.id,
                    'product_uom_id': record.product_id.uom_id.id,
                    'location_id': update_prod_move.location_id.id,
                    'location_dest_id': update_prod_move.location_dest_id.id,
                    'lot_id': record.x_studio_serial_no.id,
                    'qty_done': 1.00,
                    'company_id': company.id,
                })
                update_prod_move.write({'state': 'done'})

            record.x_studio_picking_id = prod_move.id
            record.x_studio_pick_id = prod_move.id

    @api.model
    def _delegate_studio_server_actions_to_native(self):
        """Rewrite Studio ir.actions.server.code strings to one-line
        delegations into native Python methods. Same idempotent-
        marker pattern Fix-repair uses for compute delegations (see
        sale_order._delegate_studio_computes_to_native).

        Covers:
          Tier 1 — 4 automation-triggered actions (v144)
          Tier 2 — 6 button-triggered repair-workflow actions (v145)

        Only touches actions that don't already carry the marker,
        so it's safe to run on every install/upgrade.
        """
        marker = self.env['sale.order']._FIX_REPAIR_IDEMPOTENCE_MARKER
        Server = self.env['ir.actions.server'].sudo()

        delegations = [
            # (server_action_id, guard_substring, delegation_code)
            # Tier 1 — automations
            (1976, "next_by_code('repair.seq')",
             "record._repair_seq_no_on_create_or_write()"),
            (2000, 'x_studio_return_receipt_location',
             "record._repair_populate_repair_location()"),
            (2222, 'Cancelled tickets can not be deleted',
             "record._repair_validate_cancelled_on_unlink()"),
            (1989, "trans_line = env['stock.move.line'].search",
             "record._repair_auto_select_product_for_rug()"),
            # Tier 2 — repair-workflow buttons
            (2001, 'x_studio_repair_factory_location',
             "record._repair_studio_send_to_factory()"),
            (2002, 'x_studio_created_by_2',
             "record._repair_studio_receive_at_factory()"),
            (2007, 'x_studio_created_by_9',
             "record._repair_studio_send_to_sales_centre()"),
            (2006, 'x_studio_created_by_10',
             "record._repair_studio_receive_at_sales_centre()"),
            (2220, 'Cancel reason must be specified',
             "record._repair_studio_cancel_repair()"),
            (2221, 'x_studio_reopen_status',
             "record._repair_studio_reopen_repair()"),
            # Tier 3 — heavy compute (route + serial creation)
            (1993, 'prod_lines.append',
             "record._repair_studio_auto_create_repair_route()"),
            (1994, "next_by_code('repair.serial.seq')",
             "record._repair_studio_auto_create_repair_serial_nos()"),
            # Tier 4 — email actions (Customer Letter + Final Notice
            # variants). Guards use the template id literal since
            # that's the only text that differs between the 5.
            (2269, "'id', '=', 56",
             "record._repair_send_customer_letter()"),
            (2308, "'id', '=', 66",
             "record._repair_send_final_notice()"),
            (2309, "'id', '=', 67",
             "record._repair_send_final_notice_estimated()"),
            (2310, "'id', '=', 69",
             "record._repair_send_final_notice_scrappage()"),
            (2311, "'id', '=', 70",
             "record._repair_send_reminding_letter()"),
            # Tier 5 — variants + object_write conversion
            (1990, "picking_code', '=', 'outgoing'",
             "record._repair_auto_select_product_for_rug_2()"),
            (2450, "x_studio_sn_updated'] = True",
             "record._repair_auto_select_product_for_rug_22()"),
            (2451, "x_studio_sn_updated'] = False",
             "record._repair_auto_select_product_for_rug_33()"),
            (1992, "record.ticket_type_id:",
             "record._repair_auto_select_product_for_rug_4()"),
            (2343, 'x_studio_cancelled_2',
             "record._repair_studio_cancel_repair_2()"),
            (2159, 'Warranty Card Document must be Uploaded',
             "record._repair_studio_change_repair_type_to_rug()"),
            (2558, 'does not have access to below listed warehouse',
             "record._repair_studio_user_location_validation()"),
            # 1998 is state='object_write' with an empty update_field_id
            # + value — effectively dead. Convert to state='code' with a
            # no-op delegation so any reference resolves safely. Guard
            # matches the standard boilerplate present in the code field
            # of newly-created object_write actions.
            (1998, 'Available variables:',
             "record._repair_studio_update_rug_approval_in_pipeline()"),
            # Tier 6 — actions on non-ticket models
            #  6 "JIN Company Id" on the 5 catalogue models +
            #  helpdesk.stage (all identical: set x_studio_company_id
            #  from current company context).
            (2666, 'x_studio_company_id',
             "record._jin_set_company_id()"),
            (2667, 'x_studio_company_id',
             "record._jin_set_company_id()"),
            (2668, 'x_studio_company_id',
             "record._jin_set_company_id()"),
            (2670, 'x_studio_company_id',
             "record._jin_set_company_id()"),
            (2760, 'x_studio_company_id',
             "record._jin_set_company_id()"),
            (2790, 'x_studio_company_id',
             "record._jin_set_company_id()"),
            # project.task pipeline promotion on task-create
            (2003, 'fsm_task_count',
             "record._repair_auto_update_helpdesk_pipeline_status_1()"),
            # res.users super-user permission validation
            (2544, 'x_studio_super_user_melt_items',
             "record._super_user_validate()"),
            # Tier 7 — remaining Studio project.task repair actions
            # (End Quick Repair button + diagnosis/image/diagnosis-line
            # validation guards).
            (2316, 'x_studio_end_quick_repair',
             "record._repair_studio_end_quick_repair()"),
            (2224, 'one repair diagnosis line must be specified',
             "record._repair_studio_diagnosis_validation()"),
            (2242, 'one repair image should be uploaded',
             "record._repair_studio_image_validation()"),
            (2219, 'x_studio_valid_diagnosis',
             "record._repair_studio_validate_diagnosis_lines()"),
        ]
        for action_id, guard, call in delegations:
            action = Server.browse(action_id).exists()
            if not action:
                continue
            code = action.code or ''
            if marker in code:
                continue
            if guard not in code:
                # Someone already edited the code manually — don't
                # overwrite their changes.
                continue
            vals = {'code': f"{marker}\n{call}\n"}
            if action.state != 'code':
                # Non-code actions (e.g. state='object_write' for
                # id 1998) need the state flip too, otherwise the
                # code column is set but the action still runs its
                # original (possibly broken) native mechanism.
                vals['state'] = 'code'
            action.write(vals)
