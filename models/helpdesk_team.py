# -*- coding: utf-8 -*-
from odoo import fields, models


class HelpdeskTeam(models.Model):
    _inherit = 'helpdesk.team'

    # Repair tickets and general tickets side by side: tickets of a Repair Team open in the
    # Repair ticket form (Fix-repair fields, rules, buttons); tickets of any other team open in
    # Odoo's standard Helpdesk ticket form.
    x_jin_repair_team = fields.Boolean(
        string='Repair Team',
        help="Tickets of this team use the Repair ticket form (repair fields, required rules and "
             "buttons). Tickets of other teams use Odoo's standard Helpdesk ticket form.")

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
