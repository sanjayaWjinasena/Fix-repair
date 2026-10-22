# -*- coding: utf-8 -*-
"""v1.0.372: Repair tickets and general tickets side by side.

Teams are environment data (no xmlid), so the existing repair teams are found by name and
marked as Repair Teams; their tickets keep the Repair ticket form. Any other team is a general
team using Odoo's standard ticket form; the flag can be changed on the team form. ORM only;
no-op when no team has that name.
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

REPAIR_TEAM_NAMES = ('Customer Care - Repair',)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    teams = env['helpdesk.team'].with_context(active_test=False).search([('name', 'in', REPAIR_TEAM_NAMES)])
    teams.filtered(lambda t: not t.x_jin_repair_team).write({'x_jin_repair_team': True})
    _logger.info('Fix-repair: %s helpdesk team(s) marked as Repair Team: %s', len(teams), teams.mapped('display_name'))
