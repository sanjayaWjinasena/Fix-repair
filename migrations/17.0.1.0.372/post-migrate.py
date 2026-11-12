"""v1.0.372: Repair tickets and general tickets side by side.

Teams are environment data (no xmlid), so the existing repair teams are found by name and
marked as Repair Teams; their tickets keep the Repair ticket form. Any other team is a general
team using Odoo's standard ticket form; the flag can be changed on the team form. ORM only;
no-op when no team has that name.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

REPAIR_TEAM_NAMES = ("Customer Care - Repair",)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    teams = (
        env["helpdesk.team"]
        .with_context(active_test=False)
        .search([("name", "in", REPAIR_TEAM_NAMES)])
    )
    # Field renamed x_jin_repair_team -> repair_team by the Studio rename. The
    # rename runs in this same upgrade (pre-10-fields of .387) and every 'pre'
    # script runs before any 'post' script, so by the time this executes the
    # column already carries the new name.
    teams.filtered(lambda t: not t.repair_team).write({"repair_team": True})
    _logger.info(
        "Fix-repair: %s helpdesk team(s) marked as Repair Team: %s",
        len(teams),
        teams.mapped("display_name"),
    )
