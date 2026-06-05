# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    repair_stage_state = fields.Selection([
        ('new',                      'New'),
        ('sent_to_factory',          'Sent to Factory'),
        ('received_at_factory',      'Received at Factory'),
        ('repair_completed',         'Repair Completed'),
        ('sent_to_sales_centre',     'Sent to Sales Centre'),
        ('received_at_sales_centre', 'Received at Sales Centre'),
        ('other',                    'Other'),
    ], compute='_compute_repair_stage_state', store=True)

    # Override the Studio-defined x_studio_handed_over compute to:
    #   1. Remove the stage-write side effect (caused timeouts on list views)
    #   2. Remove the user-context company bug (was using allowed_company_ids[0]
    #      instead of rec.company_id, moving company-2 tickets to stage 13)
    # Stage transitions are now handled entirely by stock_picking._action_done.
    x_studio_handed_over = fields.Boolean(
        compute='_compute_x_studio_handed_over',
        store=False,
    )

    # True once the technician clicks Mark as Done on the linked FSM task.
    # Used to gate the Send to Sales Centre button.
    task_done = fields.Boolean(compute='_compute_task_done')

    @api.depends('stage_id')
    def _compute_repair_stage_state(self):
        mapping = {
            'New':                      'new',
            'Sent to Factory':          'sent_to_factory',
            'Received at Factory':      'received_at_factory',
            'Repair Completed':         'repair_completed',
            'Sent to Sales Centre':     'sent_to_sales_centre',
            'Received at Sales Centre': 'received_at_sales_centre',
        }
        for ticket in self:
            # sudo() so users without perm_read on helpdesk.stage can still
            # read the stage name (the stored value is set here, not exposed raw)
            name = (ticket.sudo().stage_id.name or '').strip()
            ticket.repair_stage_state = mapping.get(name, 'other')

    @api.depends('picking_ids')
    def _compute_x_studio_handed_over(self):
        for rec in self:
            rec.x_studio_handed_over = sum(
                1 for p in rec.picking_ids if p.state == 'done'
            ) > 1

    def _compute_task_done(self):
        for ticket in self:
            ticket.task_done = self.env['project.task'].sudo().search_count([
                ('helpdesk_ticket_id', '=', ticket.id),
                ('is_fsm', '=', True),
                ('fsm_done', '=', True),
            ]) > 0

    @api.onchange('x_studio_serial_no')
    def _onchange_serial_no_product(self):
        if self.x_studio_serial_no and self.x_studio_serial_no.product_id:
            self.product_id = self.x_studio_serial_no.product_id
        elif not self.x_studio_serial_no:
            self.product_id = False

    @api.model
    def _deactivate_clearing_serial_automation(self):
        """Deactivate the Studio automation that unconditionally clears product_id,
        lot_id, etc. whenever x_studio_serial_no changes — it overwrites our
        onchange and prevents the product from auto-populating from the serial.
        The clearing logic is now handled by _onchange_serial_no_product instead.
        """
        automation = self.env['base.automation'].sudo().search([
            ('name', '=', 'RR - Auto Select Product for RUG Repairs-33'),
            ('model_id.model', '=', 'helpdesk.ticket'),
        ], limit=1)
        if automation and automation.active:
            automation.write({'active': False})

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            # Restrict stage selection to the ticket's own company
            for field in arch.xpath("//field[@name='stage_id']"):
                field.set('domain',
                    "[('team_ids', 'in', [team_id]), "
                    "'|', ('x_studio_company_id', '=', company_id), "
                    "('x_studio_company_id', '=', False)]"
                )

            # Plan Intervention: show at Received at Factory with no task yet.
            # Warranty (RUG) repairs also require a valid return picking to confirm
            # the item is physically at the factory; non-warranty customers bring
            # the item in directly so no return picking exists.
            for btn in arch.xpath("//button[@name='action_generate_fsm_task']"):
                btn.set('invisible',
                    "not use_fsm or "
                    "fsm_task_count > 0 or "
                    "repair_stage_state != 'received_at_factory' or "
                    "(x_studio_rug_repair and not x_studio_valid_return)"
                )
            # Return button — same action 195, two distinct popup behaviours:
            #   New stage:                 default_ticket_id=id → wizard shows Sale Order
            #                              group so user selects which delivery to reverse
            #   Received at Sales Centre:  default_picking_id=x_studio_pick_id, no ticket_id
            #                              → Sale Order group hidden, items pre-load from
            #                              the picking; return location defaults to Customers
            cust_loc = self.env.ref('stock.stock_location_customers', raise_if_not_found=False)
            cust_loc_id = cust_loc.id if cust_loc else 5
            for btn in arch.xpath("//button[@name='195']"):
                btn.set('invisible', "False")
                btn.set('context',
                    # ticket_id: only for RUG at New stage (no pick_id yet) — shows SO picker
                    # picking_id: non-warranty New (outgoing delivery) + Received at Sales Centre
                    #             (incoming return picking); automation 172 stores both in x_studio_pick_id
                    # partner_id: passed so stock_return_picking._get_view can filter SOs by customer
                    "{'default_ticket_id': (repair_stage_state == 'new' and not x_studio_pick_id and id) or False, "
                    "'default_picking_id': x_studio_pick_id or False, "
                    "'default_partner_id': partner_id, "
                    f"'default_location_id': (repair_stage_state == 'received_at_sales_centre' and {cust_loc_id}) or False, "
                    "'default_company_id': company_id}"
                )

            # Serial Number: only show lots already issued via a sale order.
            # sale_order_ids is non-stored so domain filters on it are ignored.
            # is_issued is a virtual field with a _search that queries move lines.
            serial_domain = "[('is_issued', '=', True)]"
            serial_options = "{'no_create': True, 'no_quick_create': True}"
            for field in arch.xpath("//field[@name='x_studio_serial_no']"):
                field.set('domain', serial_domain)
                field.set('options', serial_options)
            for field in arch.xpath("//field[@name='lot_id']"):
                field.set('domain', serial_domain)
                field.set('options', serial_options)
        return arch, view

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _get_or_create_stage(self, name, sequence):
        """Find the stage by name scoped to this ticket's team and company."""
        self.ensure_one()
        stage = self.env['helpdesk.stage'].sudo().search([
            ('name', '=', name),
            ('team_ids', 'in', self.team_id.ids),
            '|',
            ('x_studio_company_id', '=', self.company_id.id),
            ('x_studio_company_id', '=', False),
        ], limit=1)
        if not stage:
            stage = self.env['helpdesk.stage'].sudo().create({'name': name, 'sequence': sequence})
        return stage

    def _move_to_stage(self, stage_name):
        """Move each ticket to the named stage, scoped to the ticket's company and team."""
        for ticket in self:
            stage = self.env['helpdesk.stage'].sudo().search([
                ('name', '=', stage_name),
                ('team_ids', 'in', ticket.team_id.ids),
                '|',
                ('x_studio_company_id', '=', ticket.company_id.id),
                ('x_studio_company_id', '=', False),
            ], limit=1)
            if stage:
                ticket.sudo().write({'stage_id': stage.id})

    # ── Button actions ───────────────────────────────────────────────────────

    def action_assign_to_me(self):
        self.write({'user_id': self.env.uid})

    def action_send_to_factory(self):
        stage = self._get_or_create_stage('Sent to Factory', 20)
        self.write({
            'stage_id': stage.id,
            'x_studio_s_shipped_date': fields.Datetime.now(),
            'x_studio_s_shipped_by': self.env.uid,
        })

    def action_received_at_factory(self):
        stage = self._get_or_create_stage('Received at Factory', 30)
        self.write({
            'stage_id': stage.id,
            'x_studio_f_received_date': fields.Datetime.now(),
            'x_studio_f_received_by': self.env.uid,
        })

    def action_send_to_sales_centre(self):
        stage = self._get_or_create_stage('Sent to Sales Centre', 100)
        self.write({
            'stage_id': stage.id,
            'x_studio_f_shipped_date': fields.Datetime.now(),
            'x_studio_f_shipped_by': self.env.uid,
        })

    def action_received_at_sales_centre(self):
        stage = self._get_or_create_stage('Received at Sales Centre', 110)
        for ticket in self:
            # Find the most-recent done incoming picking that collected this
            # customer's item to the repair virtual location.  Stored so the
            # "Return to Customer" popup (action 195 at this stage) can
            # pre-load the picking via default_picking_id.
            repair_loc = ticket.x_studio_virtual_location_1 or ticket.x_studio_virtual_location
            domain = [
                ('partner_id', '=', ticket.partner_id.id),
                ('company_id', '=', ticket.company_id.id),
                ('state', '=', 'done'),
                ('picking_type_code', '=', 'incoming'),
            ]
            if repair_loc:
                domain.append(('location_dest_id', '=', repair_loc.id))
            pick = self.env['stock.picking'].sudo().search(
                domain, order='date_done desc', limit=1
            )
            ticket.write({
                'stage_id': stage.id,
                'x_studio_s_received_date': fields.Datetime.now(),
                'x_studio_s_received_by': self.env.uid,
                'x_studio_pick_id': pick.id if pick else 0,
            })
