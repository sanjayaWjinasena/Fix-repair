# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    # Computed field so the view can show/hide stage buttons cleanly
    repair_stage_state = fields.Selection([
        ('new',                 'New'),
        ('sent_to_factory',     'Sent to Factory'),
        ('received_at_factory', 'Received at Factory'),
        ('other',               'Other'),
    ], compute='_compute_repair_stage_state')

    @api.depends('stage_id.name')
    def _compute_repair_stage_state(self):
        for ticket in self:
            name = (ticket.stage_id.name or '').strip()
            if name == 'New':
                ticket.repair_stage_state = 'new'
            elif name == 'Sent to Factory':
                ticket.repair_stage_state = 'sent_to_factory'
            elif name == 'Received at Factory':
                ticket.repair_stage_state = 'received_at_factory'
            else:
                ticket.repair_stage_state = 'other'

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _get_or_create_stage(self, name, sequence):
        """Return the stage with the given name, creating it if missing."""
        stage = self.env['helpdesk.stage'].search(
            [('name', '=', name)], limit=1
        )
        if not stage:
            stage = self.env['helpdesk.stage'].create({
                'name': name,
                'sequence': sequence,
            })
        return stage

    # ── Button actions ───────────────────────────────────────────────────────

    def action_assign_to_me(self):
        self.write({'user_id': self.env.uid})

    def action_send_to_factory(self):
        stage = self._get_or_create_stage('Sent to Factory', 10)
        self.write({
            'stage_id': stage.id,
            'x_studio_s_shipped_data': fields.Date.today(),
            'x_studio_s_shipped_by': self.env.uid,
        })

    def action_received_at_factory(self):
        stage = self._get_or_create_stage('Received at Factory', 20)
        self.write({
            'stage_id': stage.id,
            'x_studio_f_recieved_data': fields.Date.today(),
            'x_studio_f_recieved_by': self.env.uid,
        })
