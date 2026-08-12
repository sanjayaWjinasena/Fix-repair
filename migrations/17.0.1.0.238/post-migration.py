# -*- coding: utf-8 -*-
"""Upgrade path for v238 — re-runs load_post_init_view_files with
the new sentinel guard so previously-failed loads get a clean skip
on DBs where Studio's hardcoded action IDs don't exist."""
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
