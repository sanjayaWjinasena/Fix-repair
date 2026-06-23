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
        """
        if not self.sale_order_id:
            self._fsm_create_sale_order()
        self._sync_quotation_type()
        return self.sale_order_id

    def _sync_quotation_type(self):
        """Set x_studio_quotation_type on the linked SO based on ticket type.

        Called both when a new SO is created (via _fsm_ensure_sale_order) and
        when an existing SO is linked to the task (write). This ensures the
        type is correct regardless of how the SO was created.
        """
        for task in self:
            if not task.helpdesk_ticket_id or not task.sale_order_id:
                continue
            ticket = task.helpdesk_ticket_id
            qtype = 'Repair' if ticket.x_studio_rug_confirmed else 'Not Under Warranty'
            if task.sale_order_id.x_studio_quotation_type == qtype:
                continue
            if qtype == 'Not Under Warranty':
                self.env['sale.order']._ensure_not_under_warranty_selection()
            task.sale_order_id.sudo().write({'x_studio_quotation_type': qtype})

    def write(self, vals):
        result = super().write(vals)
        if 'sale_order_id' in vals and vals.get('sale_order_id'):
            self._sync_quotation_type()
        return result

    def _fsm_create_sale_order(self):
        """Delegate to industry_fsm_sale's implementation, skipping industry_fsm_stock.

        After the SO is created, immediately bind every existing return
        picking on the linked ticket to it (origin / group_id /
        sale_line_id on moves) so the SO's Delivery smart button counts
        those movements going forward.
        """
        FsmSaleTask._fsm_create_sale_order(self)
        for task in self:
            if task.sale_order_id and task.helpdesk_ticket_id:
                task._bind_ticket_pickings_to_so()

    def _bind_ticket_pickings_to_so(self):
        """Re-point every existing return picking on this task's ticket
        to this task's sale order.

        The default_get of stock.return.picking creates pickings without
        any sale-order link (we don't care about the original sale that
        put the item in the customer's hands). Once the repair SO is
        born on this task, this method:

          1. Ensures a sale.order.line exists on the SO for the ticket's
             product (creates a price=0 placeholder line if missing).
          2. Ensures the SO has a procurement.group.
          3. For every picking linked to the ticket via
             x_studio_helpdesk_ticket_id or the standard picking_ids m2m:
             writes origin = SO.name, group_id = SO.procurement_group_id.
          4. For every move on those pickings whose product matches the
             ticket's product: writes sale_line_id = the placeholder line
             and group_id = SO.procurement_group_id.

        After this, picking.sale_id (computed from move.sale_line_id) will
        resolve to the repair SO and the SO's Delivery smart button picks
        these movements up.
        """
        self.ensure_one()
        ticket = self.helpdesk_ticket_id
        so = self.sale_order_id
        product = ticket.product_id
        if not (so and product):
            return

        # 1. Find or create a placeholder line for the customer's item
        line = so.order_line.filtered(
            lambda l: l.product_id == product and not l.display_type
        )[:1]
        if not line:
            line = self.env['sale.order.line'].sudo().create({
                'order_id': so.id,
                'product_id': product.id,
                'product_uom_qty': 1.0,
                'price_unit': 0.0,
                'name': product.display_name,
            })

        # 2. Ensure the SO has a procurement group
        if not so.procurement_group_id:
            group = self.env['procurement.group'].sudo().create({
                'name': so.name,
                'sale_id': so.id,
                'partner_id': so.partner_id.id,
            })
            so.sudo().write({'procurement_group_id': group.id})
        group = so.procurement_group_id

        # 3 + 4. Find every picking that belongs to this ticket and bind it.
        Picking = self.env['stock.picking'].sudo()
        pickings = (
            Picking.search([('x_studio_helpdesk_ticket_id', '=', ticket.id)])
            | ticket.picking_ids.sudo()
        )
        for picking in pickings:
            vals = {}
            if picking.origin != so.name:
                vals['origin'] = so.name
            if picking.group_id != group:
                vals['group_id'] = group.id
            if not picking.x_studio_helpdesk_ticket_id:
                vals['x_studio_helpdesk_ticket_id'] = ticket.id
            if vals:
                picking.sudo().write(vals)
            for move in picking.move_ids:
                mvals = {}
                if move.product_id == product and move.sale_line_id != line:
                    mvals['sale_line_id'] = line.id
                if move.group_id != group:
                    mvals['group_id'] = group.id
                if mvals:
                    move.sudo().write(mvals)

    def action_fsm_validate(self, stop_running_timers=False):
        """After Mark as Done, advance the linked helpdesk ticket to
        'Repair Completed'. Non-repair FSM tasks have no
        helpdesk_ticket_id and so are unaffected.
        """
        res = super().action_fsm_validate(stop_running_timers=stop_running_timers)
        for task in self:
            ticket = task.helpdesk_ticket_id
            if ticket and task.fsm_done:
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
