# -*- coding: utf-8 -*-
"""v1.0.377: repair numbering sequences ship with the module (models/res_company.py).

Create 'repair.seq' and 'repair.serial.seq' for every company that has none. Existing sequences
(and their counters) are left alone. ORM only.
"""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['res.company']._jin_ensure_repair_sequences()
