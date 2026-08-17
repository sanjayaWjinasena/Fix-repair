# -*- coding: utf-8 -*-
"""v278 upgrade — bug fix on v277's _fix_repair_auto_generate_quotation_type.

v277's helper searched task.sale_order_id but missed the reverse direction
(sale.order.task_id -> project.task) which is the more common FSM path.
v278 checks the direct link first, then falls back to the search.

Re-runs the (now correct) back-fill on SOs still without a quotation type.
"""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    unset = env['sale.order'].sudo().search([
        ('x_studio_quotation_type', '=', False),
    ])
    if unset:
        unset._fix_repair_auto_generate_quotation_type()
