"""v17.0.1.0.369: fields that are related on Clear-DB had lost related= in the port and are linked again
(stored). Their columns already existed, and Odoo does not backfill an existing column for a field that
becomes related, so recompute them for existing records. ORM only.
"""

from odoo import SUPERUSER_ID, api

FIELDS = {
    "stock.picking": [
        "type_of_operation",
        "quotation_type",
        "quotation_type_2",
    ],
    "project.task": ["payment_type"],
}


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {"active_test": False})
    for model, names in FIELDS.items():
        if model not in env:
            continue
        records = env[model].search([])
        for name in names:
            if name in records._fields:
                env.add_to_compute(records._fields[name], records)
        records.flush_model([n for n in names if n in records._fields])
