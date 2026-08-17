# -*- coding: utf-8 -*-
"""v283 upgrade -- port Studio automations 202 + 203 + 204 (RR - Track
Lock Status trio) as create/write overrides on sale.order and an
onchange handler on sale.order.line.

Requires BugFix-Sales v44 for the two new line-level marker fields
(x_studio_re_estimated + x_studio_count_1).

Also back-fills existing done-state Repair SOs: any SO that is
currently state='done' + x_studio_quotation_type='Repair' but is not
yet locked gets locked with the correct re_estimate_count derived from
its most recent re-estimated line. Symmetric back-fill for state='sale'
locked-but-not-unlocked SOs is intentionally NOT run -- those may
legitimately be in the process of being re-estimated and touching them
would race the user's own edits.
"""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    Order = env['sale.order'].sudo()
    done_repair = Order.search([
        ('x_studio_quotation_type', '=', 'Repair'),
        ('state', '=', 'done'),
        ('x_studio_locked', '=', False),
    ])
    if done_repair:
        done_repair._fix_repair_apply_track_lock_status()
