"""v276 upgrade — close the last repair-scope Studio field gaps.

Adds Python declarations for:
  - accounting_company_id on the 6 diagnosis catalogues
    (conditions, diagnosis_areas, diagnosis_codes, symptom_areas,
     symptom_codes, resolutions)
  - active on task_diagnosis
  - 3 project.task fields: payment_type, starting_date,
    task_id_sale_order_count
  - stock.location Studio-generated m2m field many2many_field_7kpUe

On Clear-DB the corresponding state='manual' rows already exist — Odoo's
module loader detects the Python declaration on load and flips the
state to 'base'. No data migration script needed; this file exists
purely to establish the migration folder convention.
"""


def migrate(cr, version):
    if not version:
        return
    # No-op — the field declarations take effect via Odoo's normal
    # module upgrade path (Python declarations override manual state).
    return
