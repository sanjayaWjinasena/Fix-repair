# -*- coding: utf-8 -*-
"""One-shot upgrade cleanup for v236.

post_init_hook only fires on install, never on upgrade. Fix-repair is
already installed on every DB (production Clear-DB + stand-alone dev
envs), so the hook that creates the 4 Studio-ported helpdesk.ticket
view records via convert_file never gets a chance to run when we bump
the version.

This migration re-uses the same load_post_init_view_files entry point
so upgrade paths pick up the view records too. Idempotent: convert_file
in mode='init' updates existing records by external ID and creates
missing ones.
"""
import importlib.util
import os

from odoo import api, SUPERUSER_ID
from odoo.modules.module import get_module_path


def migrate(cr, version):
    if not version:
        # Fresh install path — post_init_hook handles it.
        return

    hooks_path = os.path.join(get_module_path('Fix-repair'), 'hooks.py')
    spec = importlib.util.spec_from_file_location(
        'fix_repair_hooks', hooks_path,
    )
    hooks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hooks)

    env = api.Environment(cr, SUPERUSER_ID, {})
    hooks.load_post_init_view_files(env)
