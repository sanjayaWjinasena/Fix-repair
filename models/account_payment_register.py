# -*- coding: utf-8 -*-
from odoo import models


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def action_create_payments(self):
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
                lambda o: o.x_studio_quotation_type == 'Not Under Warranty'
            ):
                task = order.sudo().task_id or self.env['project.task'].sudo().search(
                    [('sale_order_id', '=', order.id)], limit=1
                )
                ticket = task.sudo().helpdesk_ticket_id if task else None
                if ticket and (ticket.sudo().stage_id.name or '').strip() == 'Estimation Approval Received':
                    order._move_ticket_to_stage(order, 'Advance Received')
        return result
