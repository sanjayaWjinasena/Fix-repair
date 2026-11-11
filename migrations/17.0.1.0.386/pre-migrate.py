"""v1.0.386 (pre): Repair ticket form for databases installed from the rename trial.

Databases installed from Rename-HelpdeskRepair before the general-tickets changes are past
v1.0.372, so its pre-migrate (move the ticket form customizations onto the Repair form in one
step) never ran there. Same step, only where the form customizations still extend Odoo's
standard ticket form; no-op everywhere else. ORM only.
"""

import importlib.util
import logging
import os

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def _v372(name):
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "17.0.1.0.372", name)
    spec = importlib.util.spec_from_file_location("fix_repair_v372_" + name[:-3].replace("-", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    view = env.ref("Fix-repair.ported_view_helpdesk_ticket_form_4012", raise_if_not_found=False)
    standard = env.ref("helpdesk.helpdesk_ticket_view_form", raise_if_not_found=False)
    if view and standard and view.inherit_id == standard:
        _logger.info("Fix-repair: ticket form customizations still on the standard form, moving them")
        _v372("pre-migrate.py").migrate(cr, version)
