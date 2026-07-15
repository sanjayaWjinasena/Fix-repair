# -*- coding: utf-8 -*-
from odoo import models
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

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
            if invoice.payment_state not in ('in_payment', 'paid'):
                continue
            orders = invoice.invoice_line_ids.sale_line_ids.order_id
            for order in orders.filtered(
                lambda o: o.x_repair_customer_pays
                          or o.x_studio_rug_rejected
            ):
                task = order.sudo().task_id or self.env['project.task'].sudo().search(
                    [('sale_order_id', '=', order.id)], limit=1
                )
                ticket = task.sudo().helpdesk_ticket_id if task else None
                if ticket and (ticket.sudo().stage_id.name or '').strip() == 'Estimation Approval Received':
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
