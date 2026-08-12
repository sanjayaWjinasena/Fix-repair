# -*- coding: utf-8 -*-
"""v252 upgrade migration — force use_product_returns=True on every
helpdesk.team so the Return button surfaces on repair tickets.

Without this, has_return_picking never becomes True, and Send to
Factory / the rest of the repair pipeline never surfaces. Clear-DB
has this flag on; a bare Enterprise install has it off. Codified
here so no Studio customisation is required.

Idempotent — the underlying hook only writes teams where the flag
is currently False.
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
    hooks.enable_product_returns_on_all_teams(env)
