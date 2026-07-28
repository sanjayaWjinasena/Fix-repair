# -*- coding: utf-8 -*-
from lxml import etree
from odoo import api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    nuw_block_validate = fields.Boolean(
        compute='_compute_nuw_block_validate',
    )

    # Payment-states that count as "customer has paid enough to
    # release the delivery". 'partial' is included because a partial
    # payment still means real money has been recorded against the
    # invoice; the operator wants to release the goods at that point.
    _NUW_PAID_STATES = ('partial', 'in_payment', 'paid')

    @api.depends(
        'sale_id',
        'sale_id.x_repair_customer_pays',
        'sale_id.x_studio_rug_rejected',
        'sale_id.invoice_ids.state',
        'sale_id.invoice_ids.payment_state',
    )
    def _compute_nuw_block_validate(self):
        """Block delivery Validate on customer-pays repair SO pickings
        until an actual payment has landed on at least one non-
        cancelled invoice for the linked sale order.

        Applies to any SO with x_repair_customer_pays=True (started as
        not-under-warranty) OR x_studio_rug_rejected=True (warranty
        repair fell through to customer-pays after the RUG cycle).
        Warranty-approved and non-Repair SOs pass through — this field
        stays False for them.

        Unblock rule: at least one invoice on the SO must be
        non-cancelled AND its payment_state must be in
        ('partial', 'in_payment', 'paid'). A draft or posted-but-
        not_paid invoice is not enough — the previous implementation
        unblocked as soon as any invoice_ids row existed, which let
        deliveries validate before the customer paid anything.

        Reasoning behind the states we accept:
          - 'partial'    → at least some money is in
          - 'in_payment' → payment registered, awaiting bank recon
          - 'paid'       → fully reconciled
        Everything else ('not_paid', 'reversed', 'invoicing_legacy')
        means no money has actually changed hands from the operator's
        perspective, so we keep the block.
        """
        for picking in self:
            so = picking.sale_id
            customer_pays = bool(so) and (
                so.x_repair_customer_pays
                or so.x_studio_rug_rejected
            )
            if not customer_pays:
                picking.nuw_block_validate = False
                continue
            invoices = so.invoice_ids.filtered(lambda m: m.state != 'cancel')
            picking.nuw_block_validate = not any(
                inv.payment_state in self._NUW_PAID_STATES
                for inv in invoices
            )

    def button_validate(self):
        """Server-side safety net for the delivery Validate gate.

        _compute_nuw_block_validate + the _get_view button-hide
        expression together suppress the Validate button in the UI
        when the customer-pays repair invoice has no payment against
        it yet. Re-check server-side so the gate can't be bypassed
        via a URL / API call directly hitting button_validate.
        """
        blocked = self.filtered(lambda p: p.nuw_block_validate)
        if blocked:
            raise UserError(
                "Cannot validate delivery: the customer-pays repair "
                "invoice on the linked sale order has no payment yet. "
                "Register at least a partial payment on the invoice "
                "before validating the delivery.\n\n"
                "Affected pickings:\n"
                + "\n".join("  • %s" % p.name for p in blocked)
            )
        return super().button_validate()

    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            for sheet in arch.xpath("//sheet"):
                fld = etree.Element('field')
                fld.set('name', 'nuw_block_validate')
                fld.set('invisible', '1')
                sheet.insert(0, fld)
                # Load x_studio_helpdesk_ticket_id as an invisible field
                # so the broadened hide expression below can reference
                # it. Movement transfers (internal factory / dispatch /
                # return pickings) carry this linkage but often have no
                # x_studio_quotation_type value, so the gate needs both
                # sides.
                ticket_fld = etree.Element('field')
                ticket_fld.set('name', 'x_studio_helpdesk_ticket_id')
                ticket_fld.set('invisible', '1')
                sheet.insert(0, ticket_fld)
                break
            for btn in arch.xpath("//button[@name='button_validate']"):
                existing = btn.get('invisible', '')
                extra = 'nuw_block_validate'
                btn.set('invisible', f"({existing}) or {extra}" if existing else extra)
            # Hide the Return button (action 195) entirely — returns are
            # initiated from the helpdesk ticket itself, never from the
            # picking form.
            for btn in arch.xpath("//button[@name='195']"):
                btn.set('invisible', '1')

            # Hide "Retun Reject Reason" button (typo in original
            # Studio-set string; backed by action 1999 → server
            # action "RR - Transfer Rejection"). The rejection flow
            # is deprecated in the repair workflow — no operator
            # should be reaching for it from the picking form.
            # Kept the underlying action on record so historical
            # references stay resolvable; only the button hide.
            for btn in arch.xpath("//button[@name='1999']"):
                btn.set('invisible', '1')

            # Hide UI-only fields on repair-flow pickings — every
            # variant. The workflow generates two picking-family types
            # off a repair ticket:
            #
            #   * DELIVERY pickings — created from a repair sale.order
            #     via Odoo's stock rules. These carry
            #     x_studio_quotation_type='Repair' (mirrored from the SO
            #     via Studio automation at picking creation time).
            #   * MOVEMENT pickings — internal factory transfers,
            #     dispatches to sales centre, returns, etc. These are
            #     stamped with x_studio_helpdesk_ticket_id linking back
            #     to the ticket but often have no x_studio_quotation_type
            #     (they're not SO-driven).
            #
            # Original v177 gate covered only the first case; v182
            # broadens to (quotation_type == 'Repair') OR
            # (helpdesk_ticket_id is set) so both families get the same
            # hides. Non-repair deliveries and non-repair internal
            # transfers are untouched.
            #
            # Fields stay on the model — computes that reference
            # x_studio_quotation_type / x_studio_sales_order (e.g.
            # x_studio_repair_payment_made) continue to fire because
            # invisible only affects rendering.
            hide_gate = (
                "x_studio_quotation_type == 'Repair' "
                "or x_studio_helpdesk_ticket_id"
            )
            for fname in (
                'origin',                       # Source Document
                'x_studio_sales_order',         # Sales Order (Studio duplicate of sale_id)
                'picking_type_id',              # Operation Type
                'picking_type_code',            # Type of Operation (standard selection)
                'x_studio_type_of_operation',   # Type of Operation (Studio duplicate)
                'x_studio_quotation_type',      # Quotation Type
                'owner_id',                     # Assign Owner
                'x_studio_validation',          # Validation
            ):
                for field_el in arch.xpath(f"//field[@name='{fname}']"):
                    field_el.set('invisible', hide_gate)

            # Lock repair-flow picking fields. Two branches:
            #
            #   1. Repair-SO DELIVERY pickings (quotation_type='Repair',
            #      no helpdesk_ticket_id stamp) — freeze only after
            #      Validate (state='done'). Stock managers still need
            #      to touch qty_done / lot etc. before validation.
            #
            #   2. Repair MOVEMENT pickings (helpdesk_ticket_id stamped
            #      by _create_returns and the Send-to-Factory /
            #      Received-at-Factory / Send-to-Sales-Centre /
            #      Dispatch server actions) — freeze ALWAYS, from
            #      creation onward. These are one-click transfers with
            #      every field (partner, dates, source doc, moves,
            #      serials) pre-populated by our code; the operator
            #      only needs to click Validate. Editing anything else
            #      is a data-quality risk (accidentally rewriting
            #      partner_id / origin / picking_type_id on the return
            #      would desync the ticket's smart buttons and
            #      subsequent stage transitions).
            #
            # ORed into each field's existing readonly so per-field
            # rules stay live before the picking-lock kicks in.
            #
            # Buttons (Validate, Cancel, our injected workflow
            # buttons) aren't <field> elements, so the loop leaves
            # them clickable.
            #
            # not(ancestor::field): skip fields inside embedded
            # views (move_ids_without_package, move_line_ids etc.).
            # Those sub-rows are stock.move / stock.move.line — they
            # don't have x_studio_quotation_type or
            # x_studio_helpdesk_ticket_id, so stamping the picking-
            # level lock expression on them would raise a
            # "Name not defined" during list-cell readonly eval.
            lock_gate = (
                "(x_studio_quotation_type == 'Repair' "
                "and state == 'done') "
                "or x_studio_helpdesk_ticket_id"
            )
            for field_el in arch.xpath(
                    "//sheet//field[not(ancestor::field)]"):
                if field_el.get('invisible') == '1':
                    continue
                existing = field_el.get('readonly', '')
                field_el.set(
                    'readonly',
                    f"({existing}) or ({lock_gate})"
                    if existing else lock_gate,
                )
        return arch, view

    # ── Native compute methods that back Studio compute strings ──────────
    # Same delegation pattern as sale.order / account.move.line: safe_eval
    # only sees a one-line call, the real work runs at native Python speed.
    # Field names and returned values are identical to the Studio version.

    def _fix_repair_compute_cash_full_payment_made(self):
        for rec in self:
            valid = False
            inv_found = False
            tso = rec.x_studio_ticket_sales_order
            so_amount = tso.amount_total if tso else 0
            inv_amount = 0
            if tso:
                if tso.state == 'cancel':
                    if rec.x_studio_created_from_help_ticket.x_studio_repair_complete_stage_updated:
                        valid = False
                    if rec.x_studio_helpdesk_ticket_id.x_studio_repair_complete_stage_updated:
                        valid = False
                else:
                    if tso.x_studio_order_payment_method == 'Cash':
                        for inv in tso.invoice_ids:
                            inv_amount += inv.amount_total
                            if inv.payment_state in ('not_paid', 'partial',
                                                     'reversed', 'invoicing_legacy'):
                                valid = True
                            if tso.x_studio_rug_approved:
                                valid = False
                        if so_amount > inv_amount:
                            valid = True
                    else:
                        for inv in tso.invoice_ids:
                            inv_found = True
                        if inv_found:
                            valid = False
                        else:
                            valid = True
            if rec.x_studio_created_from_help_ticket.x_studio_quick_repair_status == 'Quick Repair':
                valid = False
            if rec.x_studio_helpdesk_ticket_id.x_studio_quick_repair_status == 'Quick Repair':
                valid = False
            rec.x_studio_cash_full_payment_made = valid

    def _fix_repair_compute_fsm_task_done(self):
        for rec in self:
            value = False
            ticket = rec.x_studio_created_from_help_ticket
            if not ticket:
                ticket = rec.x_studio_helpdesk_ticket_id
            if ticket:
                for line in ticket.fsm_task_ids:
                    if line.fsm_done or line.x_studio_end_quick_repair:
                        value = True
            rec.x_studio_fsm_task_done = value

    def _fix_repair_compute_fully_paid_so(self):
        for rec in self:
            value = False
            ticket = rec.x_studio_created_from_help_ticket
            if ticket:
                so = ticket.x_studio_sale_order
                if so:
                    if so.partner_id.id:
                        if so.x_studio_order_payment_method == 'Credit':
                            value = False
                        else:
                            value = ticket.x_studio_fully_paid_so
                else:
                    if ticket.x_studio_quick_repair_status == 'Quick Repair':
                        value = True
            else:
                ticket = rec.x_studio_helpdesk_ticket_id
                if ticket:
                    so = ticket.x_studio_sale_order
                    if so:
                        if so.partner_id.id:
                            if so.x_studio_order_payment_method == 'Credit':
                                value = False
                            else:
                                value = ticket.x_studio_fully_paid_so
                    else:
                        # Original Studio code had the Quick Repair check
                        # commented-out, unconditionally setting value = True.
                        value = True
            rec.x_studio_fully_paid_so = value

    def _fix_repair_compute_need_approval(self):
        for rec in self:
            val = False
            if rec.picking_type_code == 'internal':
                if not rec.origin:
                    val = True
            elif rec.picking_type_code == 'outgoing':
                if rec.origin:
                    val = True
            rec.x_studio_need_approval = val

    def _fix_repair_compute_repair_payment_made(self):
        Payment = self.env['account.payment'].sudo()
        for rec in self:
            valid = False
            so = rec.sale_id
            if so:
                if so.x_studio_order_payment_method == 'Credit':
                    valid = True
                elif so.x_studio_rug_approved:
                    valid = True
                else:
                    payment = Payment.search([
                        ('x_studio_sales_order', '=', so.id),
                        ('state', '=', 'posted'),
                    ], limit=1)
                    if payment:
                        valid = True
                    else:
                        for inv in so.invoice_ids:
                            if inv.payment_state in ('in_payment', 'partial', 'paid'):
                                valid = True
                                break
            rec.x_studio_repair_payment_made = valid

    def _fix_repair_compute_user_location_validation(self):
        # Preserves the original Studio flow verbatim — including the
        # post-nested `if loc:` that reassigns `valid` for every
        # non-internal operation based on the last search's `loc`.
        Location = self.env['stock.location'].sudo()
        for rec in self:
            company_ids = self.env.context.get(
                'allowed_company_ids',
                [self.env.user.company_id.id],
            )
            company_id = company_ids[0]
            valid = False
            valid2 = False
            loc = Location.browse()
            if rec.x_studio_type_of_operation == 'internal':
                loc = Location.search([
                    ('id', '=', rec.location_dest_id.id),
                    ('x_studio_users_internal_transfer', 'ilike', self._uid),
                    ('active', '=', True),
                    ('company_id', '=', company_id),
                ], limit=1)
                if loc:
                    valid = False
                else:
                    valid = True
            else:
                if rec.x_studio_type_of_operation == 'outgoing':
                    if rec.x_studio_created_from_help_ticket:
                        loc = Location.search([
                            ('id', '=', rec.location_dest_id.id),
                            ('x_studio_users_stock_location', 'ilike', self._uid),
                            ('active', '=', True),
                            ('company_id', '=', company_id),
                        ], limit=1)
                        if loc:
                            valid = False
                        else:
                            valid = True
                    else:
                        loc = Location.search([
                            ('id', '=', rec.location_id.id),
                            ('x_studio_users_stock_location', 'ilike', self._uid),
                            ('active', '=', True),
                            ('company_id', '=', company_id),
                        ], limit=1)
                        if loc:
                            valid2 = False
                        else:
                            valid2 = True
                else:
                    loc = Location.search([
                        ('id', '=', rec.location_dest_id.id),
                        ('x_studio_users_stock_location', 'ilike', self._uid),
                        ('active', '=', True),
                        ('company_id', '=', company_id),
                    ], limit=1)
                if loc:
                    valid = False
                else:
                    valid = True
            rec.x_studio_user_location_validation = valid
            rec.x_studio_user_location_validation_2 = valid2

    def _fix_repair_compute_valid_factory_repair(self):
        for rec in self:
            value = False
            value2 = False
            value3 = False
            value4 = False
            ticket = rec.x_studio_created_from_help_ticket
            if ticket:
                if ticket.x_studio_receive_at_factory:
                    value = True
                if ticket.x_studio_job_location == 'Factory Repair':
                    value2 = True
                value3 = ticket.x_studio_receive_at_centre
                if ticket.pickings_count > 1:
                    value4 = True
            else:
                ticket = rec.x_studio_helpdesk_ticket_id
                if ticket:
                    if ticket.x_studio_receive_at_factory:
                        value = True
                    if ticket.x_studio_job_location == 'Factory Repair':
                        value2 = True
                    value3 = ticket.x_studio_receive_at_centre
                    if ticket.pickings_count > 1:
                        value4 = True
            rec.x_studio_factory_repair = value2
            rec.x_studio_received_at_centre = value3
            rec.x_studio_picking_count = value4
            rec.x_studio_valid_factory_repair = value

    def _fix_repair_compute_valid_transfer_lines(self):
        for rec in self:
            rec.x_studio_valid_transfer_lines = bool(
                rec.move_line_ids_without_package
                or rec.move_ids_without_package
            )

    @api.model
    def _delegate_studio_computes_to_native(self):
        """Rewrite each heavy Studio compute string on stock.picking to a
        one-line delegation call. Same functional output — every field
        returns the same value it did before, only the execution path is
        faster (native Python instead of safe_eval'd Studio code).

        Idempotent via the shared `# fix_repair:idempotent-v1` marker;
        also verifies a per-field guard substring before rewriting so
        manual Studio edits are preserved.
        """
        IrField = self.env['ir.model.fields'].sudo()
        marker = self.env['sale.order']._FIX_REPAIR_IDEMPOTENCE_MARKER

        delegations = [
            ('x_studio_cash_full_payment_made',
             'x_studio_ticket_sales_order',
             'self._fix_repair_compute_cash_full_payment_made()'),
            ('x_studio_fsm_task_done',
             'fsm_task_ids',
             'self._fix_repair_compute_fsm_task_done()'),
            ('x_studio_fully_paid_so',
             'x_studio_quick_repair_status',
             'self._fix_repair_compute_fully_paid_so()'),
            ('x_studio_need_approval',
             "picking_type_code == 'internal'",
             'self._fix_repair_compute_need_approval()'),
            ('x_studio_repair_payment_made',
             'x_studio_sales_order',
             'self._fix_repair_compute_repair_payment_made()'),
            ('x_studio_user_location_validation',
             'x_studio_users_internal_transfer',
             'self._fix_repair_compute_user_location_validation()'),
            ('x_studio_valid_factory_repair',
             'x_studio_receive_at_factory',
             'self._fix_repair_compute_valid_factory_repair()'),
            ('x_studio_valid_transfer_lines',
             'move_line_ids_without_package',
             'self._fix_repair_compute_valid_transfer_lines()'),
        ]
        for name, guard_substring, call in delegations:
            field = IrField.search([
                ('model', '=', 'stock.picking'),
                ('name', '=', name),
            ], limit=1)
            if not field:
                continue
            code = field.compute or ''
            if marker in code:
                continue
            if guard_substring not in code:
                continue
            field.write({'compute': f"{marker}\n{call}\n"})

    def _action_done(self):
        res = super()._action_done()

        # ── Path A: Repair SO pickings (warranty path only) ───────────────────
        # Move ticket through repair stages based on picking completion.
        # Reject-RUG repairs go through Path C instead — once the RUG is
        # rejected the SO behaves like Not Under Warranty (customer pays).
        repair_so_ids = set()
        for picking in self.filtered(lambda p: p.state == 'done' and p.sale_id):
            so = picking.sale_id
            if (so.x_studio_quotation_type == 'Repair'
                    and not so.x_studio_rug_rejected):
                repair_so_ids.add(so.id)

        for so in self.env['sale.order'].sudo().browse(list(repair_so_ids)):
            task = so.task_id or self.env['project.task'].sudo().search(
                [('sale_order_id', '=', so.id)], limit=1
            )
            ticket = task.helpdesk_ticket_id if task else None
            if not ticket:
                continue

            current_stage = (ticket.stage_id.name or '').strip()

            # Stages where Path A should NOT move the ticket.
            # Early stages: SO confirm auto-completes service moves — must not
            # pull the ticket forward before the customer approves.
            # Later stages: repair is done — material pickings fired by Mark as
            # Done must not pull the ticket backward to 'Repair Started'.
            _pre_repair_stages = {
                'New', 'Sent to Factory', 'Received at Factory', 'Diagnosis',
                'Estimation Sent to Customer',
                'Repair Completed', 'Sent to Sales Centre',
                'Handed Over to Customer',
            }

            if current_stage == 'Received at Sales Centre':
                self.env['sale.order']._move_ticket_to_stage(so, 'Handed Over to Customer')
            elif current_stage in _pre_repair_stages:
                pass  # don't advance until advance payment is recorded
            else:
                self.env['sale.order']._move_ticket_to_stage(so, 'Repair Started')
                all_pickings = self.env['stock.picking'].sudo().search(
                    [('sale_id', '=', so.id)]
                )
                if all_pickings and all(p.state in ('done', 'cancel') for p in all_pickings):
                    self.env['sale.order']._move_ticket_to_stage(so, 'Repair Completed')

        # ── Path C: Customer-pays SO pickings (started-NUW + Reject-RUG) ────
        # Same flow for both: customer must pay before pickings can advance
        # the ticket past Repair Started.
        nuw_so_ids = set()
        for picking in self.filtered(lambda p: p.state == 'done' and p.sale_id):
            so = picking.sale_id
            if (so.x_repair_customer_pays
                    or so.x_studio_rug_rejected):
                nuw_so_ids.add(so.id)

        for so in self.env['sale.order'].sudo().browse(list(nuw_so_ids)):
            task = so.task_id or self.env['project.task'].sudo().search(
                [('sale_order_id', '=', so.id)], limit=1
            )
            ticket = task.helpdesk_ticket_id if task else None
            if not ticket:
                continue

            current_stage = (ticket.stage_id.name or '').strip()

            # Stages where a delivery validation must not advance the ticket.
            # Everything before Advance Received = customer hasn't paid yet.
            # Everything after Repair Started = don't regress.
            _pre_repair_stages_nuw = {
                'New', 'Sent to Factory', 'Received at Factory', 'Diagnosis',
                'Estimation Sent to Customer', 'Estimation Approval Received',
                'Repair Completed', 'Sent to Sales Centre',
                'Handed Over to Customer',
            }

            if current_stage == 'Received at Sales Centre':
                self.env['sale.order']._move_ticket_to_stage(so, 'Handed Over to Customer')
            elif current_stage in _pre_repair_stages_nuw:
                pass
            else:
                # Stage is 'Advance Received' (or 'Repair Started' for subsequent pickings)
                self.env['sale.order']._move_ticket_to_stage(so, 'Repair Started')
                all_pickings = self.env['stock.picking'].sudo().search(
                    [('sale_id', '=', so.id)]
                )
                if all_pickings and all(p.state in ('done', 'cancel') for p in all_pickings):
                    self.env['sale.order']._move_ticket_to_stage(so, 'Repair Completed')

        # ── Path B: Return-to-customer handover pickings ──────────────────────
        # Pickings: Virtual/inventory location → Customer location.
        # Primary match: picking.return_id.id == ticket.x_studio_pick_id
        # (the wizard stores the original RET picking on the ticket; the
        #  2nd return reverses it, so return_id points back to that picking).
        # Fallback: partner + company + stage (for pickings not via wizard).
        #
        # Tickets eligible to move to "Handed Over to Customer":
        #   • Factory Repair / NUW-with-serial → stage = Received at Sales Centre
        #   • Centre Repair                    → stage = Repair Completed
        #     (Centre Repair skips the factory trip, so the ticket sits at
        #      Repair Completed at the moment of Dispatch)
        handover_stage_ids = self.env['helpdesk.stage'].sudo().search([
            '|',
            ('name', '=', 'Received at Sales Centre'),
            ('name', '=', 'Repair Completed'),
        ]).ids

        if handover_stage_ids:
            handover_pickings = self.filtered(
                lambda p: (
                    p.state == 'done'
                    and p.partner_id
                    and p.location_id.usage == 'inventory'
                    and p.location_dest_id.usage == 'customer'
                )
            )
            for picking in handover_pickings:
                ticket = self.env['helpdesk.ticket']
                if picking.return_id:
                    ticket = self.env['helpdesk.ticket'].sudo().search([
                        ('x_studio_pick_id', '=', picking.return_id.id),
                        ('stage_id', 'in', handover_stage_ids),
                        ('company_id', '=', picking.company_id.id),
                    ], limit=1)
                if not ticket:
                    ticket = self.env['helpdesk.ticket'].sudo().search([
                        ('partner_id', '=', picking.partner_id.id),
                        ('stage_id', 'in', handover_stage_ids),
                        ('company_id', '=', picking.company_id.id),
                        ('x_studio_rug_repair', '=', True),
                    ], limit=1)
                if ticket:
                    ticket._move_to_stage('Handed Over to Customer')

        return res
