# -*- coding: utf-8 -*-
"""v272 upgrade migration — activate any dormant internal
stock.picking.type records so the repair-flow _create_repair_transfer
helper stops silently no-op'ing (only the initial Return was
producing a picking; Send-to-Factory / Received-at-Factory /
Send-to-Sales-Centre / Received-at-Sales-Centre were failing at
the picking-type search step because Odoo's ORM auto-filters
active=True).
"""
import importlib.util
import os

from odoo import api, SUPERUSER_ID
from odoo.modules.module import get_module_path


def migrate(cr, version):
    if not version:
        return
    hooks_path = os.path.join(get_module_path('Fix-repair'), 'hooks.py')
    spec = importlib.util.spec_from_file_location(
        'fix_repair_hooks', hooks_path,
    )
    hooks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hooks)
    env = api.Environment(cr, SUPERUSER_ID, {})
    hooks.activate_internal_picking_types(env)
