# -*- coding: utf-8 -*-
"""v1.0.373: general (non-repair) Helpdesk tickets get Odoo-style stages and types.

* Ticket types with a Repair setting (RUG, With / Without Serial No) or named "Repair ..." are
  marked as Repair types; the Repair ticket form offers only those, Odoo's standard form only
  the others (the new Question / Issue).
* Teams that are not a Repair Team switch to the general stages (New, In Progress, On Hold,
  Solved, Cancelled). Their tickets move to the matching general stage: by Odoo's stage xmlid
  (Repair renamed those records), otherwise by folded / not folded.
ORM only; Repair teams and their tickets are not touched.
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

STAGE_MAP = {  # Odoo stage xmlid -> general stage xmlid
    'helpdesk.stage_new': 'Fix-repair.helpdesk_stage_general_new',
    'helpdesk.stage_in_progress': 'Fix-repair.helpdesk_stage_general_in_progress',
    'helpdesk.stage_on_hold': 'Fix-repair.helpdesk_stage_general_on_hold',
    'helpdesk.stage_solved': 'Fix-repair.helpdesk_stage_general_solved',
    'helpdesk.stage_cancelled': 'Fix-repair.helpdesk_stage_general_cancelled',
}


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    Type = env['helpdesk.ticket.type'].with_context(active_test=False)
    repair_types = Type.search(['|', '|', '|', ('x_studio_rug', '=', True), ('x_studio_with_serial_no', '=', True),
                                ('x_studio_without_serial_no', '=', True), ('name', '=ilike', 'repair%')])
    repair_types.filtered(lambda t: not t.x_jin_repair_type).write({'x_jin_repair_type': True})
    _logger.info('Fix-repair: %s ticket types marked as Repair types', len(repair_types))

    general = env['helpdesk.team']._jin_default_stage_ids()
    by_old_stage = {}
    for old_xmlid, new_xmlid in STAGE_MAP.items():
        old = env.ref(old_xmlid, raise_if_not_found=False)
        new = env.ref(new_xmlid, raise_if_not_found=False)
        if old and new:
            by_old_stage[old.id] = new
    new_open = env.ref('Fix-repair.helpdesk_stage_general_new', raise_if_not_found=False)
    new_folded = env.ref('Fix-repair.helpdesk_stage_general_solved', raise_if_not_found=False)
    teams = env['helpdesk.team'].with_context(active_test=False).search([('x_jin_repair_team', '=', False)])
    for team in teams:
        tickets = env['helpdesk.ticket'].with_context(active_test=False).search(
            [('team_id', '=', team.id), ('stage_id', 'not in', general.ids)])
        for stage in tickets.stage_id:
            target = by_old_stage.get(stage.id) or (new_folded if stage.fold else new_open)
            tickets.filtered(lambda t, s=stage: t.stage_id == s).write({'stage_id': target.id})
        team.write({'stage_ids': [(6, 0, general.ids)]})
        _logger.info('Fix-repair: team %s uses the general stages (%s tickets moved)', team.display_name, len(tickets))
