# -*- coding: utf-8 -*-
"""One-shot upgrade cleanup for v237.

Same load-post-init-view-files call as the v236 migration, needed
again because that one bombed out mid-load on the pre-fix order
(field_hides.xml before ported.xml). This time the order is fixed
and the load completes cleanly.

Idempotent — convert_file in mode='init' updates existing records
by external ID and creates missing ones.
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
    hooks.load_post_init_view_files(env)
