# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    # True once the salesperson has typed a value into the Amount
    # field on the register-payment wizard. Odoo's default
    # _compute_amount depends on currency_id / journal_id and other
    # signals — changing the Journal after the user has entered a
    # partial-payment amount would re-derive amount from the
    # invoice's full residual, silently overpaying. Trap the user's
    # edit via onchange and skip the recompute for that wizard row.
    #
    # Non-stored: transient wizard, one shot per open, no need to
    # persist. Default False so a fresh wizard doesn't preserve a
    # ghost value.
    x_amount_user_touched = fields.Boolean(store=False, default=False)

    @api.onchange('amount')
    def _bugfix_repair_mark_amount_touched(self):
        """Onchange fires only on client-side user edits (not on
        server-side compute writes), so this reliably distinguishes
        'user typed a value' from 'Odoo recomputed the default'.

        We deliberately do NOT reset the flag when the value goes
        back to the full residual — that would mean a user who
        typed the full amount by hand then changed Journal would
        still get the reset. Once touched, it stays touched for
        this wizard instance.
        """
        for wizard in self:
            wizard.x_amount_user_touched = True

    def _compute_amount(self):
        """Preserve a user-set Amount across Journal / currency
        recomputes.

        Save the wizard rows the salesperson has already touched
        BEFORE calling super() (which unconditionally rewrites
        amount from source_amount + currency conversion). Restore
        those values AFTER super so the write cascade sees the
        right final value. Rows that weren't touched fall through
        to Odoo's default behaviour — a wizard just opened will
        still auto-fill with the invoice's residual amount.
        """
        preserved = {
            wizard.id: wizard.amount
            for wizard in self
            if wizard.x_amount_user_touched
        }
        super()._compute_amount()
        if not preserved:
            return
        for wizard in self:
            if wizard.id in preserved:
                wizard.amount = preserved[wizard.id]

    # Ticket stages that come BEFORE Advance Received in the repair
    # workflow. When the first (or any subsequent) invoice payment
    # posts on a non-RUG-approved repair SO and the linked ticket is
    # sitting at one of these stages, we advance it. Stages AT or
    # AFTER Advance Received are no-ops — never regress a ticket that
    # is already past this milestone.
    _PRE_ADVANCE_STAGES = frozenset({
        'New',
        'Sent to Factory',
        'Received at Factory',
        'Diagnosis',
        'Estimation Sent to Customer',
        'Estimation Approval Received',
    })

    # Payment states we treat as "real money has landed against the
    # invoice". Includes 'partial' — the FIRST payment on a repair
    # invoice is nearly always an advance (e.g. 50% of the SO total),
    # so payment_state stays at 'partial' after posting. Prior
    # implementations skipped 'partial' and missed the stage move
    # for the very case the workflow was designed around.
    _MONEY_IN_STATES = ('partial', 'in_payment', 'paid')

    def action_create_payments(self):
        # Enforce the advance-payment threshold before any payment
        # record is created. Raises if the cumulative amount that
        # would be paid on a non-RUG repair invoice after this
        # payment posts is below the configured minimum percentage.
        self._validate_repair_advance_threshold()

        invoices = self.line_ids.move_id.filtered(
            lambda m: m.move_type == 'out_invoice'
        )
        result = super().action_create_payments()
        for invoice in invoices:
            invoice.invalidate_recordset(['payment_state'])
            if invoice.payment_state not in self._MONEY_IN_STATES:
                continue
            orders = invoice.invoice_line_ids.sale_line_ids.order_id
            # Advance the ticket for every non-RUG-approved repair SO
            # linked to this invoice. "Non-RUG-approved" covers three
            # cases the workflow treats as customer-pays for the
            # advance step:
            #   * customer_pays=True   — started as not-under-warranty
            #   * rug_rejected=True    — warranty repair fell through
            #                            to customer-pays after RUG
            #                            rejection
            #   * rug_approved=False   — warranty cycle not yet
            #                            resolved (defensive; invoices
            #                            usually don't exist yet here,
            #                            but if operations creates one
            #                            manually we still want to
            #                            advance the ticket on payment)
            for order in orders.filtered(
                lambda o: (
                    o.x_studio_quotation_type == 'Repair'
                    and not o.x_studio_rug_approved
                )
            ):
                task = order.sudo().task_id or self.env['project.task'].sudo().search(
                    [('sale_order_id', '=', order.id)], limit=1
                )
                ticket = task.sudo().helpdesk_ticket_id if task else None
                if not ticket:
                    continue
                current_stage = (ticket.sudo().stage_id.name or '').strip()
                if current_stage in self._PRE_ADVANCE_STAGES:
                    order._move_ticket_to_stage(order, 'Advance Received')
        return result

    def _validate_repair_advance_threshold(self):
        """Block payment registration on non-RUG repair invoices when
        the cumulative amount paid after this payment posts would
        fall below the company's configured advance-payment
        percentage on x_minimum_sales_margin.

        Applies to every account.move on this wizard whose linked
        sale.order carries x_repair_customer_pays=True or
        x_studio_rug_rejected=True. RUG-approved (warranty) repair
        SOs and non-Repair SOs pass through untouched.

        Threshold lookup is company-scoped: read the
        x_minimum_sales_margin row for the SO's own company_id.
        Skip validation when no row exists for that company or the
        advance-payment percentage is 0 — those cases mean 'no
        minimum configured'.

        Edge cases:
          - Refund moves (out_refund) are ignored — a refund is not
            a customer payment against a repair invoice.
          - Multi-invoice wizards: check each invoice independently
            using self.amount as the total payment for that
            invoice. Common repair flow is single-invoice per
            wizard so this is accurate. Multi-invoice groups
            (rare in this workflow) may over-approve if the wizard
            spreads self.amount across several invoices — refine
            later if that becomes an operational issue.
        """
        for wizard in self:
            invoices = wizard.line_ids.mapped('move_id').filtered(
                lambda m: m.move_type == 'out_invoice'
            )
            for invoice in invoices:
                orders = invoice.invoice_line_ids.mapped('sale_line_ids.order_id')
                non_rug = orders.filtered(
                    lambda o: o.x_repair_customer_pays
                              or o.x_studio_rug_rejected
                )
                for order in non_rug:
                    config = self.env['x_minimum_sales_margin'].sudo().search(
                        [('x_studio_company_id', '=', order.company_id.id)],
                        limit=1,
                    )
                    if not config:
                        continue
                    pct = config.x_studio_advance_payment_ or 0.0
                    if pct <= 0:
                        continue
                    threshold = round(order.amount_total * pct / 100.0, 2)
                    already_paid = invoice.amount_total - invoice.amount_residual
                    projected = round(already_paid + wizard.amount, 2)
                    if projected < threshold:
                        currency = order.currency_id.symbol or ''
                        raise UserError(
                            "Advance Payment should be at least %s%% of "
                            "the sale order total (%s %s). This payment "
                            "brings the total paid on %s to %s %s, which "
                            "is below the required minimum. Please "
                            "increase the payment amount."
                            % (
                                self._format_pct(pct),
                                currency,
                                self._format_money(threshold),
                                invoice.name,
                                currency,
                                self._format_money(projected),
                            )
                        )

    @staticmethod
    def _format_pct(value):
        """Trim trailing zeros so 50.0 renders as '50' but 12.5 stays '12.5'."""
        return ('%f' % value).rstrip('0').rstrip('.')

    @staticmethod
    def _format_money(value):
        return '{:,.2f}'.format(value)
