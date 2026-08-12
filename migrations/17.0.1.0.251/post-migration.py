# -*- coding: utf-8 -*-
"""v251 upgrade migration — seed admin user into default WH stock
locations for the Return Receipt Location dropdown.

post_init_hook only fires on fresh install. Existing DBs (already at
Fix-repair v250 with the stock.location x_studio_users_stock_location
field declared but empty) get the seed via this migration.

Idempotent — the underlying hook checks membership before writing,
so re-runs are no-ops.
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
    hooks.seed_default_stock_location_users(env)
