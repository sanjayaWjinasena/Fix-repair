# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            # Plan Intervention: only at Received at Factory with a valid return and no task yet
            for btn in arch.xpath("//button[@name='action_generate_fsm_task']"):
                btn.set('invisible',
                    "not use_fsm or "
                    "fsm_task_count > 0 or "
                    "stage_id.name != 'Received at Factory' or "
                    "not x_studio_valid_return"
                )
            # Return: hide once a return already exists
            for btn in arch.xpath("//button[@name='195']"):
                btn.set('invisible', "x_studio_valid_return == True")
        return arch, view

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
        self.write({
            'stage_id': stage.id,
            'x_studio_s_received_date': fields.Datetime.now(),
            'x_studio_s_received_by': self.env.uid,
        })
