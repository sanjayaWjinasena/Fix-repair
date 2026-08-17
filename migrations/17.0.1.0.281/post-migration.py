# -*- coding: utf-8 -*-
"""v281 upgrade — bug fix on v280 install failure.

v280's x_studio_rug_confirmed was declared as
`related='x_studio_sale_id.x_studio_rug_confirmed'`. Setup crashed:

  KeyError: 'Field x_studio_sale_id referenced in related field
  definition account.move.x_studio_rug_confirmed does not exist.'

x_studio_sale_id is declared by the studio_migrations module, which
Fix-repair doesn't depend on. Odoo's setup_related() runs at load
time and can't guarantee studio_migrations has loaded its fields
first when Fix-repair loads.

v281 switches the field from `related` to `compute` that walks
invoice_origin -> sale.order (same self-contained pattern as
Fix-repair's existing is_rug_invoice compute). No dependency on
studio_migrations. Store=True preserved so search domains work.

Also softened the write() override to fall back to invoice_origin
lookup when x_studio_sale_id isn't declared.
"""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Force-recompute the new field on every existing invoice so
    # the stored column is populated correctly.
    moves = env['account.move'].sudo().search([('invoice_origin', '!=', False)])
    if moves:
        moves.invalidate_recordset(['x_studio_rug_confirmed'])
        moves._compute_x_studio_rug_confirmed()
