# -*- coding: utf-8 -*-
from lxml import etree
from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    nuw_block_validate = fields.Boolean(
        compute='_compute_nuw_block_validate',
    )

    repair_ticket_sent_to_sales_centre = fields.Boolean(
        compute='_compute_repair_ticket_sent_to_sales_centre',
    )

    @api.depends('x_studio_helpdesk_ticket_id', 'x_studio_helpdesk_ticket_id.stage_id')
    def _compute_repair_ticket_sent_to_sales_centre(self):
        for picking in self:
            ticket = picking.sudo().x_studio_helpdesk_ticket_id
            stage_name = (ticket.stage_id.name or '').strip() if ticket else ''
            picking.repair_ticket_sent_to_sales_centre = (
                stage_name == 'Received at Sales Centre'
            )

    @api.depends('sale_id', 'sale_id.x_studio_quotation_type')
    def _compute_nuw_block_validate(self):
        for picking in self:
            so = picking.sale_id
            if not so or so.x_studio_quotation_type != 'Not Under Warranty':
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
                for fname in ('nuw_block_validate', 'repair_ticket_sent_to_sales_centre'):
                    fld = etree.Element('field')
                    fld.set('name', fname)
                    fld.set('invisible', '1')
                    sheet.insert(0, fld)
                break
            for btn in arch.xpath("//button[@name='button_validate']"):
                existing = btn.get('invisible', '')
                extra = 'nuw_block_validate'
                btn.set('invisible', f"({existing}) or {extra}" if existing else extra)
            # Dispatch button: shown on repair collection pickings only when the
            # ticket has physically arrived ('Received at Sales Centre').
            # The arch has two button[@name='195'] elements — a Studio-injected
            # duplicate (no data-hotkey) and the standard Odoo return button
            # (data-hotkey="k"). Hide the duplicate; configure only the standard one.
            # Pass default_location_id so the wizard pre-fills the customer
            # location and _get_view / _compute_moves_locations lock it.
            cust_loc = self.env.ref('stock.stock_location_customers', raise_if_not_found=False)
            cust_loc_id = cust_loc.id if cust_loc else 5
            for btn in arch.xpath("//button[@name='195'][@type='action']"):
                if not btn.get('data-hotkey'):
                    btn.set('invisible', '1')
                else:
                    btn.set('string', 'Dispatch')
                    btn.set('invisible', 'not repair_ticket_sent_to_sales_centre')
                    btn.set('context',
                        f"{{'default_ticket_id': x_studio_helpdesk_ticket_id, "
                        f"'default_location_id': {cust_loc_id}, "
                        f"'default_picking_id': id}}"
                    )
        return arch, view

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

        # ── Path D: Dispatch pickings created via the Dispatch button ─────────
        # _create_returns stamps x_studio_helpdesk_ticket_id on the new picking.
        # When that picking is validated and either endpoint is a customer
        # location, move the ticket from 'Received at Sales Centre' to
        # 'Handed Over to Customer'.
        # The stage guard ensures the initial collection picking (also
        # customer-location, but ticket at 'New') never triggers this path.
        for picking in self.filtered(
            lambda p: p.state == 'done'
            and (
                p.location_dest_id.usage == 'customer'
                or p.location_id.usage == 'customer'
            )
        ):
            ticket = picking.sudo().x_studio_helpdesk_ticket_id
            if not ticket:
                continue
            if (ticket.sudo().stage_id.name or '').strip() == 'Received at Sales Centre':
                ticket._move_to_stage('Handed Over to Customer')

        return res
