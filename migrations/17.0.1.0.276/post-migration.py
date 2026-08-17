# -*- coding: utf-8 -*-
"""v276 upgrade — close the last repair-scope Studio field gaps.

Adds Python declarations for:
  - x_studio_company_id on the 6 diagnosis catalogues
    (x_conditions, x_diagnosis_areas, x_diagnosis_codes, x_symptom_areas,
     x_symptom_codes, x_resolutions)
  - x_active on x_task_diagnosis
  - 3 project.task fields: x_studio_payment_type, x_studio_starting_date,
    x_task_id_sale_order_count
  - stock.location Studio-generated m2m field x_studio_many2many_field_7kpUe

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
