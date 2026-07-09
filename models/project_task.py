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
