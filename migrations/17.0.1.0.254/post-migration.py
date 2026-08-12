# -*- coding: utf-8 -*-
"""v254 upgrade migration — flag each warehouse's Stock location as
x_studio_repair_return_location=True so the RR - Auto Create Repair
Route delegate can resolve its stock.picking.type search.

Clear-DB has this flag pre-set on every branch warehouse's main
Stock location. Codifying here so no manual configuration is
required post-install.

Idempotent — the underlying hook only writes locations whose flag
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
    hooks.seed_repair_return_receipt_locations(env)
