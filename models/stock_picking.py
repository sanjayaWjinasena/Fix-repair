# -*- coding: utf-8 -*-
from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        res = super()._action_done()

        # ── Path A: Repair SO pickings ────────────────────────────────────────
        # Move ticket through repair stages based on picking completion
        repair_so_ids = set()
        for picking in self.filtered(lambda p: p.state == 'done' and p.sale_id):
            if picking.sale_id.x_studio_quotation_type == 'Repair':
                repair_so_ids.add(picking.sale_id.id)

        for so in self.env['sale.order'].sudo().browse(list(repair_so_ids)):
            task = so.task_id or self.env['project.task'].sudo().search(
                [('sale_order_id', '=', so.id)], limit=1
            )
            ticket = task.helpdesk_ticket_id if task else None
            if not ticket:
                continue

            current_stage = (ticket.stage_id.name or '').strip()

            if current_stage == 'Received at Sales Centre':
                self.env['sale.order']._move_ticket_to_stage(so, 'Handed Over to Customer')
            else:
                self.env['sale.order']._move_ticket_to_stage(so, 'Repair Started')
                all_pickings = self.env['stock.picking'].sudo().search(
                    [('sale_id', '=', so.id)]
                )
                if all_pickings and all(p.state in ('done', 'cancel') for p in all_pickings):
                    self.env['sale.order']._move_ticket_to_stage(so, 'Repair Completed')

        # ── Path B: Type-2 handover pickings (not linked to a Repair SO) ─────
        # These move FROM a virtual/inventory location TO the customer, i.e.
        # "sales centre gives the repaired item back to the customer".
        # They may be on a Sales SO or have no SO at all, so Path A misses them.
        # We detect them by location.usage and match tickets by partner + company.
        received_stage_ids = self.env['helpdesk.stage'].sudo().search(
            [('name', '=', 'Received at Sales Centre')]
        ).ids

        if received_stage_ids:
            handover_pickings = self.filtered(
                lambda p: (
                    p.state == 'done'
                    and p.partner_id
                    and p.location_id.usage == 'inventory'
                    and p.location_dest_id.usage == 'customer'
                )
            )
            for picking in handover_pickings:
                tickets = self.env['helpdesk.ticket'].sudo().search([
                    ('partner_id', '=', picking.partner_id.id),
                    ('stage_id', 'in', received_stage_ids),
                    ('company_id', '=', picking.company_id.id),
                ])
                tickets._move_to_stage('Handed Over to Customer')

        return res
