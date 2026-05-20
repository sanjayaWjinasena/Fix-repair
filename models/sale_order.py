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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            task_id = vals.get('task_id')
            if task_id and not vals.get('x_studio_quotation_type'):
                task = self.env['project.task'].sudo().browse(task_id)
                if task.helpdesk_ticket_id:
                    vals['x_studio_quotation_type'] = 'Repair'
        return super().create(vals_list)

    def write(self, vals):
        # When a repair task is linked to an existing quotation, auto-set type to Repair
        if vals.get('task_id') and not vals.get('x_studio_quotation_type'):
            task = self.env['project.task'].sudo().browse(vals['task_id'])
            if task.helpdesk_ticket_id:
                vals = dict(vals, x_studio_quotation_type='Repair')

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
