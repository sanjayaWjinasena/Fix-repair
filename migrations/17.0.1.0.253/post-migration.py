# -*- coding: utf-8 -*-
"""v253 upgrade migration — seed the two per-user repair location
fields on every internal user that has them unset.

Without this, `_repair_studio_auto_create_repair_route` (the delegate
behind the new RR - Auto Create Repair Route ir.actions.server) raises
UserError on the first click because it reads
`x_studio_virtual_location` and `x_studio_source_location` on the
current user and both are False on a fresh install.

post_init_hook only fires on install. Existing DBs (v252 → v253 upgrade)
get the seed via this migration.

Idempotent — the underlying hook only writes users whose field is
currently False.
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
    hooks.seed_admin_repair_location_defaults(env)
