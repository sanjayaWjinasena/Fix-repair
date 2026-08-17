# -*- coding: utf-8 -*-
"""v285 upgrade -- Odoo-17 fix for the Track Lock Status port from v283.

Studio automations 202 + 203 both used `state == 'done'` as their gate.
Odoo 17 removed the `done` state from sale.order (states are now
draft / sent / sale / cancel) so the guard has never matched in
production since the v17 upgrade. Effectively legacy dead code both
on Clear-DB and the dev env.

v285 rewrites the port to watch the native `locked` Boolean instead
(Odoo 17's replacement for the old done-state lock mechanism).
Semantics match the original intent:

  * locked=True  -> mirror x_studio_locked=True + x_studio_unlocked=False
                    + stamp re_estimate_count from most recent re-line
  * locked=False + Studio-locked still True -> mirror x_studio_locked=False
                                               + x_studio_unlocked=True

Back-fills every already-locked Repair SO on dev env so its Studio
lock fields align with the native locked field.

Clear-DB reference is left unchanged (bug on Clear-DB, fixed only in
Fix-repair's port).
"""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    Order = env['sale.order'].sudo()
    # Back-fill locked=True Repair SOs to also carry x_studio_locked=True.
    locked = Order.search([
        ('x_studio_quotation_type', '=', 'Repair'),
        ('locked', '=', True),
        ('x_studio_locked', '=', False),
    ])
    if locked:
        locked._fix_repair_apply_track_lock_status()
    # Symmetric back-fill for legacy stuck x_studio_locked=True on
    # native-unlocked SOs -- intentionally NOT run. Leave any existing
    # Studio-side stamps as-is so a manual audit can spot them.
