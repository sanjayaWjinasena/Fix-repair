# -*- coding: utf-8 -*-
"""One-shot upgrade cleanup for v225.

post_init_hook only fires on install, never on upgrade. The 12
res.partner x_studio_* fields ported here are already installed on
every live DB, so the studio_customization xmlid cleanup needs to run
at upgrade time too. This migration script calls the same hook
function — idempotent, safe to leave in place.
"""
import importlib.util
import os

from odoo import api, SUPERUSER_ID
from odoo.modules.module import get_module_path


def migrate(cr, version):
    if not version:
        # Fresh install path — post_init_hook handles it.
        return

    # Dynamic-load hooks.py: the module name 'Fix-repair' has a dash,
    # which breaks `from odoo.addons.Fix-repair.hooks import ...`.
    hooks_path = os.path.join(get_module_path('Fix-repair'), 'hooks.py')
    spec = importlib.util.spec_from_file_location(
        'fix_repair_hooks', hooks_path,
    )
    hooks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hooks)

    env = api.Environment(cr, SUPERUSER_ID, {})
    hooks.strip_studio_xmlids_for_ported_fields(env)
