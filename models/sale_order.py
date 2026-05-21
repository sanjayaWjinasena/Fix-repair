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

            # Quotation Type: lock to Repair once set — cannot be changed away from Repair
            for el in arch.xpath("//field[@name='x_studio_quotation_type']"):
                el.set('readonly',
                       "x_studio_quotation_type == 'Repair' or "
                       "(task_id != False) or "
                       "(state not in ['draft', 'sent'])")

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
            # Approve: rewire to our method so it confirms the SO directly (no send wizard)
            for btn in arch.xpath("//button[@name='1981']"):
                btn.set('invisible', rug_approve_invisible)
                btn.set('type', 'object')
                btn.set('name', 'action_approve_rug_direct')
            # Reject: keep Studio server action, only override visibility
            for btn in arch.xpath("//button[@name='2004']"):
                btn.set('invisible', rug_approve_invisible)

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

    def action_approve_rug_direct(self):
        self.write({'x_studio_rug_approved': True})
        return self.action_confirm()

    def _move_ticket_to_stage(self, order, stage_name):
        """Find the linked helpdesk ticket and move it to the named stage."""
        sudo_order = order.sudo()
        task = sudo_order.task_id or self.env['project.task'].sudo().search(
            [('sale_order_id', '=', order.id)], limit=1
        )
        ticket = task.sudo().helpdesk_ticket_id if task else False
        if not ticket:
            return
        stage = self.env['helpdesk.stage'].sudo().search(
            [('name', '=', stage_name),
             ('team_ids', 'in', ticket.team_id.ids)],
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
