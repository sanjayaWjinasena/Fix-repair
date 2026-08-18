# -*- coding: utf-8 -*-
"""v287 upgrade -- fix account.move.x_studio_rug_confirmed compute
reactivity to sale.order side flips.

The v281 stored compute on account.move only depends on
`invoice_origin` + `move_type`. It walks invoice_origin (Char) to a
sale.order by name match, but Odoo's ORM can't trace that string-
based reverse lookup as a dependency. Result: flipping
x_studio_rug_confirmed on the SO does not invalidate the invoice's
cached value.

v287 adds a sale.order.write() override in Fix-repair that, when the
flag flips, calls _compute_x_studio_rug_confirmed on any invoice with
matching invoice_origin. This migration back-fills every existing
out_invoice with an invoice_origin so the cached values are
in sync with current SO state on install.

E2E test that exposed this on dev env: SO 81 flipped rug_confirmed
to True after invoice FTI/2026/00001 was posted; invoice's
x_studio_rug_confirmed stayed False (had been captured False at
create time). Junk-then-restore of invoice_origin was the temporary
workaround.
"""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    moves = env['account.move'].sudo().search([
        ('invoice_origin', '!=', False),
        ('move_type', '=', 'out_invoice'),
    ])
    if moves:
        moves._compute_x_studio_rug_confirmed()
