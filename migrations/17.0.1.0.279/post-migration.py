# -*- coding: utf-8 -*-
"""v279 upgrade — port Studio automation 193 'RR - Sales Price For
RUG Items' as a sale.order.line create/write override on Fix-repair.

Also back-fills existing lines: for any sale.order.line whose parent
SO is Repair AND rug_confirmed, reprice to product cost. Skip lines
whose price already matches (idempotent) and any line where
product_template_id is falsy.

Requires BugFix-Sales v43 for x_studio_price_unit_original on
sale.order.line.
"""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    Line = env['sale.order.line'].sudo()
    candidates = Line.search([
        ('order_id.x_studio_quotation_type', '=', 'Repair'),
        ('order_id.x_studio_rug_confirmed', '=', True),
    ])
    if candidates:
        candidates._fix_repair_maybe_reprice_rug_line()
