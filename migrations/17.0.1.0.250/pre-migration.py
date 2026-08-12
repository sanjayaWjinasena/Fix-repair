# -*- coding: utf-8 -*-
"""v250 pre-migration — force-create ir.model.data pins for the 11
Studio-created models Fix-repair owns.

Runs BEFORE any data file loads (Odoo module upgrade order:
pre-migration -> load_data -> post-migration). This is the only phase
that fires early enough to create the pins before security/ir.model.access.csv
tries to resolve them.

v249's data-XML approach (data/ir_model_pins.xml) didn't work on
Clear-DB: when Odoo's data loader processes <record model="ir.model">
for a row whose `model` field value already matches an existing
ir.model row, it silently reuses the existing row but does NOT
create a companion ir.model.data pin. Result: pin still missing,
ACL CSV load still fails.

Raw SQL bypasses the ORM entirely. INSERT ... ON CONFLICT DO NOTHING
means already-pinned rows are left alone. On stand-alone, all pins
already exist from module install; this migration no-ops. On
Clear-DB, missing pins get created and ACL CSV loads successfully.
"""
_MODELS = [
    'x_conditions',
    'x_symptom_areas',
    'x_symptom_codes',
    'x_diagnosis_areas',
    'x_diagnosis_codes',
    'x_resolutions',
    'x_repair_accounts',
    'x_repair_reason',
    'x_repair_reason_custom',
    'x_repair_stages',
    'x_repair_sub_reason',
    'x_task_diagnosis',
]


def migrate(cr, version):
    if not version:
        return

    # For each model name: find its ir_model.id, then ensure an
    # ir.model.data row exists with (module='Fix-repair', name='model_<name>').
    # On Clear-DB, the row exists (created by studio_customization long ago)
    # but the Fix-repair pin doesn't. On stand-alone, the pin exists from
    # module install — the INSERT ... ON CONFLICT skip covers that case.
    for model_name in _MODELS:
        cr.execute("SELECT id FROM ir_model WHERE model = %s", (model_name,))
        row = cr.fetchone()
        if not row:
            # Model doesn't exist yet on this DB (e.g. fresh install path
            # where the model is about to be created by the ORM in the
            # very-next phase). The post-init hook / registry sync will
            # create the pin automatically. Nothing to do here.
            continue
        model_id = row[0]
        xmlid_name = 'model_' + model_name

        cr.execute(
            """
            INSERT INTO ir_model_data
                (module, name, model, res_id, noupdate)
            VALUES
                ('Fix-repair', %s, 'ir.model', %s, TRUE)
            ON CONFLICT (module, name) DO NOTHING
            """,
            (xmlid_name, model_id),
        )
