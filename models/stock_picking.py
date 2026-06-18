# -*- coding: utf-8 -*-
from lxml import etree
from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    nuw_block_validate = fields.Boolean(
        compute='_compute_nuw_block_validate',
    )

    @api.depends(
        'sale_id',
        'sale_id.x_studio_quotation_type',
        'sale_id.x_studio_rug_rejected',
    )
    def _compute_nuw_block_validate(self):
        # The same delivery-validation gate that applies to Not Under
        # Warranty SOs must also apply to Repair SOs whose RUG has been
        # rejected — in both cases the customer pays before delivery.
        for picking in self:
            so = picking.sale_id
            customer_pays = bool(so) and (
                so.x_studio_quotation_type == 'Not Under Warranty'
                or so.x_studio_rug_rejected
            )
            if not customer_pays:
                picking.nuw_block_validate = False
                continue
            task = so.sudo().task_id or self.env['project.task'].sudo().search(
                [('sale_order_id', '=', so.id)], limit=1
            )
            ticket = task.sudo().helpdesk_ticket_id if task else None
            if not ticket:
                picking.nuw_block_validate = False
                continue
            stage_name = (ticket.sudo().stage_id.name or '').strip()
            picking.nuw_block_validate = stage_name not in ('Advance Received', 'Repair Started')

    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            for sheet in arch.xpath("//sheet"):
                fld = etree.Element('field')
                fld.set('name', 'nuw_block_validate')
                fld.set('invisible', '1')
                sheet.insert(0, fld)
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
        return arch, view

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

        # ── Path C: Customer-pays SO pickings (NUW + Reject-RUG) ─────────────
        # Same flow for both: customer must pay before pickings can advance
        # the ticket past Repair Started.
        nuw_so_ids = set()
        for picking in self.filtered(lambda p: p.state == 'done' and p.sale_id):
            so = picking.sale_id
            if (so.x_studio_quotation_type == 'Not Under Warranty'
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
