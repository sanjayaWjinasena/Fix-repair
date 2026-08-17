# -*- coding: utf-8 -*-
import datetime

from lxml import etree
from odoo import api, fields, models
from odoo.exceptions import UserError
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

    # ─────────────────────────────────────────────────────────────────
    # Leftover Studio repair-workflow fields (v162)
    # ─────────────────────────────────────────────────────────────────
    # These 9 x_studio_* fields on project.task weren't in the 13-item
    # Cluster 5 list but every one is referenced by view 3019's Studio
    # arch or by Fix-repair Python. Ported verbatim from their Studio
    # runtime definitions (ttype, related chain, selection choices,
    # store flag, compute string) so the state='manual' → 'base' flip
    # in _migrate_studio_leftover_repair_fields below resolves against
    # these declarations instead of dropping the fields from the
    # registry.

    # Related to the linked helpdesk ticket's Cluster 3 cancel flag.
    # Store=True per Studio so it's searchable / indexable on task
    # lists.
    x_studio_cancelled = fields.Boolean(
        string='Cancelled',
        related='helpdesk_ticket_id.x_studio_cancelled',
        store=True,
        readonly=True,
    )

    # Plain stored datetime — no compute, editable, marked copied=True
    # in Studio.
    x_studio_created_date = fields.Datetime(
        string='Created Date',
        copy=True,
    )

    # One2many onto the Studio-manual x_task_diagnosis catalogue via
    # its x_studio_task_id many2one back-reference. Both sides remain
    # DB-level Studio artefacts; the field itself is now Python-owned.
    x_studio_diagnosis_ids = fields.One2many(
        'x_task_diagnosis',
        'x_studio_task_id',
        string='Diagnosis Ids',
    )

    # v276: three remaining Studio-manual fields ported verbatim from
    # Clear-DB. All three are cross-cutting between repair and other
    # workflows on the same project.task record.
    x_studio_payment_type = fields.Selection(
        selection=[
            ('Cash', 'Cash'),
            ('Credit', 'Credit'),
            ('Advance', 'Advance'),
        ],
        string='Payment Type',
    )
    x_studio_starting_date = fields.Datetime(
        string='Starting Date',
    )
    # Studio-generated stat counter: number of sale.order records whose
    # task_id points at this task. Kept as a plain integer to preserve
    # arch references (Studio wired a stat button to it); actual value
    # would be computed by Odoo/Studio in prod. Non-stored, no compute
    # here — reads return 0 on dev env unless separately populated.
    x_task_id_sale_order_count = fields.Integer(
        string='Task Id Sale Order Count',
    )

    # Non-stored computed. Studio's original compute added a no-op
    # branch that set valid=False when it was already False — dropped
    # from the port; observable behaviour is unchanged.
    x_studio_incomplete_delivery_available = fields.Boolean(
        string='Incomplete Delivery Available',
        compute='_compute_x_studio_incomplete_delivery_available',
        store=False,
        readonly=True,
    )

    @api.depends('sale_order_id', 'sale_order_id.state')
    def _compute_x_studio_incomplete_delivery_available(self):
        Picking = self.env['stock.picking']
        for rec in self:
            valid = False
            so = rec.sale_order_id
            if so and so.state != 'cancel':
                open_delivery = Picking.search(
                    [('sale_id', '=', so.id), ('state', '!=', 'done')],
                    limit=1,
                )
                if open_delivery:
                    valid = open_delivery.state != 'cancel'
                else:
                    any_delivery = Picking.search(
                        [('sale_id', '=', so.id)], limit=1,
                    )
                    valid = not any_delivery
            rec['x_studio_incomplete_delivery_available'] = valid

    x_studio_priority = fields.Selection(
        selection=[
            ('Highest', 'Highest'),
            ('High', 'High'),
            ('Normal', 'Normal'),
            ('Low', 'Low'),
            ('Lowest', 'Lowest'),
        ],
        string='Priority',
        copy=True,
    )

    # Related to sale.order.x_studio_quotation_type (still Studio-
    # manual on sale.order — outside this migration's scope, but
    # related fields work fine across state='manual'/'base' boundaries).
    x_studio_quotation_type = fields.Selection(
        selection=[
            ('Sales', 'Sales'),
            ('Project', 'Project'),
            ('Repair', 'Repair'),
        ],
        string='Quotation Type',
        related='sale_order_id.x_studio_quotation_type',
        store=True,
        readonly=True,
    )

    x_studio_related_information = fields.Binary(
        string='Related Information',
        related='helpdesk_ticket_id.x_studio_related_information',
        store=True,
        readonly=True,
    )

    # Non-stored computed. Studio's compute was equivalent to a
    # bool() of the one2many; the loop pattern is preserved verbatim
    # in commentary but the port uses the shorter expression.
    x_studio_valid_diagnosis = fields.Boolean(
        string='Valid Diagnosis',
        compute='_compute_x_studio_valid_diagnosis',
        store=False,
        readonly=True,
    )

    @api.depends('x_studio_diagnosis_ids')
    def _compute_x_studio_valid_diagnosis(self):
        for rec in self:
            rec.x_studio_valid_diagnosis = bool(rec.x_studio_diagnosis_ids)

    x_studio_warranty_card = fields.Binary(
        string='Warranty Card',
        related='helpdesk_ticket_id.x_studio_warranty_card',
        store=True,
        readonly=True,
    )

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

    def _repair_auto_update_helpdesk_pipeline_status_1(self):
        """Studio server action id 2003 native port. When a task is
        created for a helpdesk ticket that's still in an early stage
        (New / Received at Factory) AND already has an FSM task,
        promote the ticket to 'Diagnosis' and record audit slot 3.
        """
        for record in self:
            if not record.helpdesk_ticket_id:
                continue
            company_id = self.env.context.get(
                'allowed_company_ids', [self.env.user.company_id.id]
            )[0]
            company = self.env['res.company'].browse(company_id)
            ticket = self.env['helpdesk.ticket'].search([
                ('id', '=', record.helpdesk_ticket_id.id),
            ], limit=1)
            if not ticket:
                continue
            now = datetime.datetime.now()
            if company.id == 1:
                if ticket.stage_id.id == 1 or ticket.stage_id.id == 6:
                    if ticket.fsm_task_count > 0:
                        ticket.write({
                            'stage_id': 2,
                            'x_studio_stage_date': now,
                            'x_studio_created_by_3': self.env.uid,
                            'x_studio_created_on_3': now,
                        })
            else:
                if ticket.stage_id.id == 20 or ticket.stage_id.id == 25:
                    if ticket.fsm_task_count > 0:
                        ticket.write({
                            'stage_id': 21,
                            'x_studio_stage_date': now,
                            'x_studio_created_by_3': self.env.uid,
                            'x_studio_created_on_3': now,
                        })

    @api.model_create_multi
    def create(self, vals_list):
        """Replaces automation 179 'RR - Auto Update Helpdesk Pipeline
        Status - 1' (on_create_or_write, trigger_field=create_date —
        fire-on-create-only pattern)."""
        records = super().create(vals_list)
        records._repair_auto_update_helpdesk_pipeline_status_1()
        return records

    def _repair_studio_end_quick_repair(self):
        """Studio server action id 2316 native port. Marks the task's
        quick-repair flags and advances the linked ticket to the
        Repair Completed stage (id 9 on company 1, id 28 on company 2)
        with audit slot 8. Verbatim behavior — same field writes, same
        stage-id resolution."""
        for record in self:
            if not record.id:
                continue
            company_id = self.env.context.get(
                'allowed_company_ids', [self.env.user.company_id.id]
            )[0]
            company = self.env['res.company'].browse(company_id)
            stage = 9 if company.id == 1 else 28
            record.x_studio_end_quick_repair = True
            record.x_studio_quick_repair_status_1 = 'Quick Repair'
            ticket = self.env['helpdesk.ticket'].search([
                ('id', '=', record.helpdesk_ticket_id.id),
            ], limit=1)
            if ticket:
                now = datetime.datetime.now()
                ticket.write({
                    'x_studio_repair_complete_stage_updated': True,
                    'stage_id': stage,
                    'x_studio_stage_date': now,
                    'x_studio_created_by_8': self.env.uid,
                    'x_studio_created_on_8': now,
                    'x_studio_quick_repair_status': 'Quick Repair',
                })

    def _repair_studio_diagnosis_validation(self):
        """Studio server action id 2224 native port. Unconditional
        guard raise — the pre-condition is enforced at the button /
        automation trigger level, not here."""
        for record in self:
            if not record.id:
                continue
            raise UserError(
                'Atleast one repair diagnosis line must be specified '
                'for the selected task.'
            )

    def _repair_studio_image_validation(self):
        """Studio server action id 2242 native port. Same unconditional
        guard-raise pattern as _repair_studio_diagnosis_validation."""
        for record in self:
            if not record.id:
                continue
            raise UserError(
                'Atleast one repair image should be uploaded for the '
                'selected task.'
            )

    def _repair_studio_validate_diagnosis_lines(self):
        """Studio server action id 2219 native port. Fires from an
        automation on write; raises if the task is linked to a
        helpdesk ticket but its diagnosis is not yet valid."""
        for record in self:
            if not record.helpdesk_ticket_id:
                continue
            if not record.x_studio_valid_diagnosis:
                raise UserError('Repair diagnosis must be specified.')

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
            # v258: extended the sentinel list — on standalone the base
            # project.task arch doesn't happen to mention these fields,
            # so OWL's FormRenderer raises "Name … is not defined" when
            # our injected invisible expressions reference them. Clear-
            # DB masks this because Studio's project.task view already
            # renders (invisibly) most of these fields elsewhere.
            targets = arch.xpath("//sheet") or arch.xpath("//form")
            if targets:
                for fname in (
                    'ticket_repair_stage_state',
                    'so_cancelled',
                    # v258 additions — read from the invisible/readonly
                    # expressions our _get_view adds below.
                    'helpdesk_ticket_id',
                    'sale_order_id',
                    'x_studio_valid_diagnosis',
                    'x_studio_repair_image_01',
                    'x_studio_end_quick_repair',
                    'x_studio_cancelled',
                ):
                    if not arch.xpath(f"//field[@name='{fname}']"):
                        field_el = etree.Element('field')
                        field_el.set('name', fname)
                        field_el.set('invisible', '1')
                        targets[0].insert(0, field_el)

                # v207 — inline warning banners for missing repair
                # data. Replaces the v205/v206 JS notification
                # approach (useEffect on record.data slots — didn't
                # reliably dismiss on image upload because the
                # binary widget's mutation didn't propagate to the
                # reactive proxy the effect was watching).
                #
                # Use the SAME invisible-expression pattern the
                # original Studio buttons used (action 2224 / 2242
                # — removed in v190). Odoo's built-in view-attr
                # reactivity re-evaluates these expressions on
                # every field change, so the banners hide the
                # instant the field is populated — no save needed.
                #
                # Visibility mirrors the buttons' old invisible
                # exactly (minus the arch-caching quirks that were
                # avoided by rebuilding the arch in v190's sanitize):
                #   * helpdesk_ticket_id must be set (repair task).
                #   * x_studio_cancelled must NOT be True.
                #   * x_studio_end_quick_repair must NOT be True.
                #   * The specific data field must be missing.
                #
                # Idempotent — bail if banners already there
                # (subsequent _get_view calls on the same arch).
                # v208 — inject reactivity-trigger divs. The arch
                # invisible expression is the reliable mechanism
                # (v207 confirmed it dismisses on field change with
                # zero delay). But the user wants toast notifications
                # rather than inline banners. Solution: keep the
                # arch divs so Odoo's built-in reactivity governs
                # when they appear/disappear from the DOM, but style
                # them display:none via CSS and have a JS asset watch
                # for their DOM presence to fire / dismiss toasts.
                #
                # The two <div> elements below therefore serve as
                # reactivity anchors. Never visually rendered. The
                # fix_repair_task_toast_trigger class + variant class
                # are the JS observer's hook.
                if not arch.xpath("//div[contains(@class,'fix_repair_task_toast_trigger--diagnosis')]"):
                    diag = etree.Element('div')
                    diag.set(
                        'class',
                        'fix_repair_task_toast_trigger '
                        'fix_repair_task_toast_trigger--diagnosis',
                    )
                    diag.set('invisible',
                        "not helpdesk_ticket_id or "
                        "x_studio_end_quick_repair or "
                        "x_studio_cancelled or "
                        "x_studio_valid_diagnosis"
                    )
                    targets[0].insert(0, diag)

                if not arch.xpath("//div[contains(@class,'fix_repair_task_toast_trigger--image')]"):
                    img = etree.Element('div')
                    img.set(
                        'class',
                        'fix_repair_task_toast_trigger '
                        'fix_repair_task_toast_trigger--image',
                    )
                    img.set('invisible',
                        "not helpdesk_ticket_id or "
                        "x_studio_end_quick_repair or "
                        "x_studio_cancelled or "
                        "x_studio_repair_image_01"
                    )
                    targets[0].insert(0, img)

            # UI-only field hides. Kept in Python so we can operate
            # on the fully-merged arch — some of these fields are
            # inserted by other modules' inherits (sale_project,
            # project_enterprise, studio_customization) and can't
            # be reliably targeted from an XML inherit that points
            # at project.view_task_form2 (the base). Hiding here
            # gracefully skips any field not present in this
            # install. All fields keep their DB columns, computes,
            # and constraints — only the render is suppressed.
            # Gate all four hides on helpdesk_ticket_id: only tasks
            # created from a helpdesk ticket (i.e. via Plan Intervention
            # on a repair ticket) get these fields hidden. Plain
            # project.task records outside the repair flow continue to
            # show Tags / Sales Order Item / Planned Date / Material
            # Availability normally.
            for fname in (
                'tag_ids',                          # Tags
                'sale_line_id',                     # Sales Order Item
                'planned_date_begin',               # Planned Date / Start date
                'x_studio_material_availability',   # Material Availability
            ):
                for field_el in arch.xpath(f"//field[@name='{fname}']"):
                    field_el.set('invisible', 'helpdesk_ticket_id')

            # Freeze the task form (including its notebook pages) once
            # a linked sale.order exists. On the repair workflow, a
            # task's sale_order_id is set as soon as Plan Intervention
            # confirms the SO — any subsequent edit to task fields
            # (Diagnosis, Repair Image, Warranty Card, etc.) would
            # drift away from what the SO / invoice / picking cycle
            # has already booked against. Gate applies only to repair
            # tasks (helpdesk_ticket_id set) so plain project.task
            # records outside the repair flow retain full editability.
            #
            # ORed into each field's existing readonly expression via
            # "(existing) or (helpdesk_ticket_id and sale_order_id)"
            # so per-field readonly gates from Studio / core Odoo
            # keep firing before this ticket-level freeze.
            #
            # Buttons (Mark as Done, Products smart button, etc.)
            # aren't <field> elements so the loop leaves them alone
            # — same rationale as helpdesk.ticket.x_ticket_locked.
            #
            # not(ancestor::field): skip fields nested inside another
            # field's embedded view (one2many sub-lists like subtasks,
            # timesheets, stock.moves). Those subrecords are on
            # different models and don't have helpdesk_ticket_id /
            # sale_order_id — stamping the expression on them raises
            # "Name not defined" when Odoo's ListRenderer evaluates
            # the readonly per-cell.
            for field_el in arch.xpath(
                    "//sheet//field[not(ancestor::field)]"):
                if field_el.get('invisible') == '1':
                    continue
                existing = field_el.get('readonly', '')
                extra = 'helpdesk_ticket_id and sale_order_id'
                field_el.set(
                    'readonly',
                    f"({existing}) or ({extra})" if existing else extra,
                )

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

            # Recolour every Mark as Done variant to primary purple.
            # Odoo's stock arch declares two action_fsm_validate
            # buttons — one btn-primary, one btn-secondary — each
            # gated for different states (timesheet-timer-running,
            # allow_billable, etc). Whichever surfaces should render
            # in the primary accent so the salesperson sees the same
            # visual cue regardless of state. Runs AFTER the existing
            # invisibility loops so the xpath [@class='btn-secondary']
            # lookup above still matches the arch's original class.
            for btn in arch.xpath("//button[@name='action_fsm_validate']"):
                btn.set('class', 'btn-primary')

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
