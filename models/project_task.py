# -*- coding: utf-8 -*-
from lxml import etree
from odoo import api, fields, models
from odoo.addons.industry_fsm_sale.models.project_task import Task as FsmSaleTask


class ProjectTask(models.Model):
    _inherit = 'project.task'

    # Mirrors the linked ticket's repair_stage_state so it can be used in
    # view invisible expressions without a full related-model traversal.
    ticket_repair_stage_state = fields.Char(
        compute='_compute_ticket_repair_stage_state',
    )

    # True when this task's sale order has been cancelled. Used to bypass
    # the repair-stage gate on Mark as Done — once the SO is cancelled
    # the repair never completes, so we let the user close the task
    # anyway.
    so_cancelled = fields.Boolean(
        compute='_compute_so_cancelled',
    )

    def _compute_ticket_repair_stage_state(self):
        for task in self:
            task.ticket_repair_stage_state = (
                task.helpdesk_ticket_id.repair_stage_state or ''
            ) if task.helpdesk_ticket_id else ''

    @api.depends('sale_order_id.state')
    def _compute_so_cancelled(self):
        for task in self:
            task.so_cancelled = task.sale_order_id.state == 'cancel'

    # ─────────────────────────────────────────────────────────────────
    # Studio-owned repair fields migrated to Python
    # ─────────────────────────────────────────────────────────────────
    # These 13 x_studio_* fields on project.task are READ by the
    # Cluster 5 helpdesk.ticket stage-validation computes and by
    # Cluster 8's material_availability / re_estimate_status computes.
    # Migration completes the field ownership graph for the helpdesk
    # repair workflow. Compute strings ported verbatim from Studio.

    x_studio_end_quick_repair = fields.Boolean(
        string='End Quick Repair',
    )

    x_studio_repair_image_01 = fields.Binary(
        string='Repair Image 01',
    )

    x_studio_repair_image_02 = fields.Binary(
        string='Repair Image 02',
    )

    x_studio_repair_reason = fields.Many2many(
        'x_repair_reason',
        string='Repair Reason',
    )

    x_studio_quick_repair_status_1 = fields.Selection(
        selection=[
            ('None', 'None'),
            ('Quick Repair', 'Quick Repair'),
        ],
        string='Quick Repair Status',
    )

    # Related from linked helpdesk ticket's cluster-4 flag. Store=True
    # per Studio's row so it can be indexed/searched on task lists.
    x_studio_repair_completed_stage_updated = fields.Boolean(
        string='Repair Completed Stage Updated',
        related='helpdesk_ticket_id.x_studio_repair_complete_stage_updated',
        store=True,
        readonly=True,
    )

    # Written by x_studio_valid_delivered_so's compute as a side
    # effect. store=True stays; no auto-compute of its own.
    x_studio_valid_delivered_so2 = fields.Boolean(
        string='Valid Delivered SO2',
    )

    x_studio_fully_invoiced_so = fields.Boolean(
        string='Fully Invoiced SO',
        compute='_compute_x_studio_fully_invoiced_so',
        store=False,
        readonly=True,
    )

    def _compute_x_studio_fully_invoiced_so(self):
        for rec in self:
            valid = False
            if rec.sale_order_id != False:
                if rec.sale_order_id.state == 'cancel':
                    if rec.x_studio_repair_completed_stage_updated == True:
                        valid = True
                else:
                    if rec.sale_order_id.invoice_status == 'invoiced':
                        valid = True
            rec['x_studio_fully_invoiced_so'] = valid

    x_studio_material_availability = fields.Selection(
        selection=[
            ('Material Not Ready', 'Material Not Ready'),
            ('Material Ready', 'Material Ready'),
        ],
        string='Material Availability',
        compute='_compute_x_studio_material_availability',
        store=False,
        readonly=True,
    )

    def _compute_x_studio_material_availability(self):
        for rec in self:
            val = 'Material Not Ready'
            if rec.sale_order_id != False:
                if rec.sale_order_id.state == 'done':
                    delivery = self.env['stock.picking'].search([
                        ('sale_id', '=', rec.sale_order_id.id),
                        ('state', '=', 'done'),
                        ('picking_type_code', '=', 'outgoing'),
                        ('location_id', '!=', rec.sale_order_id.warehouse_id.lot_stock_id.id),
                    ], limit=1)
                    if delivery:
                        val = 'Material Ready'
            rec['x_studio_material_availability'] = val

    x_studio_valid_confirm_so = fields.Boolean(
        string='Valid Confirm SO',
        compute='_compute_x_studio_valid_confirm_so',
        store=False,
        readonly=True,
    )

    def _compute_x_studio_valid_confirm_so(self):
        for rec in self:
            valid = False
            if rec.sale_order_id != False:
                if rec.sale_order_id.state == 'sent':
                    valid = True
            rec['x_studio_valid_confirm_so'] = valid

    x_studio_valid_confirm2_so = fields.Boolean(
        string='Valid Confirm2 SO',
        compute='_compute_x_studio_valid_confirm2_so',
        store=False,
        readonly=True,
    )

    def _compute_x_studio_valid_confirm2_so(self):
        for rec in self:
            valid = False
            if rec.sale_order_id != False:
                if rec.sale_order_id.state == 'done':
                    valid = True
            rec['x_studio_valid_confirm2_so'] = valid

    # This compute has a SIDE EFFECT — it also writes to
    # x_studio_valid_delivered_so2 (the stored Boolean above).
    # Preserved verbatim from Studio.
    x_studio_valid_delivered_so = fields.Boolean(
        string='Valid Delivered SO',
        compute='_compute_x_studio_valid_delivered_so',
        store=False,
        readonly=True,
    )

    def _compute_x_studio_valid_delivered_so(self):
        for rec in self:
            valid = False
            valid2 = False
            if rec.sale_order_id != False:
                if rec.sale_order_id.state == 'done':
                    delivery = self.env['stock.picking'].search([
                        ('sale_id', '=', rec.sale_order_id.id),
                        ('state', '=', 'done'),
                    ], limit=1)
                    if delivery:
                        valid = True
                    loc_type = self.env['stock.location'].search([
                        ('usage', '=', 'customer'),
                    ], limit=1)
                    if loc_type:
                        delivery2 = self.env['stock.picking'].search([
                            ('sale_id', '=', rec.sale_order_id.id),
                            ('state', '=', 'done'),
                            ('location_dest_id', '=', loc_type.id),
                        ], limit=1)
                        if delivery2:
                            valid2 = True
            rec['x_studio_valid_delivered_so'] = valid
            rec['x_studio_valid_delivered_so2'] = valid2

    x_studio_valid_invoiced_so = fields.Boolean(
        string='Valid Invoiced SO',
        compute='_compute_x_studio_valid_invoiced_so',
        store=False,
        readonly=True,
    )

    def _compute_x_studio_valid_invoiced_so(self):
        for rec in self:
            valid = False
            valid2 = False
            if rec.sale_order_id.id != False:
                if rec.sale_order_id.x_studio_order_payment_method == 'Credit' or rec.sale_order_id.x_studio_rug_approved == True:
                    if rec.x_studio_repair_completed_stage_updated == True:
                        if rec.sale_order_id.state == 'cancel':
                            valid = True
                        else:
                            if rec.sale_order_id.x_studio_order_payment_method == 'Credit':
                                valid = True
                            else:
                                if rec.sale_order_id.x_studio_rug_approved == True:
                                    valid = True
                                else:
                                    payment = self.env['account.payment'].search([
                                        ('x_studio_sales_order', '=', rec.sale_order_id.id),
                                        ('state', '=', 'posted'),
                                    ])
                                    if payment:
                                        valid = True
                                    else:
                                        for invoices in rec.sale_order_id.invoice_ids:
                                            if invoices.payment_state == 'in_payment':
                                                valid = True
                                            else:
                                                valid2 = True

                                    if valid2 == True:
                                        valid = False
                else:
                    if rec.sale_order_id.state == 'cancel':
                        valid = True
                    else:
                        payment = self.env['account.payment'].search([
                            ('x_studio_sales_order', '=', rec.sale_order_id.id),
                            ('state', '=', 'posted'),
                        ])
                        if payment:
                            valid = True
                        else:
                            for invoices in rec.sale_order_id.invoice_ids:
                                if invoices.payment_state == 'in_payment':
                                    valid = True
                                else:
                                    valid2 = True

                        if valid2 == True:
                            valid = False
            rec['x_studio_valid_invoiced_so'] = valid

    @api.model
    def _migrate_studio_project_task_repair_cluster_to_base(self):
        """Flip state='manual'→'base' + unlink studio_customization
        pins for the 13 repair-related x_studio_* fields on
        project.task. Idempotent; data preserved."""
        cluster = [
            'x_studio_end_quick_repair',
            'x_studio_fully_invoiced_so',
            'x_studio_material_availability',
            'x_studio_quick_repair_status_1',
            'x_studio_repair_completed_stage_updated',
            'x_studio_repair_image_01',
            'x_studio_repair_image_02',
            'x_studio_repair_reason',
            'x_studio_valid_confirm_so',
            'x_studio_valid_confirm2_so',
            'x_studio_valid_delivered_so',
            'x_studio_valid_delivered_so2',
            'x_studio_valid_invoiced_so',
        ]
        Field = self.env['ir.model.fields'].sudo()
        rows = Field.search([
            ('model', '=', 'project.task'),
            ('name', 'in', cluster),
        ])
        manual_rows = rows.filtered(lambda f: f.state == 'manual')
        if manual_rows:
            manual_rows.write({'state': 'base'})

        ModelData = self.env['ir.model.data'].sudo()
        studio_pins = ModelData.search([
            ('model', '=', 'ir.model.fields'),
            ('res_id', 'in', rows.ids),
            ('module', '=', 'studio_customization'),
        ])
        if studio_pins:
            studio_pins.unlink()

    def _fsm_ensure_sale_order(self):
        """Create the SO if absent, then return it — without confirming.

        industry_fsm_stock overrides this method and calls action_confirm()
        immediately so stock reservations can be made. We bypass that by
        recreating the create-only logic from industry_fsm_sale directly,
        leaving the SO in draft (Quotation) until the user confirms manually.

        _sync_repair_flags() runs immediately after creation so the SO
        carries the correct quotation_type + x_repair_customer_pays from
        the moment it exists — no downstream code sees a partially-set
        record.
        """
        if not self.sale_order_id:
            self._fsm_create_sale_order()
        self._sync_repair_flags()
        return self.sale_order_id

    def _sync_repair_flags(self):
        """Mirror the linked ticket's warranty state onto the SO.

        All repair SOs carry quotation_type='Repair' (there is no
        'Not Under Warranty' selection value anymore). The
        under-warranty vs customer-pays distinction lives in the
        x_repair_customer_pays Boolean: True when the ticket's
        x_studio_rug_confirmed is False (i.e. the item is not under
        warranty and the customer will pay from the start).

        Called from _fsm_ensure_sale_order (immediately after SO
        creation) and from write() when sale_order_id is (re)linked.
        Both fields are written in a single write() so downstream
        subscribers see a consistent record.
        """
        for task in self:
            if not task.helpdesk_ticket_id or not task.sale_order_id:
                continue
            ticket = task.helpdesk_ticket_id
            so = task.sale_order_id
            desired = {
                'x_studio_quotation_type': 'Repair',
                'x_repair_customer_pays': not ticket.x_studio_rug_confirmed,
            }
            changed = {
                k: v for k, v in desired.items()
                if getattr(so, k) != v
            }
            if changed:
                so.sudo().write(changed)

    def write(self, vals):
        result = super().write(vals)
        if 'sale_order_id' in vals and vals.get('sale_order_id'):
            self._sync_repair_flags()
        return result

    def _fsm_create_sale_order(self):
        """Delegate to industry_fsm_sale's implementation, skipping industry_fsm_stock."""
        FsmSaleTask._fsm_create_sale_order(self)

    def action_fsm_validate(self, stop_running_timers=False):
        """After Mark as Done:
          - create a state='done' picking reversing the Plan-Intervention
            hop (item leaves the Repair location, back to its prior spot)
          - advance the linked helpdesk ticket to 'Repair Completed'.
        Non-repair FSM tasks have no helpdesk_ticket_id and so are
        unaffected.
        """
        res = super().action_fsm_validate(stop_running_timers=stop_running_timers)
        for task in self:
            ticket = task.helpdesk_ticket_id
            if ticket and task.fsm_done:
                ticket._create_mark_as_done_picking()
                ticket._move_to_stage('Repair Completed')
        return res

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            # Inject helper fields as invisible so they are available in
            # button invisible expressions below.
            targets = arch.xpath("//sheet") or arch.xpath("//form")
            if targets:
                for fname in ('ticket_repair_stage_state', 'so_cancelled'):
                    if not arch.xpath(f"//field[@name='{fname}']"):
                        field_el = etree.Element('field')
                        field_el.set('name', fname)
                        field_el.set('invisible', '1')
                        targets[0].insert(0, field_el)

            # New Quotation: not used in the repair workflow — hide entirely.
            for btn in arch.xpath("//button[@name='action_fsm_create_quotation']"):
                btn.set('invisible', '1')

            # Products (material) stat button: for repair tickets only show once
            # both the Repair Diagnosis Validation and Image Validation are present.
            # Non-repair FSM tasks keep their original allow_material condition.
            for btn in arch.xpath("//button[@name='action_fsm_view_material']"):
                existing = btn.get('invisible', '')
                extra = "helpdesk_ticket_id and not (x_studio_valid_diagnosis and x_studio_repair_image_01)"
                btn.set('invisible', f"({existing}) or ({extra})" if existing else extra)

            # Mark as Done: only show for repair tickets when the repair is
            # complete (ticket at Repair Completed). Non-repair FSM tasks have
            # no helpdesk_ticket_id so the guard is False and they show normally.
            # When the linked SO has been cancelled the repair never reaches
            # 'Repair Completed', so bypass the stage gate in that case so the
            # user can still close the task.
            repair_guard = (
                "helpdesk_ticket_id and "
                "ticket_repair_stage_state != 'repair_completed' and "
                "not so_cancelled"
            )
            for btn in arch.xpath(
                "//button[@name='action_fsm_validate'][@class='btn-primary']"
            ):
                existing = btn.get('invisible', 'False')
                btn.set('invisible', f"({existing}) or ({repair_guard})")

            # Secondary: also remove Studio's over-restrictive Repair/Credit conditions
            for btn in arch.xpath(
                "//button[@name='action_fsm_validate'][@class='btn-secondary']"
            ):
                btn.set('invisible',
                    f"not display_mark_as_done_secondary or ({repair_guard})")

            # Stage statusbar: make it read-only (no clicking between stages).
            # Stage transitions on repair tasks are driven by Mark as Done /
            # automations — the salesperson shouldn't be able to skip stages
            # by clicking on the bar.
            for field in arch.xpath("//field[@name='stage_id']"):
                if field.get('widget', '').startswith('statusbar'):
                    field.set('options', "{'clickable': '0', 'fold_field': 'fold'}")
                    field.set('readonly', '1')

            # In Progress / Changes Requested / Approved … state button:
            # lock it readonly so the user can't pick a new state from the
            # dropdown. State changes happen via Mark as Done / automations.
            for field in arch.xpath("//field[@name='state']"):
                field.set('readonly', '1')

            # Worksheet stat buttons (action_fsm_worksheet) — not used in
            # the repair workflow, hide entirely.
            for btn in arch.xpath("//button[@name='action_fsm_worksheet']"):
                btn.set('invisible', '1')

        return arch, view
