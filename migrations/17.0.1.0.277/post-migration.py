# -*- coding: utf-8 -*-
"""v277 upgrade — port Studio automation 176 'RR - Auto Generate
Quotation Type for Repair SOs' as sale.order create/write override.

Also back-fills x_studio_quotation_type='Repair' on any existing SO
that IS FSM-task-linked to a repair helpdesk ticket (or a repair
project once Group C ships) but doesn't have the flag set — matches
what the Studio automation would have done historically.
"""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Back-fill on existing SOs whose flag is empty.
    unset = env['sale.order'].sudo().search([
        ('x_studio_quotation_type', '=', False),
    ])
    if unset:
        unset._fix_repair_auto_generate_quotation_type()
