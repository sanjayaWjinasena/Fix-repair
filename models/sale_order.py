# -*- coding: utf-8 -*-
from odoo import api, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            # Order Payment Type: editable in draft/sent for all customers
            for el in arch.xpath("//field[@name='x_studio_order_payment_method']"):
                el.set('readonly', "state in ('cancel', 'done', 'sale')")

            # RUG Request button: only on Repair quotations, before request is sent
            rug_req_invisible = (
                "(x_studio_quotation_type != 'Repair') or "
                "(state not in ['draft', 'sent']) or "
                "(x_studio_rug_request_sent == True) or "
                "(x_studio_rug_rejected == True) or "
                "(x_studio_rug_approved == True)"
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
            for name in ('1981', '2004'):
                for btn in arch.xpath(f"//button[@name='{name}']"):
                    btn.set('invisible', rug_approve_invisible)

        return arch, view

    def write(self, vals):
        res = super().write(vals)

        # When RUG request is sent, move linked helpdesk ticket to "Estimation Sent to Customer"
        if vals.get('x_studio_rug_request_sent'):
            for order in self:
                # task_id may be unset; fall back to searching by sale_order_id
                task = order.task_id or self.env['project.task'].search(
                    [('sale_order_id', '=', order.id)], limit=1
                )
                ticket = task.helpdesk_ticket_id if task else False
                if ticket:
                    # Filter by ticket's team to avoid cross-company stage access errors
                    stage = self.env['helpdesk.stage'].search(
                        [('name', '=', 'Estimation Sent to Customer'),
                         ('team_ids', 'in', ticket.team_id.ids)],
                        limit=1
                    )
                    if stage:
                        ticket.write({'stage_id': stage.id})

        # When RUG is approved, reprice all lines to product cost price
        if vals.get('x_studio_rug_approved'):
            for order in self:
                if order.x_studio_quotation_type == 'Repair':
                    for line in order.order_line:
                        if line.product_id:
                            line.write({'price_unit': line.product_id.standard_price})

        return res
