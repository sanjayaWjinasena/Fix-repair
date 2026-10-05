# -*- coding: utf-8 -*-
"""Make the Studio-ported check fields calculate again (v17.0.1.0.366).

On Clear-DB / production these 15 fields are Studio COMPUTED fields
(sale.order credit / overdue / bank-guarantee / commission checks,
stock.picking approval / payment checks). The port declared them in
BugFix-Sales and BugFix-Stock as PLAIN fields, so on the dev envs they
never calculated, and on a production copy they stopped calculating as soon
as the repos took them over from Studio.

This module already carries native Python versions of those computations
(the _fix_repair_compute_* methods its _delegate_studio_computes_to_native
functions pointed the Studio formulas at). Here they become the fields' real
compute, with the dependency lists and storage taken verbatim from Clear-DB
ir.model.fields (2026-10-05):
  sale.order    7 fields, stored    (store=True, copy=False)
  stock.picking 8 fields, not stored
Only the compute-related attributes are set; labels and the rest come from
the declaring modules. Fix-repair depends on both BugFix-Sales and
BugFix-Stock, so these definitions load after the plain ones.
"""
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    x_studio_over_commission = fields.Boolean(
        compute='_jin_compute_over_commission', store=True, readonly=True, copy=False)
    x_studio_over_credit = fields.Boolean(
        compute='_jin_compute_over_credit', store=True, readonly=True, copy=False)
    x_studio_over_credit_amount = fields.Float(
        compute='_jin_compute_over_credit_amount', store=True, readonly=True, copy=False)
    x_studio_over_bank_guarantee = fields.Boolean(
        compute='_jin_compute_over_bank_guarantee', store=True, readonly=True, copy=False)
    x_studio_over_bank_guarantee_amount = fields.Float(
        compute='_jin_compute_over_bank_guarantee_amount', store=True, readonly=True, copy=False)
    x_studio_guarantee_status = fields.Char(
        compute='_jin_compute_guarantee_status', store=True, readonly=True, copy=False)
    x_studio_overdue = fields.Boolean(
        compute='_jin_compute_overdue', store=True, readonly=True, copy=False)

    @api.depends('order_line')
    def _jin_compute_over_commission(self):
        self._fix_repair_compute_over_commission()

    @api.depends('partner_invoice_id.credit', 'partner_invoice_id.credit_limit', 'amount_total',
                 'partner_id', 'x_studio_order_payment_method')
    def _jin_compute_over_credit(self):
        self._fix_repair_compute_over_credit()

    @api.depends('partner_invoice_id.credit', 'partner_invoice_id.credit_limit', 'amount_total',
                 'partner_id', 'x_studio_order_payment_method')
    def _jin_compute_over_credit_amount(self):
        self._fix_repair_compute_over_credit_amount()

    @api.depends('partner_invoice_id.credit', 'partner_invoice_id.x_studio_bank_guarantee_amount',
                 'amount_total', 'partner_id', 'x_studio_order_payment_method',
                 'x_studio_valid_bank_guarantee')
    def _jin_compute_over_bank_guarantee(self):
        self._fix_repair_compute_over_bank_guarantee()

    @api.depends('partner_invoice_id.credit', 'partner_invoice_id.x_studio_bank_guarantee_amount',
                 'amount_total', 'partner_id', 'x_studio_order_payment_method',
                 'x_studio_valid_bank_guarantee')
    def _jin_compute_over_bank_guarantee_amount(self):
        self._fix_repair_compute_over_bank_guarantee_amount()

    @api.depends('partner_id', 'x_studio_order_payment_method', 'x_studio_valid_bank_guarantee')
    def _jin_compute_guarantee_status(self):
        self._fix_repair_compute_guarantee_status()

    @api.depends('partner_invoice_id.total_overdue', 'partner_id', 'x_studio_order_payment_method')
    def _jin_compute_overdue(self):
        self._fix_repair_compute_overdue()


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    x_studio_cash_full_payment_made = fields.Boolean(
        compute='_jin_compute_cash_full_payment_made', store=False, readonly=True)
    x_studio_fsm_task_done = fields.Boolean(
        compute='_jin_compute_fsm_task_done', store=False, readonly=True)
    x_studio_fully_paid_so = fields.Boolean(
        compute='_jin_compute_fully_paid_so', store=False, readonly=True)
    x_studio_need_approval = fields.Boolean(
        compute='_jin_compute_need_approval', store=False, readonly=True)
    x_studio_repair_payment_made = fields.Boolean(
        compute='_jin_compute_repair_payment_made', store=False, readonly=True)
    x_studio_user_location_validation = fields.Boolean(
        compute='_jin_compute_user_location_validation', store=False, readonly=True)
    x_studio_valid_factory_repair = fields.Boolean(
        compute='_jin_compute_valid_factory_repair', store=False, readonly=True)
    x_studio_valid_transfer_lines = fields.Boolean(
        compute='_jin_compute_valid_transfer_lines', store=False, readonly=True)

    @api.depends('sale_id')
    def _jin_compute_cash_full_payment_made(self):
        self._fix_repair_compute_cash_full_payment_made()

    @api.depends('x_studio_created_from_help_ticket', 'x_studio_helpdesk_ticket_id')
    def _jin_compute_fsm_task_done(self):
        self._fix_repair_compute_fsm_task_done()

    @api.depends('x_studio_created_from_help_ticket', 'x_studio_helpdesk_ticket_id')
    def _jin_compute_fully_paid_so(self):
        self._fix_repair_compute_fully_paid_so()

    @api.depends('picking_type_code')
    def _jin_compute_need_approval(self):
        self._fix_repair_compute_need_approval()

    @api.depends('sale_id')
    def _jin_compute_repair_payment_made(self):
        self._fix_repair_compute_repair_payment_made()

    @api.depends('x_studio_type_of_operation')
    def _jin_compute_user_location_validation(self):
        self._fix_repair_compute_user_location_validation()

    @api.depends('x_studio_created_from_help_ticket', 'x_studio_helpdesk_ticket_id')
    def _jin_compute_valid_factory_repair(self):
        self._fix_repair_compute_valid_factory_repair()

    @api.depends('move_line_ids_without_package', 'move_ids_without_package')
    def _jin_compute_valid_transfer_lines(self):
        self._fix_repair_compute_valid_transfer_lines()


STORED_SALE_ORDER_COMPUTES = (
    'x_studio_over_commission', 'x_studio_over_credit', 'x_studio_over_credit_amount',
    'x_studio_over_bank_guarantee', 'x_studio_over_bank_guarantee_amount',
    'x_studio_guarantee_status', 'x_studio_overdue',
)


def recompute_stored_studio_computes(env):
    """Fill the stored sale.order check fields once. Odoo only computes a
    stored compute by itself when its column is new; these columns already
    exist (stale on prod copies since the repo takeover, never filled on dev
    envs). ORM only."""
    SaleOrder = env['sale.order'].sudo().with_context(active_test=False)
    orders = SaleOrder.search([])
    if not orders:
        return 0
    for name in STORED_SALE_ORDER_COMPUTES:
        env.add_to_compute(SaleOrder._fields[name], orders)
    env.flush_all()   # runs the pending recomputation and writes it
    return len(orders)
