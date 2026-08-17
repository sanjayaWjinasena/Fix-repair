# -*- coding: utf-8 -*-
"""account.payment repair-flow overrides.

v284: port of Studio automation 241 / server action 2427
'RR - Validate Payment %'.

Clear-DB code (on_change on account.payment):
    if record.state == 'draft':
      if record.x_studio_quotation_type == 'Repair':
        sum_total = 0
        so_value = 0
        payment = env['account.payment'].search([
            ('x_studio_sales_order', '=', record.x_studio_sales_order.id),
            ('state', '=', 'posted')])
        if payment:
          for total in payment:
            sum_total += total.amount

        min_magin = record.company_id
        if min_magin:
          so_value = round(record.x_studio_sales_order.amount_total
                           * (min_magin.x_studio_advance_payment_/100), 2)

        if so_value > (record.amount + sum_total):
          raise UserError('Payment is not within the minimum precentage.')

Belt-and-braces validator: catches direct-form-edit payments that
bypass the account.payment.register wizard (which Fix-repair already
gates via _validate_repair_advance_threshold). Same threshold math,
different entry point.

Fields x_studio_sales_order + x_studio_quotation_type live on
account.payment (declared in BugFix-Sales v45). Company advance %
lives on res.company.x_studio_advance_payment_ (BugFix-Sales v22
config-cutover proxy).
"""
from odoo import api, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.onchange('amount', 'x_studio_sales_order', 'x_studio_quotation_type', 'state')
    def _fix_repair_onchange_validate_advance_pct(self):
        """Studio automation 241 port. Block the form-editing user
        when the draft payment they're building on a Repair SO would
        bring the SO's cumulative paid amount below the company's
        configured advance-payment percentage.

        Guards on:
          * state == 'draft'        (only during payment build-up)
          * quotation_type == 'Repair'
          * x_studio_sales_order set (need SO to compute threshold)
          * company advance_payment_ > 0 (min % actually configured)

        No recursion guard needed: onchange is form-scoped and the
        method only raises UserError; no writes back.
        """
        for payment in self:
            if payment.state != 'draft':
                continue
            if payment.x_studio_quotation_type != 'Repair':
                continue
            so = payment.x_studio_sales_order
            if not so:
                continue
            company = payment.company_id
            pct = getattr(company, 'x_studio_advance_payment_', 0.0) or 0.0
            if pct <= 0:
                continue
            # Sum every already-posted payment against this same SO.
            posted = self.env['account.payment'].sudo().search([
                ('x_studio_sales_order', '=', so.id),
                ('state', '=', 'posted'),
                ('id', '!=', payment.id or 0),
            ])
            sum_posted = sum(posted.mapped('amount'))
            threshold = round(so.amount_total * (pct / 100.0), 2)
            projected = round(payment.amount + sum_posted, 2)
            if threshold > projected:
                raise UserError(
                    'Payment is not within the minimum percentage.'
                )
