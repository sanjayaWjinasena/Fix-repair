# -*- coding: utf-8 -*-
from lxml import etree
from markupsafe import Markup, escape
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.http import request


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Mirrors the linked helpdesk ticket's repair_stage_state for use in view
    # expressions (e.g. gating Create Invoice on Repair Completed for RUG SOs).
    ticket_repair_stage_state = fields.Char(compute='_compute_ticket_repair_stage_state')

    # True once the customer has signed the quotation on the portal preview.
    # Used as the gate for the backend Confirm button on NUW / Reject-RUG
    # quotations. Wraps signed_on/signature because directly referencing
    # 'signed_on' in a view expression fails ("Name not defined") — the
    # standard signed_on field doesn't survive injection into our form arch,
    # but this custom field, which we declare and own, does.
    x_customer_signed = fields.Boolean(
        compute='_compute_x_customer_signed',
    )

    def _compute_ticket_repair_stage_state(self):
        for order in self:
            task = order.sudo().task_id or self.env['project.task'].sudo().search(
                [('sale_order_id', '=', order.id)], limit=1
            )
            ticket = task.helpdesk_ticket_id if task else None
            order.ticket_repair_stage_state = (ticket.repair_stage_state or '') if ticket else ''

    @api.depends('signed_on', 'signed_by', 'signature')
    def _compute_x_customer_signed(self):
        for order in self:
            order.x_customer_signed = bool(
                order.signed_on or order.signed_by or order.signature
            )

    # True when this SO can be re-estimated: customer has signed AND no
    # outgoing delivery on it is validated yet. Powers the Re-estimate
    # button on the SO form.
    can_re_estimate = fields.Boolean(compute='_compute_can_re_estimate')

    @api.depends('state', 'signed_on', 'signed_by', 'picking_ids.state',
                 'picking_ids.picking_type_id.code')
    def _compute_can_re_estimate(self):
        for order in self:
            if order.state == 'cancel':
                order.can_re_estimate = False
                continue
            if not (order.signed_on or order.signed_by):
                order.can_re_estimate = False
                continue
            any_outgoing_done = any(
                p.state == 'done' and p.picking_type_id.code == 'outgoing'
                for p in order.picking_ids
            )
            order.can_re_estimate = not any_outgoing_done

    # ── Stock availability at the repair source ──────────────────────────
    # Gate the forward-progress buttons (Send by Email / Request RUG /
    # Confirm) until every storable line has enough stock in the parts
    # pool that will actually be consumed for the repair:
    #   • Factory Repair  → the Factory Repair Location's warehouse's
    #                       resupply_wh_ids (their stock locations,
    #                       summed). The factory itself typically doesn't
    #                       hold parts stock — it pulls from central
    #                       supply warehouses. Falls back to the factory
    #                       location itself when no resupply is configured.
    #   • Centre Repair   → ticket.x_studio_repair_location (the branch's
    #                       own stock).
    # Non-repair SOs and configs without a resolvable source default to
    # "OK" so the gate never applies outside the repair workflow.
    x_repair_stock_ok = fields.Boolean(
        compute='_compute_x_repair_stock_ok',
    )

    def _get_repair_stock_source_locations(self):
        """Return the stock.location recordset to check availability
        against for this SO. May contain multiple locations (the resupply
        pool feeding the factory). Empty recordset means 'skip the gate'
        — non-repair or unresolvable config."""
        self.ensure_one()
        task = self.sudo().task_id or self.env['project.task'].sudo().search(
            [('sale_order_id', '=', self.id)], limit=1
        )
        ticket = task.helpdesk_ticket_id if task else False
        Location = self.env['stock.location']
        if not ticket:
            return Location
        job = ticket.x_studio_job_location
        if job == 'Factory Repair':
            key = f'fix_repair.factory_repair_location.{self.company_id.id}'
            raw = self.env['ir.config_parameter'].sudo().get_param(key)
            if not raw:
                return Location
            try:
                factory_loc = Location.sudo().browse(int(raw)).exists()
            except (TypeError, ValueError):
                return Location
            if not factory_loc:
                return Location
            # Parts get consumed at the factory but stocked at the
            # factory warehouse's resupply warehouses (e.g. RP-JM's
            # resupply pool is JM-EK + BR-EK). Check availability there;
            # fall back to the factory location itself when no resupply
            # is configured so the check doesn't silently break if the
            # warehouse setup changes.
            factory_wh = factory_loc.warehouse_id
            resupply = factory_wh.resupply_wh_ids
            if resupply:
                return resupply.mapped('lot_stock_id')
            return factory_loc
        if job == 'Centre Repair':
            return ticket.x_studio_repair_location or Location
        return Location

    @api.depends('order_line', 'order_line.product_id',
                 'order_line.product_uom_qty', 'company_id', 'state')
    def _compute_x_repair_stock_ok(self):
        for order in self:
            locations = order._get_repair_stock_source_locations()
            if not locations:
                order.x_repair_stock_ok = True
                continue
            short = False
            for line in order.order_line.filtered(
                    lambda l: l.product_id.type == 'product'
                              and not l.display_type):
                need = line.product_uom_qty or 0
                if need <= 0:
                    continue
                total = sum(
                    line.product_id.with_context(location=loc.id).free_qty
                    for loc in locations
                )
                if total < need:
                    short = True
                    break
            order.x_repair_stock_ok = not short

    def action_show_stock_shortage(self):
        """Warning button callback: raise a UserError listing each
        insufficient line and its shortfall against the resupply pool.
        Invoked when the salesperson clicks the red 'Not Enough Stock'
        button that appears in draft / sent state when x_repair_stock_ok
        is False."""
        self.ensure_one()
        locations = self._get_repair_stock_source_locations()
        if not locations:
            return
        source_names = ', '.join(locations.mapped('display_name'))
        details = []
        for line in self.order_line.filtered(
                lambda l: l.product_id.type == 'product' and not l.display_type):
            need = line.product_uom_qty or 0
            if need <= 0:
                continue
            total = sum(
                line.product_id.with_context(location=loc.id).free_qty
                for loc in locations
            )
            if total < need:
                details.append(
                    f"  • {line.product_id.display_name}: "
                    f"need {need:g}, available {total:g}, "
                    f"short by {need - total:g}"
                )
        if not details:
            return
        raise UserError(
            f"Not enough stock at {source_names}:\n\n"
            + "\n".join(details)
        )

    def action_re_estimate(self):
        """Reset this SO for re-estimation and move the linked helpdesk
        ticket back to Diagnosis. Mirrors helpdesk.ticket.action_re_estimate
        so the button can live on either side."""
        for order in self:
            order._re_estimate_reset()
            task = order.sudo().task_id or self.env['project.task'].sudo().search(
                [('sale_order_id', '=', order.id)], limit=1
            )
            ticket = task.helpdesk_ticket_id if task else None
            if ticket:
                ticket._move_to_stage('Diagnosis')

    # Marker embedded in every Studio server action we've rewritten with
    # idempotence guards. Presence of the marker in `code` means the
    # action is already optimised — subsequent upgrades skip the patch,
    # so any manual edits the user made afterwards survive.
    _FIX_REPAIR_IDEMPOTENCE_MARKER = "# fix_repair:idempotent-v1"

    # ── Native compute methods that back the Studio compute strings ──────
    # Studio computed fields have their body stored as a text 'compute' on
    # ir.model.fields, executed via safe_eval on every recompute. That
    # parse+eval per compute is expensive.
    # By rewriting each compute string to a single delegating call —
    #   `self._fix_repair_compute_<name>()`
    # — safe_eval sees just one method call, and the actual work runs in
    # native Python at CPython speed. Same field name, same value returned.
    # These methods are the native implementations; the rewriter function
    # below installs the one-line delegations.

    def _fix_repair_compute_over_commission(self):
        for rec in self:
            rec.x_studio_over_commission = any(
                line.x_studio_over_commission for line in rec.order_line
            )

    def _fix_repair_compute_over_credit(self):
        for rec in self:
            result = False
            if rec.partner_id.id and rec.x_studio_order_payment_method == 'Credit':
                pi = rec.partner_invoice_id
                amt = rec.amount_total
                if rec.x_studio_quotation_type == 'Repair':
                    amt = amt * 0.5
                result = (pi.credit + amt) > pi.credit_limit
            rec.x_studio_over_credit = result

    def _fix_repair_compute_over_credit_amount(self):
        for rec in self:
            result = 0
            if rec.partner_id.id and rec.x_studio_order_payment_method == 'Credit':
                pi = rec.partner_invoice_id
                result = (pi.credit + rec.amount_total) - pi.credit_limit
            rec.x_studio_over_credit_amount = result

    def _fix_repair_compute_over_bank_guarantee(self):
        today = fields.Date.context_today(self)
        for rec in self:
            result = False
            if rec.partner_id.id and rec.x_studio_order_payment_method == 'Credit' \
                    and rec.x_studio_valid_bank_guarantee:
                pi = rec.partner_invoice_id
                expiry = pi.x_studio_expiry_date
                if expiry and expiry < today:
                    result = True
                else:
                    result = (pi.credit + rec.amount_total) > (pi.x_studio_bank_guarantee_amount or 0)
            rec.x_studio_over_bank_guarantee = result

    def _fix_repair_compute_over_bank_guarantee_amount(self):
        for rec in self:
            result = 0
            if rec.partner_id.id and rec.x_studio_order_payment_method == 'Credit' \
                    and rec.x_studio_valid_bank_guarantee:
                pi = rec.partner_invoice_id
                result = (pi.credit + rec.amount_total) - (pi.x_studio_bank_guarantee_amount or 0)
            rec.x_studio_over_bank_guarantee_amount = result

    def _fix_repair_compute_guarantee_status(self):
        today = fields.Date.context_today(self)
        for rec in self:
            result = False
            if rec.x_studio_order_payment_method == 'Credit' and rec.x_studio_valid_bank_guarantee:
                expiry = rec.partner_id.x_studio_expiry_date
                if expiry and expiry < today:
                    result = 'Bank Guarantee has Expired'
                else:
                    result = 'Valid Bank Guarantee'
            rec.x_studio_guarantee_status = result

    def _fix_repair_compute_overdue(self):
        for rec in self:
            result = False
            if rec.partner_id.id and rec.x_studio_order_payment_method == 'Credit':
                # partner_invoice_id.total_overdue is Odoo core — cost is
                # inherited but unavoidable for correct behaviour.
                result = rec.partner_invoice_id.total_overdue > 0.00
            rec.x_studio_overdue = result

    @api.model
    def _delegate_studio_computes_to_native(self):
        """Rewrite each heavy Studio compute string on sale.order to a
        one-line delegation call. safe_eval sees ~one line; the actual
        computation runs in the native Python method above.

        Same functional output — every field returns the same value it
        did before. Only the execution path is faster.

        Idempotent via the shared '# fix_repair:idempotent-v1' marker.
        """
        IrField = self.env['ir.model.fields'].sudo()
        marker = self._FIX_REPAIR_IDEMPOTENCE_MARKER

        # Map: (field_name, expected_substring_in_original, delegating_snippet)
        delegations = [
            ('x_studio_over_commission',    'x_studio_over_commission',      'self._fix_repair_compute_over_commission()'),
            ('x_studio_over_credit',        'partner_invoice_id.credit',     'self._fix_repair_compute_over_credit()'),
            ('x_studio_over_credit_amount', 'credit_limit',                  'self._fix_repair_compute_over_credit_amount()'),
            ('x_studio_over_bank_guarantee','x_studio_bank_guarantee_amount','self._fix_repair_compute_over_bank_guarantee()'),
            ('x_studio_over_bank_guarantee_amount','x_studio_bank_guarantee_amount','self._fix_repair_compute_over_bank_guarantee_amount()'),
            ('x_studio_guarantee_status',   'Valid Bank Guarantee',          'self._fix_repair_compute_guarantee_status()'),
            ('x_studio_overdue',            'total_overdue',                 'self._fix_repair_compute_overdue()'),
        ]

        for name, guard_substring, call in delegations:
            field = IrField.search([
                ('model', '=', 'sale.order'),
                ('name', '=', name),
            ], limit=1)
            if not field:
                continue
            code = field.compute or ''
            if marker in code:
                continue  # already delegated
            if guard_substring not in code:
                continue  # someone changed it — leave alone
            field.write({'compute': f"{marker}\n{call}\n"})

    @api.model
    def _restrict_notify_transfer_completion_automation(self):
        """Narrow the fire condition of Studio automation
        'PROJ - Notify Transfer Completion' so it only creates a
        mail.activity when a Project-flow picking transitions to
        state='done'. Currently it fires on every write to every
        stock.picking, creating a To-Do activity per fire — even for
        repair-flow deliveries — which is the direct cause of the
        delivery-Validate slowness (each button_validate spawns 4+
        duplicate activities per picking, on top of an already-bloated
        mail.activity table).

        Functional intent preserved: Janitha still receives the
        'Project Transfer Completed' To-Do when a Project transfer's
        picking is validated. Repair and Not Under Warranty pickings
        no longer create activities from this automation.

        Idempotent: only patches when filter_domain is empty (its
        original state). If someone edits the filter manually, we
        leave it alone.
        """
        Auto = self.env['base.automation'].sudo()
        auto = Auto.search([
            ('model_name', '=', 'stock.picking'),
            ('name', '=', 'PROJ - Notify Transfer Completion'),
        ], limit=1)
        if not auto:
            return
        # Skip if someone already narrowed the filter
        if auto.filter_domain or auto.filter_pre_domain:
            return
        target_filter_domain = (
            "[('sale_id.x_studio_quotation_type', '=', 'Project'), "
            "('state', '=', 'done')]"
        )
        target_filter_pre_domain = "[('state', '!=', 'done')]"
        auto.write({
            'filter_domain': target_filter_domain,
            'filter_pre_domain': target_filter_pre_domain,
        })

    @api.model
    def _optimize_slow_studio_computes(self):
        """Convert redundant stored Studio compute fields into related
        fields (or a cheaper compute) so they don't add cost during
        write cascades. Functionally identical — the fields return the
        same values, just resolved via native ORM traversal instead of
        safe_eval'd Python code.

        Idempotent: only touches fields whose current compute code matches
        the redundant pattern we can safely replace. Manual Studio edits
        (any change to the compute code) preserve the field as-is.
        """
        IrField = self.env['ir.model.fields'].sudo()

        # Redundant computes that just return record.amount_total.
        # Replace with related='amount_total' — Odoo handles the
        # traversal natively (no safe_eval per fire).
        redundant_amount_total_computes = [
            'x_studio_current_tot_amount',
            'x_studio_current_tot_amount_1',
        ]
        for name in redundant_amount_total_computes:
            field = IrField.search([
                ('model', '=', 'sale.order'),
                ('name', '=', name),
            ], limit=1)
            if not field:
                continue
            # Only rewrite if the compute is the known redundant pattern
            code = (field.compute or '').strip()
            if 'record.amount_total' not in code:
                continue  # someone changed it — leave alone
            if field.related == 'amount_total':
                continue  # already converted
            try:
                field.write({
                    'related': 'amount_total',
                    'compute': False,
                    'store': False,
                    'readonly': True,
                })
            except Exception:
                # If the model's cache prevents the switch mid-runtime,
                # skip silently — will retry on next upgrade.
                pass

    @api.model
    def _optimize_slow_write_automations(self):
        """Rewrite four Studio server actions on sale.order that fire on
        every SO write and unconditionally call `record.write(...)`.
        The rewritten versions perform the same work but skip the write
        (and therefore skip the downstream automation cascade) when the
        target values already equal the current values.

        Functional behaviour is unchanged — same fields are eventually
        at the same values. Just no redundant write cycles.

        Idempotent via an embedded marker string: if the action's code
        already contains the marker, the patch is skipped so manual
        Studio edits are preserved on subsequent upgrades.
        """
        Server = self.env['ir.actions.server'].sudo()
        marker = self._FIX_REPAIR_IDEMPOTENCE_MARKER

        # account.move.line and account.move actions to patch too — bundled
        # here so a single upgrade sweep covers everything.
        aml_marker_source = "SRM - Auto Populate Report Type in Account Move Lines"

        patches = [
            {
                # SRM - Auto Populate Report Type in Account Move Lines
                # (fires on every AML write — 10-15× per invoice)
                'search': [
                    ('model_id.model', '=', 'account.move.line'),
                    ('code', 'like', "x_sales_report_type"),
                    ('code', 'like', "account_internal_group"),
                ],
                'new_code': (
                    marker + "\n"
                    "if record.account_internal_group == 'income' "
                    "and not record.x_studio_sales_report_type:\n"
                    "  rpt = env['x_sales_report_type'].sudo().search(\n"
                    "    [('x_studio_report_code', '=', 'Sales Details for Incentive Calc.')],\n"
                    "    limit=1)\n"
                    "  if rpt:\n"
                    "    record.write({'x_studio_sales_report_type': rpt.id})\n"
                ),
            },
            {
                # SRM - Update Sales Order - Customer Invoice
                # (fires once per account.move create — cheap, but the
                # unconditional write still triggers downstream computes)
                'search': [
                    ('model_id.model', '=', 'account.move'),
                    ('code', 'like', "x_studio_sale_id"),
                    ('code', 'like', "invoice_origin"),
                ],
                'new_code': (
                    marker + "\n"
                    "if record.invoice_origin and not record.x_studio_sale_id:\n"
                    "  sale = env['sale.order'].sudo().search(\n"
                    "    [('name', '=', record.invoice_origin)], limit=1)\n"
                    "  if sale:\n"
                    "    record.write({'x_studio_sale_id': sale.id})\n"
                ),
            },
            {
                # RR - Track Lock Status  (fires on every sale.order write)
                'search': [
                    ('model_id.model', '=', 'sale.order'),
                    ('code', 'like', "x_studio_re_estimate_count"),
                    ('code', 'like', "x_studio_locked"),
                    ('code', 'like', "state == 'done'"),
                ],
                'new_code': (
                    marker + "\n"
                    "if record.x_studio_quotation_type == 'Repair' and record.state == 'done':\n"
                    "  re_line = env['sale.order.line'].sudo().search(\n"
                    "    [('order_id', '=', record.id), ('x_studio_re_estimated', '=', True)],\n"
                    "    limit=1, order='id desc')\n"
                    "  target_count = re_line.x_studio_count_1 if re_line else 0\n"
                    "  if (not record.x_studio_locked\n"
                    "      or record.x_studio_unlocked\n"
                    "      or record.x_studio_re_estimate_count != target_count):\n"
                    "    record.write({\n"
                    "      'x_studio_locked': True,\n"
                    "      'x_studio_unlocked': False,\n"
                    "      'x_studio_re_estimate_count': target_count,\n"
                    "    })\n"
                ),
            },
            {
                # RR - Track Lock Status - 2  (fires on every sale.order write)
                'search': [
                    ('model_id.model', '=', 'sale.order'),
                    ('code', 'like', "x_studio_locked == True"),
                    ('code', 'like', "state == 'sale'"),
                ],
                'new_code': (
                    marker + "\n"
                    "if (record.x_studio_quotation_type == 'Repair'\n"
                    "    and record.state == 'sale'\n"
                    "    and record.x_studio_locked):\n"
                    "  record.write({'x_studio_locked': False, 'x_studio_unlocked': True})\n"
                ),
            },
            {
                # Update Analytic Tag Parameters - Sales Order - User
                'search': [
                    ('model_id.model', '=', 'sale.order'),
                    ('code', 'like', "account.analytic.distribution.model"),
                    ('code', 'like', "x_studio_account_mandatory"),
                    ('code', 'like', "create_uid"),
                ],
                'new_code': (
                    marker + "\n"
                    "if record.create_uid:\n"
                    "  tag_rule = env['account.analytic.distribution.model'].sudo().search(\n"
                    "    [('partner_id.user_id', '=', record.create_uid.id)], limit=1)\n"
                    "  target = tag_rule.x_studio_user_mandatory if tag_rule else False\n"
                    "  if record.x_studio_account_mandatory != target:\n"
                    "    record.write({'x_studio_account_mandatory': target})\n"
                ),
            },
            {
                # Project Sales Order Seq.No - 3  (fires on every sale.order write)
                'search': [
                    ('model_id.model', '=', 'sale.order'),
                    ('code', 'like', "replace('_PRJ'"),
                    ('code', 'like', "x_studio_quotation_type"),
                ],
                'new_code': (
                    marker + "\n"
                    "if record.id:\n"
                    "  original_name = (record.name or '').replace('_PRJ', '')\n"
                    "  new_name = (original_name + '_PRJ'\n"
                    "              if record.x_studio_quotation_type == 'Project'\n"
                    "              else original_name)\n"
                    "  if record.name != new_name:\n"
                    "    record.write({'name': new_name})\n"
                ),
            },
        ]

        for p in patches:
            for action in Server.search(p['search']):
                if marker in (action.code or ''):
                    continue
                action.write({'code': p['new_code']})

    @api.model
    def _seed_advance_payment_method_lines(self):
        """Ensure the 'Advance Payment' and 'Advance Payment - Repairs'
        journals each have at least one inbound Manual payment method
        line, AND that method line has a payment_account_id (the
        Outstanding Receipts asset_current account for the company).

        Odoo 17's account.payment validation requires BOTH:
          1. payment_method_line_id set on the payment
          2. an outstanding account resolvable from either
             (a) the method line's payment_account_id, or
             (b) res.company.account_journal_payment_debit_account_id,
                 or
             (c) res.company.account_journal_payment_credit_account_id
        These journals were created without going through Odoo's Bank
        Setup wizard, so none of those are set — the Studio 'Create
        Advance Payment' action then raises 'You can't create a new
        payment without an outstanding payments/receipts account set…'

        Strategy: give each Manual line a `payment_account_id`
        pointing to the company's 'Outstanding Receipts' account
        (asset_current, per-company). Narrower than setting company
        defaults — doesn't affect other journals.

        Idempotent:
          - Creates a Manual line only when the journal has none
          - Backfills payment_account_id on existing Manual lines that
            are missing one
          - Skips silently when the Outstanding Receipts account
            cannot be located for a company (logged in server logs)
        """
        Journal = self.env['account.journal'].sudo()
        MethodLine = self.env['account.payment.method.line'].sudo()
        Account = self.env['account.account'].sudo()
        # Manual is the built-in fallback payment method — always
        # usable for advance payments.
        manual = self.env.ref('account.account_payment_method_manual_in',
                              raise_if_not_found=False)
        if not manual:
            manual = self.env['account.payment.method'].sudo().search(
                [('code', '=', 'manual'), ('payment_type', '=', 'inbound')],
                limit=1,
            )
        if not manual:
            return

        # Per-company lookup of the Outstanding Receipts account.
        # Matches on name (case-insensitive) + asset_current type +
        # reconcile=True. Cache per company so we only query once.
        outstanding_by_company = {}

        def _outstanding_receipts(company):
            if company.id in outstanding_by_company:
                return outstanding_by_company[company.id]
            acc = Account.search([
                ('company_id', '=', company.id),
                ('account_type', '=', 'asset_current'),
                ('reconcile', '=', True),
                ('name', '=ilike', 'Outstanding Receipts'),
            ], limit=1)
            outstanding_by_company[company.id] = acc
            return acc

        for name in ('Advance Payment', 'Advance Payment - Repairs'):
            for journal in Journal.search([('name', '=', name)]):
                outstanding = _outstanding_receipts(journal.company_id)
                existing = journal.inbound_payment_method_line_ids
                if not existing:
                    MethodLine.create({
                        'payment_method_id': manual.id,
                        'journal_id': journal.id,
                        'name': 'Manual',
                        'payment_account_id': outstanding.id if outstanding else False,
                    })
                    continue
                # Backfill existing method lines that lack an
                # outstanding account
                if outstanding:
                    to_backfill = existing.filtered(lambda l: not l.payment_account_id)
                    if to_backfill:
                        to_backfill.write({'payment_account_id': outstanding.id})

    @api.model
    def _fix_advance_payment_project_field(self):
        """Fix Studio server action 'Create Advance Payment' that passes
        record.id (sale.order ID) to x_studio_project_no_1 which is a
        Many2one to project.project — causing a FK violation when the SO id
        does not match any project.project id.

        Correct substitution: record.x_studio_project_no.id (the Project No
        field on sale.order, also Many2one to project.project).
        Search by code content so it survives action ID changes in Studio.
        Handles both space variants Studio may write (with or without space
        after the colon).
        """
        action = self.env['ir.actions.server'].sudo().search([
            ('model_id.model', '=', 'sale.order'),
            ('code', 'like', "x_studio_project_no_1"),
            ('code', 'like', "account.payment"),
        ], limit=1)
        if not action:
            return
        new = ("'x_studio_project_no_1': "
               "record.x_studio_project_no.id if record.x_studio_project_no else False,")
        code = action.code or ''
        # Studio may write the dict with or without a space after the colon
        for old in (
            "'x_studio_project_no_1':record.id,",
            "'x_studio_project_no_1': record.id,",
        ):
            if old in code:
                code = code.replace(old, new)
                break

        # Odoo 17 requires payment_method_line_id on account.payment.
        # Use the first inbound method line from the journal chosen above.
        pm_old = "'journal_id':journal.id})"
        pm_new = (
            "'journal_id':journal.id,"
            "'payment_method_line_id':"
            "journal.inbound_payment_method_line_ids[:1].id "
            "if journal.inbound_payment_method_line_ids else False})"
        )
        if pm_old in code:
            code = code.replace(pm_old, pm_new)

        action.write({'code': code})

    @api.model
    def _ensure_not_under_warranty_selection(self):
        """Add 'Not Under Warranty' to x_studio_quotation_type if absent.

        In Odoo 17 selection values live in ir.model.fields.selection,
        not in a column on ir_model_fields itself.
        Called from data/fix_repair_data.xml and inline before any write.
        """
        field = self.env['ir.model.fields'].sudo().search([
            ('model', '=', 'sale.order'),
            ('name', '=', 'x_studio_quotation_type'),
        ], limit=1)
        if not field:
            return
        IrSel = self.env['ir.model.fields.selection'].sudo()
        if not IrSel.search([
            ('field_id', '=', field.id),
            ('value', '=', 'Not Under Warranty'),
        ], limit=1):
            IrSel.create({
                'field_id': field.id,
                'value': 'Not Under Warranty',
                'name': 'Not Under Warranty',
                'sequence': 100,
            })

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            # Inject our custom helper fields so button expressions can read
            # them. We use x_customer_signed (computed from signed_on /
            # signed_by / signature) instead of signed_on directly, because
            # the standard signed_on field somehow doesn't survive
            # Studio's view post-processing — but our own fields do.
            for sheet in arch.xpath("//sheet"):
                for fname in ('ticket_repair_stage_state', 'x_customer_signed',
                              'can_re_estimate', 'x_repair_stock_ok',
                              'x_studio_order_payment_method',
                              'x_studio_over_credit',
                              'x_studio_credit_limit_approved'):
                    if not arch.xpath(f"//field[@name='{fname}']"):
                        fld = etree.Element('field')
                        fld.set('name', fname)
                        fld.set('invisible', '1')
                        sheet.insert(0, fld)
                break

            # Re-estimate button in the SO header. Visible when the SO
            # is signed AND no outgoing delivery is validated. Confirm
            # dialog spells out the side effects (state -> draft, signed
            # cleared, RUG cycle restarted) so the salesperson knows.
            for header in arch.xpath("//header"):
                if arch.xpath("//button[@name='action_re_estimate']"):
                    break
                re_est = etree.Element('button')
                re_est.set('name', 'action_re_estimate')
                re_est.set('string', 'Re-estimate')
                re_est.set('type', 'object')
                re_est.set('class', 'btn-secondary')
                re_est.set('confirm',
                    "Re-estimate this Sales Order? It will be reset to draft, "
                    "the customer's signature cleared, and the RUG approval "
                    "cycle restarted. The linked helpdesk ticket will move "
                    "back to Diagnosis.")
                re_est.set('invisible', "not can_re_estimate")
                header.insert(0, re_est)
                break

            # Create Invoice buttons — three variants ship by default:
            #   • create_invoice (purple)             : invoice_status='to invoice'
            #   • create_invoice_sub (gray)           : subscription-only
            #   • create_invoice_percentage (gray)    : percentage advance
            #
            # Behaviour we want:
            #   • RUG-confirmed (warranty path):
            #       - Purple available once the ticket hits Repair Completed
            #       - Percentage variant follows its default visibility
            #   • Reject-RUG (customer-pays path):
            #       - Hide the Purple variant entirely
            #       - Always offer the Percentage advance variant while the
            #         SO is in 'sale' state (regardless of invoice_status),
            #         so the salesperson collects a percentage advance from
            #         the customer to unblock delivery.
            for btn in arch.xpath("//button[@id='create_invoice']"):
                # Hide the purple Create Invoice button only while RUG is
                # confirmed-and-pending (waiting for Repair Completed).
                # Reject-RUG falls through to the NUW behaviour: purple
                # button visible per standard Odoo gating.
                existing = btn.get('invisible', '')
                extra = (
                    "x_studio_rug_confirmed "
                    "and not x_studio_rug_rejected "
                    "and ticket_repair_stage_state != 'repair_completed'"
                )
                btn.set('invisible', f"({existing}) or ({extra})" if existing else extra)

            for btn in arch.xpath("//button[@id='create_invoice_percentage']"):
                # Standard Odoo expression: is_subscription or invoice_status != 'no'
                # or state != 'sale'. Both NUW and Reject-RUG follow the same
                # standard gate now — percentage advance visible while SO is
                # confirmed and no invoice has been created yet.
                btn.set('invisible',
                    "is_subscription or state != 'sale' or invoice_status != 'no'"
                )

            # Order Payment Type: editable in draft/sent for all customers
            for el in arch.xpath("//field[@name='x_studio_order_payment_method']"):
                el.set('readonly', "state in ('cancel', 'done', 'sale')")

            # Quotation Type: editable in draft/sent until an FSM task is linked.
            # Allows switching between Repair and Not Under Warranty; locks once
            # Plan Intervention is clicked (task_id set) or the SO is confirmed.
            for el in arch.xpath("//field[@name='x_studio_quotation_type']"):
                el.set('readonly',
                       "(task_id != False) or "
                       "(state not in ['draft', 'sent'])")

            # RUG Request button: only on Repair quotations, before request is sent
            rug_req_invisible = (
                "(x_studio_quotation_type != 'Repair') or "
                "(state not in ['draft', 'sent']) or "
                "(x_studio_rug_request_sent == True) or "
                "(x_studio_rug_rejected == True) or "
                "(x_studio_rug_approved == True) or "
                "(not x_repair_stock_ok)"
            )
            for btn in arch.xpath("//button[@name='1980']"):
                btn.set('invisible', rug_req_invisible)

            # Approve/Reject RUG buttons: only on Repair quotations, after request is sent
            rug_approve_invisible = (
                "(x_studio_quotation_type != 'Repair') or "
                "(state not in ['draft', 'sent']) or "
                "(x_studio_rug_request_sent == False) or "
                "(x_studio_rug_rejected == True) or "
                "(x_studio_rug_approved == True)"
            )
            # Approve: rewire to our method so it confirms the SO directly (no send wizard)
            for btn in arch.xpath("//button[@name='1981']"):
                btn.set('invisible', rug_approve_invisible)
                btn.set('type', 'object')
                btn.set('name', 'action_approve_rug_direct')
            # Reject: rewire to our own method. The Studio server action 2004
            # also resets each line's price_unit to x_studio_price_unit_original,
            # but that "original" is only captured by another Studio action
            # when x_studio_rug_confirmed flips True — in a request → reject
            # cycle where rug_confirmed never flips, the original stays at 0,
            # and the reset zeros the perfectly-good current price.
            for btn in arch.xpath("//button[@name='2004']"):
                btn.set('invisible', rug_approve_invisible)
                btn.set('type', 'object')
                btn.set('name', 'action_reject_rug_direct')

            # Confirm button: visible in both draft AND sent states so the
            # salesperson can confirm either path:
            #   • Repair + RUG approved          → standard repair-warranty flow
            #   • Repair + RUG rejected          → only AFTER customer signs
            #                                      the portal preview
            #   • Not Under Warranty             → only AFTER customer signs
            #                                      the portal preview
            # Stays hidden on Repair quotations while RUG is still pending
            # (neither approved nor rejected yet).
            # Studio's arch has two action_confirm buttons — we want the
            # SECOND one to be the visible one, so force-hide the first and
            # apply our visibility logic to the second (and force-hide any
            # additional duplicates).
            confirm_btns = arch.xpath("//button[@name='action_confirm']")
            if confirm_btns:
                confirm_btns[0].set('invisible', '1')
                if len(confirm_btns) >= 2:
                    # Credit-limit gate is scoped to Order Payment Type ==
                    # 'Credit' — cash customers are never blocked. Mirrors
                    # the visibility of the studio "Request Credit Limit
                    # Approval" button so the salesperson goes through
                    # approval before the SO can be confirmed.
                    confirm_btns[1].set('invisible',
                        "(state not in ('draft', 'sent')) or "
                        "(x_studio_quotation_type == 'Repair' "
                        "and not x_studio_rug_approved "
                        "and not x_studio_rug_rejected) or "
                        "(x_studio_rug_rejected and not x_customer_signed) or "
                        "(x_studio_quotation_type == 'Not Under Warranty' "
                        "and not x_customer_signed) or "
                        "(not x_repair_stock_ok) or "
                        "(x_studio_order_payment_method == 'Credit' "
                        "and x_studio_over_credit "
                        "and not x_studio_credit_limit_approved)"
                    )
                    for btn in confirm_btns[2:]:
                        btn.set('invisible', '1')

            # Send PRO-FORMA Invoice: not used — hide both instances.
            for btn in arch.xpath("//button[contains(@id, 'send_proforma')]"):
                btn.set('invisible', '1')

            # Cancel: hidden by default for the repair workflow, but shown
            # once at least one quotation email has been sent (state = 'sent')
            # so the salesperson can cancel after sending if needed.
            for btn in arch.xpath("//button[@name='action_cancel']"):
                btn.set('invisible', "state != 'sent'")

            # Set to Quotation (action_draft): not used — once a sale order
            # has been cancelled it stays cancelled, no reverting to draft.
            for btn in arch.xpath("//button[@name='action_draft']"):
                btn.set('invisible', '1')

            # Create Advance Payment: visible only on Sales-type
            # quotations AFTER Confirm has been clicked (state='sale'
            # or 'done'). Not shown on draft / sent quotations because
            # you can't take a payment on something the customer
            # hasn't yet committed to. Repair / Not Under Warranty /
            # Project flows use their own invoicing paths (Create
            # Draft Invoice / RUG settlement) and never see this
            # button.
            for btn in arch.xpath("//button[@name='2341']"):
                btn.set('invisible',
                    "x_studio_quotation_type != 'Sales' "
                    "or state not in ('sale', 'done')"
                )

            # Send by Email: shown for Not Under Warranty (no RUG flow) AND for
            # Repair tickets where the RUG was rejected — once rejected the
            # quotation falls back to the customer-pays flow so the salesperson
            # needs to email the quote.
            # Only visible in 'draft' — once an email has been sent (state
            # becomes 'sent'), hide the button so the salesperson doesn't
            # accidentally fire a duplicate email.
            # Studio has hidden all action_quotation_send buttons via an
            # always-true `state not in ['False']` guard; inject a clean one.
            for header in arch.xpath("//header"):
                btn = etree.Element('button')
                btn.set('name', 'action_quotation_send')
                btn.set('string', 'Send by Email')
                btn.set('type', 'object')
                btn.set('class', 'btn-primary')
                btn.set('invisible',
                    "(x_studio_quotation_type != 'Not Under Warranty' "
                    "and not x_studio_rug_rejected) "
                    "or state != 'draft' "
                    "or not x_repair_stock_ok"
                )
                header.insert(0, btn)

            # Stock shortage warning: red button that appears in draft/sent
            # when any storable line on the SO can't be covered by free_qty
            # at the repair source (Factory Repair Location for Factory
            # tickets, branch stock for Centre tickets). Clicking opens a
            # UserError modal listing exactly what's short. The three
            # forward-progress buttons (Send by Email, Request RUG,
            # Confirm) are gated behind x_repair_stock_ok in this same
            # method so the salesperson can't advance the quotation while
            # this button is visible.
            for header in arch.xpath("//header"):
                warn = etree.Element('button')
                warn.set('name', 'action_show_stock_shortage')
                warn.set('string', 'Not Enough Stock')
                warn.set('type', 'object')
                warn.set('class', 'btn-danger')
                warn.set('invisible',
                    "x_repair_stock_ok or state not in ('draft', 'sent')"
                )
                header.insert(0, warn)
                break

        return arch, view

    @api.onchange('partner_id')
    def _onchange_partner_payment_method(self):
        for order in self:
            if order.partner_id.x_studio_payment_method:
                order.x_studio_order_payment_method = order.partner_id.x_studio_payment_method

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('x_studio_order_payment_method'):
                partner_id = vals.get('partner_id')
                if partner_id:
                    partner = self.env['res.partner'].sudo().browse(partner_id)
                    if partner.x_studio_payment_method:
                        vals['x_studio_order_payment_method'] = partner.x_studio_payment_method
        return super().create(vals_list)

    def action_quotation_send(self):
        action = super().action_quotation_send()
        # Apply the custom body / stage-transition treatment for:
        #   • Not Under Warranty quotations (customer-pays from the start), and
        #   • Repair quotations whose RUG has been rejected (customer now pays).
        # Both should produce the same email body as the Not Under Warranty flow.
        if self.x_studio_quotation_type != 'Not Under Warranty' \
                and not self.x_studio_rug_rejected:
            return action

        # Move linked helpdesk ticket from Diagnosis → Estimation Sent to Customer
        # when the Send by Email button is clicked (mirrors the RUG flow where
        # clicking Request RUG Approval triggers the same transition).
        self._move_ticket_to_stage(self, 'Estimation Sent to Customer')

        # Build the full portal URL (get_portal_url returns a relative path)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        portal_url = base_url + self.get_portal_url()

        link_line = Markup(
            '<div style="margin-top:24px; text-align:center;">'
            '<a href="{url}" '
            'style="display:inline-block; padding:12px 24px; '
            'background-color:#875A7B; color:#ffffff; text-decoration:none; '
            'border-radius:4px; font-family:Arial,sans-serif; font-size:14px; '
            'font-weight:bold;">'
            'View Quotation'
            '</a>'
            '</div>'
        ).format(url=escape(portal_url))

        ctx = action.get('context', {})
        template_id = ctx.get('default_template_id')
        if template_id:
            template = self.env['mail.template'].browse(template_id)
            rendered = template._render_field('body_html', self.ids, options={'post_process': True})
            body = rendered.get(self.id, '') or ''
            ctx['default_body'] = body + link_line
            # Clear the template so the composer uses our pre-built body directly
            ctx['default_template_id'] = False
            ctx['default_use_template'] = False
        else:
            ctx['default_body'] = ctx.get('default_body', '') + link_line

        action['context'] = ctx
        return action

    def action_confirm(self):
        # When the customer signs+accepts on the portal preview, Odoo's
        # portal_quote_accept route calls action_confirm() which would
        # move the quotation straight to Sales Order. For Not Under
        # Warranty and Reject-RUG quotations we want the salesperson to
        # review and click Confirm in the backend manually — so skip the
        # state transition when the call originates from a /my/... portal
        # request. The signature/signed_by/signed_on fields are still
        # captured by the prior portal _sign step, and the backend Confirm
        # button stays visible (state is still draft/sent).
        portal_call = bool(
            request and request.httprequest
            and (request.httprequest.path or '').startswith('/my/')
        )
        if portal_call:
            skip = self.filtered(
                lambda o: o.x_studio_quotation_type == 'Not Under Warranty'
                          or o.x_studio_rug_rejected
            )
            rest = self - skip
            result = super(SaleOrder, rest).action_confirm() if rest else True
            confirmed = rest
        else:
            result = super().action_confirm()
            confirmed = self

        for order in confirmed:
            # Both customer-pays flavours land at Estimation Approval
            # Received when the salesperson clicks Confirm in the backend.
            # Reject-RUG is also moved by the rug_rejected write hook, so
            # this is a no-op when the rejection happened before Confirm —
            # but if the salesperson Confirms first and rejects later, this
            # explicit move keeps the stage consistent.
            if (order.x_studio_quotation_type == 'Not Under Warranty'
                    or order.x_studio_rug_rejected):
                self._move_ticket_to_stage(order, 'Estimation Approval Received')
        return result

    def action_approve_rug_direct(self):
        self.write({'x_studio_rug_approved': True})
        # write() moves the ticket to 'Estimation Approval Received'.
        # Confirm button becomes visible once rug_approved=True; user clicks it manually.

    def action_reject_rug_direct(self):
        """Reject RUG without zeroing the order lines' price_unit.

        The Studio server action 2004 also writes price_unit from
        x_studio_price_unit_original on each line. That field is only
        captured by Studio action 2144 when x_studio_rug_confirmed flips
        True, which doesn't always happen in a request → reject cycle —
        leaving the original at 0 and the reset zeroes the line. Our
        override skips the line touch entirely; the lines keep whatever
        price they already had.
        """
        self.write({'x_studio_rug_rejected': True})

    def _re_estimate_reset(self):
        """Put the SO back to draft so the salesperson can edit lines
        and re-run the quote cycle. Resets the customer sign and RUG
        approval state; increments the re-estimate counter. No-op when
        the SO is still in draft.

        Raises UserError if any outgoing delivery on the SO has already
        been validated — re-estimate is only valid before the first
        physical delivery."""
        self.ensure_one()
        done_outgoing = self.picking_ids.filtered(
            lambda p: p.state == 'done'
            and p.picking_type_id.code == 'outgoing'
        )
        if done_outgoing:
            raise UserError(
                "Cannot re-estimate: a delivery has already been validated "
                "on this Sales Order. Re-estimate is only allowed before the "
                "first delivery."
            )

        # Force the SO back to 'draft' WITHOUT cancelling the procurement
        # pickings. Standard action_cancel cascades to picking.action_cancel
        # on the procurement group, which we don't want — the existing
        # deliveries must stay so any new lines added during re-estimate
        # land in those same pickings via the existing procurement group.
        # Standard action_draft only accepts state in ('sent','cancel'),
        # so direct write is the only way to take a 'sale' state SO back
        # to 'draft' without the cancel cascade.
        # After re-confirm, sale.order.line._action_launch_stock_rule skips
        # lines whose qty is already procured; only the new lines trigger
        # fresh moves, which merge into the existing pickings via the
        # preserved procurement_group_id.
        if self.state != 'draft':
            self.write({'state': 'draft'})

        # Reset customer sign and RUG approval cycle so they re-run on
        # the next round. Deliberately leave x_studio_rug_rejected alone
        # — that is a deliberate operator decision and shouldn't reset.
        # signature is included so x_customer_signed (computed from
        # signed_on / signed_by / signature) flips back to False
        # regardless of which of the three was set.
        self.write({
            'signed_by': False,
            'signed_on': False,
            'signature': False,
            'x_studio_rug_request_sent': False,
            'x_studio_rug_approved': False,
            'x_studio_rug_confirmed': False,
            'x_studio_re_estimate_count': (self.x_studio_re_estimate_count or 0) + 1,
            'x_studio_re_estimate_request_sent': True,
        })

    def _move_ticket_to_stage(self, order, stage_name):
        """Find the linked helpdesk ticket and move it to the named stage.

        Mirrors the guard in helpdesk.ticket._move_to_stage:
        Repair Completed is a one-way milestone — never regress to it once
        the ticket has been there at any point in its history.
        """
        sudo_order = order.sudo()
        task = sudo_order.task_id or self.env['project.task'].sudo().search(
            [('sale_order_id', '=', order.id)], limit=1
        )
        ticket = task.sudo().helpdesk_ticket_id if task else False
        if not ticket:
            return
        if (stage_name == 'Repair Completed'
                and ticket._has_been_at_stage('Repair Completed')):
            return
        stage = self.env['helpdesk.stage'].sudo().search(
            [('name', '=', stage_name),
             ('team_ids', 'in', ticket.team_id.ids),
             '|',
             ('x_studio_company_id', '=', ticket.company_id.id),
             ('x_studio_company_id', '=', False)],
            limit=1
        )
        if stage:
            ticket.sudo().write({'stage_id': stage.id})

    def write(self, vals):
        # When partner changes on a draft/sent SO, sync Order Payment Type from customer
        if vals.get('partner_id') and not vals.get('x_studio_order_payment_method'):
            partner = self.env['res.partner'].sudo().browse(vals['partner_id'])
            if partner.x_studio_payment_method:
                vals = dict(vals, x_studio_order_payment_method=partner.x_studio_payment_method)

        res = super().write(vals)

        # RUG request sent → Estimation Sent to Customer
        if vals.get('x_studio_rug_request_sent'):
            for order in self:
                self._move_ticket_to_stage(order, 'Estimation Sent to Customer')

        # RUG approved or rejected → Estimation Approval Received
        if vals.get('x_studio_rug_approved') or vals.get('x_studio_rug_rejected'):
            for order in self:
                self._move_ticket_to_stage(order, 'Estimation Approval Received')

        # RUG approved → reprice all lines to product cost price
        if vals.get('x_studio_rug_approved'):
            for order in self:
                if order.x_studio_quotation_type == 'Repair':
                    for line in order.order_line:
                        if line.product_id:
                            line.write({'price_unit': line.product_id.standard_price})

        return res
