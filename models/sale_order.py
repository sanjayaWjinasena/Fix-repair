# -*- coding: utf-8 -*-
import json

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

    # Backwards-compatible alias for tax_totals. The Studio-modified
    # sale.report_saleorder_document arch on this instance was migrated
    # from Odoo 16 and still calls
    #     <t t-call="account.document_tax_totals"/>
    # which internally does `json.loads(record.tax_totals_json)`
    # because in Odoo 16 tax_totals_json was a Char/Text field storing
    # the JSON *string*. Odoo 17 replaced it with `tax_totals` — same
    # content but as a native dict (fields.Json).
    #
    # To keep the legacy Studio template working without editing its
    # arch in Studio, expose the JSON-serialized string form under the
    # old name. json.dumps() returns a str; json.loads() in the
    # template then round-trips it back to a dict.
    tax_totals_json = fields.Char(compute='_compute_tax_totals_json')

    @api.depends('tax_totals')
    def _compute_tax_totals_json(self):
        for order in self:
            order.tax_totals_json = json.dumps(order.tax_totals) if order.tax_totals else '{}'

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

    # True when this repair is not covered by warranty (customer pays from
    # the start). Replaces the deprecated `x_studio_quotation_type ==
    # 'Not Under Warranty'` type-value pattern: quotation_type now stays
    # as 'Repair' for every repair SO (warranty or not), and this Boolean
    # captures the customer-pays semantic independently. Set by
    # project_task._sync_repair_flags() from ticket.x_studio_rug_confirmed
    # at SO creation. Existing NUW records are migrated by
    # _migrate_nuw_to_customer_pays_flag on every install/upgrade.
    #
    # Note this is orthogonal to x_studio_rug_rejected: a warranty repair
    # (customer_pays=False) can still end up as customer-pays via a RUG
    # rejection. Downstream checks that care about the "customer pays"
    # state universally read as
    #    order.x_repair_customer_pays or order.x_studio_rug_rejected
    x_repair_customer_pays = fields.Boolean(
        string='Not Under Warranty',
        default=False,
        help="True when this repair is not covered by warranty and the "
             "customer must pay from the start. Independent of the RUG "
             "rejection flag (which fires when a warranty repair falls "
             "through to customer-pays after the RUG cycle).",
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
    def _migrate_nuw_to_customer_pays_flag(self):
        """One-shot data migration: eliminate 'Not Under Warranty' as a
        quotation_type value, replace with the x_repair_customer_pays
        Boolean flag.

        The previous design used the quotation_type selection value
        'Not Under Warranty' as a proxy for the customer-pays semantic.
        That coupled a display-type value to a business flag and forced
        the salesperson to see 'Not Under Warranty' as a separate
        quotation type in the dropdown. This method:

          1. Rewrites every SO with quotation_type='Not Under Warranty'
             to quotation_type='Repair' + x_repair_customer_pays=True.
          2. Removes the 'Not Under Warranty' value from the selection
             field so it no longer appears in the UI.

        Idempotent: subsequent runs find no NUW records and no NUW
        selection value, so the method is a no-op. Called from
        data/fix_repair_data.xml on every install/upgrade.

        Not migrated: Reject-RUG SOs (x_studio_rug_rejected=True with
        quotation_type='Repair'). These already carry the RUG signal;
        downstream checks read as
        `x_repair_customer_pays or x_studio_rug_rejected` and preserve
        the historical distinction between "started as NUW" (flag) and
        "warranty rejected mid-flow" (RUG flag).
        """
        # Step 1: rewrite every existing NUW SO. Uses sudo() to bypass
        # the readonly gate on x_studio_quotation_type (readonly is a
        # view-level directive; Python writes are unaffected). We set
        # quotation_type='Repair' first, then flip the flag — the order
        # doesn't matter for correctness since both values are stored,
        # but doing them in one write() is atomic.
        nuw_orders = self.sudo().search([
            ('x_studio_quotation_type', '=', 'Not Under Warranty'),
        ])
        if nuw_orders:
            nuw_orders.write({
                'x_studio_quotation_type': 'Repair',
                'x_repair_customer_pays': True,
            })

        # Step 2: drop the 'Not Under Warranty' selection value so the
        # dropdown no longer offers it. We locate the field row on
        # sale.order first (there's also x_studio_quotation_type on
        # other models like project.task via Studio) and only delete
        # its selection child.
        field = self.env['ir.model.fields'].sudo().search([
            ('model', '=', 'sale.order'),
            ('name', '=', 'x_studio_quotation_type'),
        ], limit=1)
        if field:
            nuw_selection = self.env['ir.model.fields.selection'].sudo().search([
                ('field_id', '=', field.id),
                ('value', '=', 'Not Under Warranty'),
            ], limit=1)
            if nuw_selection:
                nuw_selection.unlink()

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
                              'x_repair_customer_pays',
                              # v263: x_studio_quotation_type is read by our
                              # OR-merged invisible expressions below
                              # (repair_expr). On standalone the base sale.order
                              # arch doesn't happen to render this field, so OWL
                              # can't evaluate the expression at render time
                              # without a sentinel.
                              'x_studio_quotation_type',
                              # v264: Confirm-button invisible expression reads
                              # both RUG flags plus is_subscription. Base arch
                              # doesn't fetch them without sentinels on standalone.
                              'x_studio_rug_confirmed',
                              'x_studio_rug_rejected',
                              'is_subscription',
                              'x_studio_order_payment_method',
                              'x_studio_over_credit',
                              'x_studio_credit_limit_approved',
                              'x_studio_overdue',
                              'x_studio_overdue_approved',
                              'x_studio_valid_order_lines',
                              'x_studio_expired',
                              'x_studio_over_commission',
                              'x_studio_over_commission_approved',
                              'x_studio_margin_exceed',
                              'x_studio_margin_approved',
                              'x_studio_over_bank_guarantee',
                              'x_studio_bank_guarantee_approved',
                              'x_studio_proj_budget_status',
                              'x_studio_budget_created',
                              'x_studio_inventory_short',
                              'x_studio_price_not_confirmed',
                              'x_studio_new_item_from_project'):
                    if not arch.xpath(f"//field[@name='{fname}']"):
                        fld = etree.Element('field')
                        fld.set('name', fname)
                        fld.set('invisible', '1')
                        sheet.insert(0, fld)
                break

            # Hide UI-only fields from the Sale Order form — but ONLY on
            # Repair SOs. Sales / Project quotations continue to show
            # Quotation Template, Sales Order Validity, Recurring Plan
            # etc. as before, because those flows genuinely use them.
            # Fields stay on the model on every SO (data + computes +
            # Confirm-button gating below still work) — we just suppress
            # rendering when x_studio_quotation_type == 'Repair'.
            # arch.xpath returns [] when Studio hasn't placed the field
            # into any view slot, so absent fields are silently skipped.
            # OR-merge with any existing invisible expression so sibling
            # modules that pre-set their own type-based hide (e.g.
            # BugFix-Sales hides these fields on Sales-type quotations)
            # don't get stomped by our overwrite. Fix-repair runs LAST
            # in the _get_view MRO because it depends on BugFix-Sales,
            # so a naïve .set() drops earlier hides silently.
            repair_expr = "x_studio_quotation_type == 'Repair'"
            for fname in (
                'sale_order_template_id',               # Quotation Template
                'x_studio_sales_order_validity',        # Sales Order Validity
                'x_studio_service_item_available',      # Service Item Available
                'x_studio_main_project_no',             # Main Project No
                'x_studio_re_estimate_request_count',   # Re-estimate Request Count (bool)
                'x_studio_re_estimate_request_count_1', # Re-estimate Request Count (int)
                'x_studio_re_estimate_count',           # Re-estimate Count
                'plan_id',                              # Recurring Plan
                'x_studio_expired',                     # Expired
            ):
                # Responsive SO header renders <label for="fname"/> in a
                # separate cell from the <field name="fname"/>. Hiding
                # only the field leaves the label dangling. Include both.
                elements = (
                    arch.xpath(f"//field[@name='{fname}']")
                    + arch.xpath(f"//label[@for='{fname}']")
                )
                for el in elements:
                    existing = el.get('invisible', '')
                    if existing and existing not in ('0', 'False'):
                        el.set(
                            'invisible',
                            f"({existing}) or ({repair_expr})",
                        )
                    else:
                        el.set('invisible', repair_expr)

            # Document Introduction / Conclusion (from BugFix-Sales): hide
            # ONLY on Repair sale orders. Sales / Project quotations still
            # show them because the intro/conclusion selectors are useful
            # for those flows. Conditional invisible instead of "1" so the
            # visibility flips automatically when x_studio_quotation_type
            # changes. Same label + field pair treatment.
            for fname in ('bugfix_sales_intro_id', 'bugfix_sales_conclusion_id'):
                elements = (
                    arch.xpath(f"//field[@name='{fname}']")
                    + arch.xpath(f"//label[@for='{fname}']")
                )
                for el in elements:
                    existing = el.get('invisible', '')
                    if existing and existing not in ('0', 'False'):
                        el.set(
                            'invisible',
                            f"({existing}) or ({repair_expr})",
                        )
                    else:
                        el.set('invisible', repair_expr)

            # Strip ghost Studio fields whose ir.model.fields row exists
            # but whose model registration is broken. Studio created two
            # `x_studio_current_tot_amount` rows (name + `_1` suffix) as
            # related fields pointing at amount_total, but neither is
            # loaded on sale.order._fields — a simple read() raises
            # ValueError: Invalid field. Leaving the <field> elements in
            # arch crashes the client (owl "field is undefined"). Until
            # the ghost rows are cleaned up in Studio, drop them from
            # arch here so the form renders.
            for ghost in ('x_studio_current_tot_amount',
                          'x_studio_current_tot_amount_1'):
                for el in arch.xpath(f"//field[@name='{ghost}']"):
                    parent = el.getparent()
                    if parent is not None:
                        parent.remove(el)

            # Re-estimate button in the SO header. Visible when the SO
            # is signed AND no outgoing delivery is validated AND no
            # invoice exists yet. Confirm dialog spells out the side
            # effects (state -> draft, signed cleared, RUG cycle
            # restarted) so the salesperson knows.
            #
            # invoice_count guard (v189): once an invoice exists we
            # can't cleanly re-estimate — the invoice would need to
            # be cancelled / reversed first, and the salesperson
            # should do that consciously via the invoice form
            # rather than through a Re-estimate that silently
            # invalidates it. Hiding the button while any invoice
            # is present forces the correct order of operations.
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
                re_est.set('invisible',
                    "not can_re_estimate or invoice_count > 0")
                header.insert(0, re_est)
                break

            # Hide the Unlock button (Odoo core, appears when
            # state='done' / SO is locked) once an invoice exists on
            # this SO. Same rationale as the Re-estimate guard —
            # unlocking a locked SO with a live invoice would create
            # a ledger / lifecycle mismatch. Salesperson should
            # cancel or reverse the invoice first, then the natural
            # SO state can revert. Non-invoiced Sales SOs still see
            # Unlock in the header when they're 'done'.
            for btn in arch.xpath("//button[@name='action_unlock']"):
                existing = btn.get('invisible', '')
                extra = 'invoice_count > 0'
                btn.set(
                    'invisible',
                    f"({existing}) or ({extra})" if existing else extra,
                )

            # Create Invoice buttons — three variants ship by default:
            #   • create_invoice (purple)             : invoice_status='to invoice'
            #   • create_invoice_sub (gray)           : subscription-only
            #   • create_invoice_percentage (gray)    : percentage advance
            #
            # v163 behaviour:
            #   • RUG-confirmed (warranty path):
            #       - Purple available once the ticket hits Repair Completed;
            #         click routes to action_repair_create_invoice which
            #         falls through to standard Odoo _create_invoices()
            #         (delivered-qty invoice, no down-payment wizard).
            #   • Non-RUG (customer-pays or Reject-RUG):
            #       - Purple visible immediately after confirm — even
            #         before delivery. Click routes to
            #         _create_repair_full_invoice() which builds ONE
            #         invoice for the entire SO ignoring the
            #         invoice_policy='delivery' gate. Supports quick
            #         repairs where the customer pays 100% upfront.
            #   • Repair SOs universally lose the Percentage advance
            #     variant (no more down-payment split).
            #   • Non-Repair SOs (Sales / Project) keep the standard
            #     Odoo behaviour on both buttons — untouched here.
            for btn in arch.xpath("//button[@id='create_invoice']"):
                # Repoint the button at our router method. This
                # replaces the default action= wizard call
                # (action_view_sale_advance_payment_inv) with a plain
                # object-method call, so no down-payment prompt.
                btn.set('name', 'action_repair_create_invoice')
                btn.set('type', 'object')
                # The default context passes
                #   default_advance_payment_method='delivered'
                # into the wizard — no longer relevant.
                btn.attrib.pop('context', None)
                btn.set('invisible',
                    # Universal gates
                    "is_subscription or state != 'sale' "
                    # Hide once at least one non-cancelled invoice
                    # exists on the SO. Odoo's invoice_count is
                    # computed after filtering out state='cancel'
                    # moves, so this reappears automatically when
                    # every invoice on the SO gets cancelled.
                    #
                    # Note we use invoice_count rather than
                    # invoice_status == 'invoiced' because down-
                    # payment-only SOs from the legacy two-invoice
                    # flow can have invoice_status = 'no' (product
                    # lines still at qty_invoiced = 0) while still
                    # carrying an active down-payment invoice.
                    "or invoice_count > 0 "
                    # RUG in progress: waiting for Repair Completed
                    "or (x_studio_rug_confirmed and not x_studio_rug_rejected "
                    "    and ticket_repair_stage_state != 'repair_completed') "
                    # RUG-approved / non-Repair: keep standard Odoo
                    # gate — only visible when something is invoiceable
                    "or (not (x_repair_customer_pays or x_studio_rug_rejected) "
                    "    and invoice_status not in ('to invoice', 'upselling'))"
                )

            for btn in arch.xpath("//button[@id='create_invoice_percentage']"):
                # Hide the percentage down-payment variant on every
                # Repair SO. Non-Repair SOs keep the standard gate.
                btn.set('invisible',
                    "is_subscription or state != 'sale' "
                    "or invoice_status != 'no' "
                    "or x_studio_quotation_type == 'Repair'"
                )

            # Order Payment Type: editable in draft/sent for all customers
            for el in arch.xpath("//field[@name='x_studio_order_payment_method']"):
                el.set('readonly', "state in ('cancel', 'done', 'sale')")

            # Quotation Type: editable in draft/sent until an FSM task is linked.
            # Repair SOs are auto-set to 'Repair' by project_task._sync_repair_flags
            # when Plan Intervention creates the task; the type readonly lock kicks
            # in from that moment. Non-repair SOs (Sales, Project) stay editable
            # until confirm.
            for el in arch.xpath("//field[@name='x_studio_quotation_type']"):
                el.set('readonly',
                       "(task_id != False) or "
                       "(state not in ['draft', 'sent'])")

            # RUG Request button: only on WARRANTY Repair quotations, before
            # request is sent. Customer-pays repairs (formerly 'Not Under
            # Warranty' quotation_type) don't go through the RUG cycle —
            # they're customer-pays from the start, so the RUG buttons must
            # stay hidden. Reject-RUG SOs also hide the request button
            # because the RUG cycle already resolved.
            rug_req_invisible = (
                "(x_studio_quotation_type != 'Repair') or "
                "(x_repair_customer_pays) or "
                "(state not in ['draft', 'sent']) or "
                "(x_studio_rug_request_sent == True) or "
                "(x_studio_rug_rejected == True) or "
                "(x_studio_rug_approved == True) or "
                "(not x_repair_stock_ok)"
            )
            for btn in arch.xpath("//button[@name='1980']"):
                btn.set('invisible', rug_req_invisible)

            # Approve/Reject RUG buttons: only on WARRANTY Repair quotations,
            # after request is sent. Same customer-pays guard as above — if a
            # customer-pays repair somehow has rug_request_sent=True (legacy
            # data), still hide the approve/reject buttons.
            rug_approve_invisible = (
                "(x_studio_quotation_type != 'Repair') or "
                "(x_repair_customer_pays) or "
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
            #   • Repair (warranty) + RUG approved  → standard warranty flow
            #   • Repair (warranty) + RUG rejected  → only AFTER customer signs
            #                                         (falls through to customer-pays)
            #   • Repair (customer-pays)            → only AFTER customer signs
            #                                         the portal preview
            # Stays hidden on warranty Repair quotations while the RUG is still
            # pending (neither approved nor rejected yet).
            # Studio's arch has two action_confirm buttons — we want the
            # SECOND one to be the visible one, so force-hide the first and
            # apply our visibility logic to the second (and force-hide any
            # additional duplicates).
            confirm_btns = arch.xpath("//button[@name='action_confirm']")
            if confirm_btns:
                confirm_btns[0].set('invisible', '1')
                if len(confirm_btns) >= 2:
                    # Split gating into (a) universal predicates that
                    # apply to EVERY sale.order regardless of quotation
                    # type, and (b) repair-workflow predicates that only
                    # fire for x_studio_quotation_type == 'Repair'.
                    #
                    # Universal:
                    #   - state check (must be draft/sent)
                    #   - credit-limit gate on Credit-payment SOs
                    #   - bank-guarantee gate on Credit-payment SOs
                    #     (parallels credit-limit — customer has a BG
                    #     ceiling and it's been exceeded)
                    #   - overdue-debt gate: partner has overdue invoices
                    #     and the override approval has not been granted
                    #   - valid-order-lines gate: SO must have at least
                    #     one billable line with qty>0 AND price>0
                    #   - expired-quotation gate: validity_date has
                    #     passed. Studio's compute already excludes
                    #     Project quotation type, so this fires only on
                    #     Sales / Repair SOs by design.
                    #
                    # Repair-only (three sub-cases inside one branch):
                    #   - Warranty repair (customer_pays=False):
                    #       needs RUG cycle resolved (approved OR
                    #       rejected). If rejected mid-flow, falls
                    #       through to the customer-pays path below.
                    #   - Customer-pays repair (customer_pays=True):
                    #       requires customer to have signed the
                    #       quotation on the portal preview before
                    #       Confirm.
                    #   - Reject-RUG:
                    #       warranty repair that fell through to
                    #       customer-pays after RUG rejection. Same
                    #       signature gate as customer-pays.
                    #   - Stock shortage applies to every repair.
                    #
                    # Non-Repair (Sales + Project):
                    #   - over-commission gate: salesperson commission
                    #     exceeds threshold and manager hasn't approved
                    #   - margin-exceed gate: SO margin below allowed
                    #     minimum on any line and manager hasn't approved
                    #
                    # Project-only:
                    #   - budget must be created AND status must be
                    #     validated or done (not draft/cancel/confirm)
                    #   - no inventory shortages / sub-contract lines
                    #   - all line prices confirmed by manager
                    #   - no un-approved new-item lines
                    #
                    # Note the customer-pays and reject-RUG branches
                    # share the same customer-signature requirement,
                    # so we OR them into one predicate for readability.
                    confirm_btns[1].set('invisible',
                        "(state not in ('draft', 'sent')) or "
                        "(x_studio_order_payment_method == 'Credit' "
                        "and x_studio_over_credit "
                        "and not x_studio_credit_limit_approved) or "
                        "(x_studio_order_payment_method == 'Credit' "
                        "and x_studio_over_bank_guarantee "
                        "and not x_studio_bank_guarantee_approved) or "
                        "(x_studio_overdue "
                        "and not x_studio_overdue_approved) or "
                        "(not x_studio_valid_order_lines) or "
                        "(x_studio_expired) or "
                        "(x_studio_quotation_type == 'Repair' and ("
                        "(not x_repair_customer_pays "
                        "and not x_studio_rug_approved "
                        "and not x_studio_rug_rejected) "
                        "or ((x_repair_customer_pays or x_studio_rug_rejected) "
                        "and not x_customer_signed) "
                        "or (not x_repair_stock_ok)"
                        ")) or "
                        "(x_studio_quotation_type in ('Sales', 'Project') and ("
                        "(x_studio_over_commission "
                        "and not x_studio_over_commission_approved) "
                        "or (x_studio_margin_exceed "
                        "and not x_studio_margin_approved)"
                        ")) or "
                        "(x_studio_quotation_type == 'Project' and ("
                        "(not x_studio_budget_created) "
                        "or (x_studio_proj_budget_status "
                        "not in ('validate', 'done')) "
                        "or (x_studio_inventory_short) "
                        "or (x_studio_price_not_confirmed) "
                        "or (x_studio_new_item_from_project)"
                        "))"
                    )
                    for btn in confirm_btns[2:]:
                        btn.set('invisible', '1')
                    # Recolour the visible Confirm (confirm_btns[1])
                    # to primary purple. Odoo core often sets it as
                    # oe_highlight / btn-primary already, but Studio's
                    # arch here has cleared the class on the second
                    # duplicate — force it back to match the rest of
                    # the header's primary actions.
                    confirm_btns[1].set('class', 'btn-primary')

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
                    "(not x_repair_customer_pays "
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

            # v222 lockdown: freeze the entire SO form on Repair-type
            # SOs at every state (draft → sent → sale → done). The SO
            # is meant to mirror the linked helpdesk ticket verbatim;
            # ad-hoc backend edits defeat that. The o2m order_line
            # field is caught by this same walk — setting readonly on
            # it hides Add-a-line and disables in-place edit / delete.
            #
            # Scope: repair SOs only. Non-repair Sales / Project flows
            # keep Odoo's core readonly rules untouched.
            #
            # v195 (superseded): earlier this gate was
            #   "x_studio_quotation_type == 'Repair' and invoice_count > 0"
            # — locking only after invoicing. v222 broadens it to lock
            # from creation onward per business requirement.
            #
            # not(ancestor::field): skip embedded views — order_line's
            # inner <tree>, invoice_ids one2many, tax_totals sub-
            # widgets, etc. Those subrecords are on other models and
            # don't have x_studio_quotation_type in their eval context.
            #
            # Ticket → SO creation writes via sudo() and bypasses
            # view-level readonly, so lines still populate on SO
            # creation — only human backend edits are blocked.
            so_lock_gate = "x_studio_quotation_type == 'Repair'"
            for field_el in arch.xpath(
                    "//sheet//field[not(ancestor::field)]"):
                if field_el.get('invisible') == '1':
                    continue
                existing = field_el.get('readonly', '')
                field_el.set(
                    'readonly',
                    f"({existing}) or ({so_lock_gate})"
                    if existing else so_lock_gate,
                )

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
        records = super().create(vals_list)
        records._fix_repair_auto_generate_quotation_type()
        # v283: newly-created SOs that came in already at state='done'
        # (rare but possible for imports/data-fix scripts) should get
        # locked on create too. No-op for the common draft-create path.
        records._fix_repair_apply_track_lock_status()
        return records

    def _fix_repair_auto_generate_quotation_type(self):
        """v277: port of Studio automation 176 / server action 1995
        'RR - Auto Generate Quotation Type for Repair SOs'.

        Sets x_studio_quotation_type='Repair' (and copies the partner's
        payment method) on any SO that is FSM-task-linked to a repair
        project. Clear-DB's version checks
        `task.project_id.x_studio_repair_project == True`. That field is
        on project.project and belongs to the deferred Group C (project
        master data) port — not yet on dev env.

        Dev-env-friendly fallback: if `x_studio_repair_project` isn't
        declared on project.project, use the presence of
        `task.helpdesk_ticket_id` (which Fix-repair itself ports) as
        the repair-flow signal. Same semantic outcome — an SO whose
        FSM task is tied to a repair helpdesk ticket is a repair SO.

        Idempotent: skips SOs whose quotation_type is already set
        to something (any value).
        """
        Task = self.env['project.task'].sudo()
        # Detect whether Group C is installed by probing the field.
        # `_fields` lookup is O(1) and avoids a per-record hasattr on
        # the browse cache.
        has_repair_project_flag = (
            'x_studio_repair_project' in self.env['project.project']._fields
        )

        def _task_is_repair(task):
            if not task:
                return False
            if has_repair_project_flag:
                return bool(task.project_id and task.project_id.x_studio_repair_project)
            # dev-env fallback: repair signal = the task is linked to a
            # repair helpdesk ticket. Fix-repair itself sets this on
            # every task created via Plan Intervention.
            return bool(task.helpdesk_ticket_id)

        for order in self:
            if not order.id:
                continue
            if order.x_studio_quotation_type:
                continue  # already set — Studio behaviour is set-once
            # Two possible link directions between sale.order and task:
            #   1. sale.order.task_id -> project.task  (SO created FROM
            #      a task, most common FSM path)
            #   2. project.task.sale_order_id -> sale.order  (task
            #      created FROM an SO; used by some create-from-quote
            #      flows)
            # Check the direct link on the SO first, then fall back
            # to searching by the reverse.
            candidate = order.task_id if order.task_id else False
            if not _task_is_repair(candidate):
                if has_repair_project_flag:
                    candidate = Task.search([
                        ('sale_order_id', '=', order.id),
                        ('project_id.x_studio_repair_project', '=', True),
                    ], limit=1)
                else:
                    candidate = Task.search([
                        ('sale_order_id', '=', order.id),
                        ('helpdesk_ticket_id', '!=', False),
                    ], limit=1)
            if not _task_is_repair(candidate):
                continue
            update = {'x_studio_quotation_type': 'Repair'}
            partner = order.partner_id
            if partner and getattr(partner, 'x_studio_payment_method', False):
                update['x_studio_order_payment_method'] = partner.x_studio_payment_method
            order.write(update)

    def action_quotation_send(self):
        action = super().action_quotation_send()
        # Apply the custom body / stage-transition treatment for
        # customer-pays repairs:
        #   • x_repair_customer_pays: repair not under warranty from the start
        #   • x_studio_rug_rejected: warranty repair whose RUG was rejected
        # Both produce the same email body (portal quote link) and drive the
        # same ticket-stage transition. Warranty repairs (customer_pays=False,
        # not-rejected) and non-repair SOs return early — nothing custom.
        if not self.x_repair_customer_pays \
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
                lambda o: o.x_repair_customer_pays
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
            if (order.x_repair_customer_pays
                    or order.x_studio_rug_rejected):
                self._move_ticket_to_stage(order, 'Estimation Approval Received')
        return result

    def action_repair_create_invoice(self):
        """Fix-repair replacement for the purple 'Create Invoice' button.

        Routes:
          - Non-RUG (x_repair_customer_pays or x_studio_rug_rejected):
            call _create_repair_full_invoice() which builds ONE
            invoice for the whole SO ignoring invoice_policy=
            'delivery' gating. No down-payment mechanism used.
          - RUG-approved (warranty): fall through to standard Odoo
            _create_invoices(). Button visibility already gates
            this branch on ticket_repair_stage_state == 'repair_completed'
            in _get_view, so we hit here after delivery is done —
            _create_invoices() then produces a normal delivered-qty
            invoice.

        Return an ir.actions.act_window opening the created invoice
        in form view. The RUG path returns the same shape so the
        button behaves consistently.
        """
        self.ensure_one()
        if self.x_repair_customer_pays or self.x_studio_rug_rejected:
            return self._create_repair_full_invoice()
        # RUG-approved / non-repair: standard Odoo behaviour
        invoices = self._create_invoices()
        if not invoices:
            raise UserError(
                "Nothing to invoice on this sale order."
            )
        return {
            'name': 'Customer Invoice',
            'view_mode': 'form',
            'res_model': 'account.move',
            'view_id': self.env.ref('account.view_move_form').id,
            'type': 'ir.actions.act_window',
            'res_id': invoices[0].id,
            'target': 'current',
        }

    def _create_repair_full_invoice(self):
        """Create ONE customer invoice for the entire SO amount for
        non-RUG (customer-pays or Reject-RUG) repair sale orders.

        Uses each order line's product_uom_qty (ordered qty) instead
        of qty_to_invoice, so the standard invoice_policy='delivery'
        gate that stalls invoicing until pickings are validated is
        bypassed. Quick repairs paid fully upfront no longer need
        the down-payment wizard.

        Refuses to run when:
          - SO isn't confirmed (state != 'sale'), or
          - An invoice already exists (any non-cancelled state).

        Skips over lines that are is_downpayment=True (from any
        legacy wizard interaction) and lines with product_uom_qty
        <= 0. Section / note lines are preserved.

        Returns an ir.actions.act_window opening the new invoice
        in form view.
        """
        self.ensure_one()
        if not (self.x_repair_customer_pays or self.x_studio_rug_rejected):
            raise UserError(
                "Full-amount invoicing is only available on non-RUG "
                "(customer-pays or Reject-RUG) repair sale orders."
            )
        if self.state != 'sale':
            raise UserError("The sale order must be confirmed first.")
        existing = self.invoice_ids.filtered(lambda i: i.state != 'cancel')
        if existing:
            raise UserError(
                "An invoice already exists for this sale order (%s). "
                "Cancel it first or use the existing invoice."
                % existing[0].name
            )

        invoice_vals = self._prepare_invoice()
        invoice_line_cmds = []
        for line in self.order_line:
            if line.display_type in ('line_section', 'line_note'):
                invoice_line_cmds.append((0, 0, {
                    'display_type': line.display_type,
                    'name': line.name,
                    'sequence': line.sequence,
                }))
                continue
            if line.is_downpayment:
                continue
            if line.product_uom_qty <= 0:
                continue
            # Force qty to the ordered qty. _prepare_invoice_line
            # already returns 'quantity': self.qty_to_invoice — the
            # override kwarg is applied AFTER via res.update(...).
            invoice_line_cmds.append((0, 0,
                line._prepare_invoice_line(quantity=line.product_uom_qty)
            ))

        if not invoice_line_cmds:
            raise UserError(
                "Nothing to invoice on this sale order — no non-"
                "downpayment lines with a positive ordered quantity."
            )

        invoice_vals['invoice_line_ids'] = invoice_line_cmds
        invoice = self.env['account.move'].create(invoice_vals)

        return {
            'name': 'Customer Invoice',
            'view_mode': 'form',
            'res_model': 'account.move',
            'view_id': self.env.ref('account.view_move_form').id,
            'type': 'ir.actions.act_window',
            'res_id': invoice.id,
            'target': 'current',
        }

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

        # v277: task_id was just set (typical FSM task-create path) —
        # re-evaluate quotation-type auto-detect. Idempotent on the
        # helper side (already-set records skip themselves).
        if 'task_id' in vals:
            self._fix_repair_auto_generate_quotation_type()

        # v283: track lock/unlock cycle for repair SOs (ports Studio
        # automations 202 + 203). Only re-evaluate when one of the
        # gate fields changed; the helper is itself guarded against
        # its own re-entry via _fix_repair_track_lock context flag.
        lock_triggers = {'state', 'x_studio_quotation_type',
                         'x_studio_locked', 'x_studio_unlocked',
                         'x_studio_re_estimate_count'}
        if lock_triggers & set(vals or ()):
            if not self.env.context.get('_fix_repair_track_lock'):
                self._fix_repair_apply_track_lock_status()

        return res

    def _fix_repair_apply_track_lock_status(self):
        """v283: port of Studio automations 202 + 203 (RR - Track Lock
        Status / - 2).

        202 (lock): when a Repair SO reaches state='done', lock it and
        sync the header's re_estimate_count from the most recent
        re-estimated line's per-line count.

        203 (unlock): when a locked Repair SO drops back to state='sale'
        (typical trigger: user re-opens for re-estimation), unlock it.

        Both are idempotent: the write is skipped when the target
        values already match. Recursion into write() is prevented by
        the _fix_repair_track_lock context flag.
        """
        Line = self.env['sale.order.line'].sudo()
        for order in self:
            if order.x_studio_quotation_type != 'Repair':
                continue
            # 202 - lock path
            if order.state == 'done':
                re_line = Line.search([
                    ('order_id', '=', order.id),
                    ('x_studio_re_estimated', '=', True),
                ], limit=1, order='id desc')
                target_count = re_line.x_studio_count_1 if re_line else 0
                needs_update = (
                    not order.x_studio_locked
                    or order.x_studio_unlocked
                    or order.x_studio_re_estimate_count != target_count
                )
                if needs_update:
                    order.with_context(_fix_repair_track_lock=True).write({
                        'x_studio_locked': True,
                        'x_studio_unlocked': False,
                        'x_studio_re_estimate_count': target_count,
                    })
            # 203 - unlock path
            elif order.state == 'sale' and order.x_studio_locked:
                order.with_context(_fix_repair_track_lock=True).write({
                    'x_studio_locked': False,
                    'x_studio_unlocked': True,
                })
