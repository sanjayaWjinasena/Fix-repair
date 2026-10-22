# -*- coding: utf-8 -*-
from odoo import fields, models

GENERAL_STAGE_XMLIDS = (
    'Fix-repair.helpdesk_stage_general_new',
    'Fix-repair.helpdesk_stage_general_in_progress',
    'Fix-repair.helpdesk_stage_general_on_hold',
    'Fix-repair.helpdesk_stage_general_solved',
    'Fix-repair.helpdesk_stage_general_cancelled',
)


class HelpdeskTeam(models.Model):
    _inherit = 'helpdesk.team'

    # Repair tickets and general tickets side by side: tickets of a Repair Team open in the
    # Repair ticket form (Fix-repair fields, rules, buttons); tickets of any other team open in
    # Odoo's standard Helpdesk ticket form.
    x_jin_repair_team = fields.Boolean(
        string='Repair Team',
        help="Tickets of this team use the Repair ticket form (repair fields, required rules and "
             "buttons). Tickets of other teams use Odoo's standard Helpdesk ticket form.")

    # Odoo picks a new team's stages by the helpdesk.stage_* xmlids, which the Repair flow has
    # renamed (Diagnosis, Advance Received, ...). New teams get the general stages instead.
    stage_ids = fields.Many2many(default=lambda self: self._jin_default_stage_ids())

    def _jin_default_stage_ids(self):
        stages = self.env['helpdesk.stage']
        for xmlid in GENERAL_STAGE_XMLIDS:
            stages |= self.env.ref(xmlid, raise_if_not_found=False) or self.env['helpdesk.stage']
        return stages or self.env['helpdesk.stage'].search([], limit=1)

    def action_view_ticket(self):
        # Every team-card button on Helpdesk > Overview (Tickets, open, closed, success rate)
        # and the team form's Tickets button go through this method.
        action = super().action_view_ticket()
        if len(self) == 1 and not self.x_jin_repair_team and action.get('views'):
            form = self.env.ref('helpdesk.helpdesk_ticket_view_form', raise_if_not_found=False)
            if form:
                action['views'] = [(form.id, view_type) if view_type == 'form' else (view_id, view_type)
                                   for view_id, view_type in action['views']]
        return action
