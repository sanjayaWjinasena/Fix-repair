"""v281 upgrade — bug fix on v280 install failure.

v280's rug_confirmed was declared as
`related='sale_id.rug_confirmed'`. Setup crashed:

  KeyError: 'Field sale_id referenced in related field
  definition account.move.rug_confirmed does not exist.'

sale_id is declared by the studio_migrations module, which
Fix-repair doesn't depend on. Odoo's setup_related() runs at load
time and can't guarantee studio_migrations has loaded its fields
first when Fix-repair loads.

v281 switches the field from `related` to `compute` that walks
invoice_origin -> sale.order (same self-contained pattern as
Fix-repair's existing is_rug_invoice compute). No dependency on
studio_migrations. Store=True preserved so search domains work.

Also softened the write() override to fall back to invoice_origin
lookup when sale_id isn't declared.
"""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Force-recompute the new field on every existing invoice so
    # the stored column is populated correctly.
    moves = env["account.move"].sudo().search([("invoice_origin", "!=", False)])
    if moves:
        moves.invalidate_recordset(["rug_confirmed"])
        moves._compute_rug_confirmed()
