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

        # ── Path C: Not Under Warranty SO pickings ───────────────────────────
        nuw_so_ids = set()
        for picking in self.filtered(lambda p: p.state == 'done' and p.sale_id):
            if picking.sale_id.x_studio_quotation_type == 'Not Under Warranty':
                nuw_so_ids.add(picking.sale_id.id)

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
                ticket = self.env['helpdesk.ticket']
                if picking.return_id:
                    ticket = self.env['helpdesk.ticket'].sudo().search([
                        ('x_studio_pick_id', '=', picking.return_id.id),
                        ('stage_id', 'in', received_stage_ids),
                        ('company_id', '=', picking.company_id.id),
                    ], limit=1)
                if not ticket:
                    ticket = self.env['helpdesk.ticket'].sudo().search([
                        ('partner_id', '=', picking.partner_id.id),
                        ('stage_id', 'in', received_stage_ids),
                        ('company_id', '=', picking.company_id.id),
                        ('x_studio_rug_repair', '=', True),
                    ], limit=1)
                if ticket:
                    ticket._move_to_stage('Handed Over to Customer')

        return res
