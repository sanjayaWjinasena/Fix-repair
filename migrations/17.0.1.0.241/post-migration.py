# -*- coding: utf-8 -*-
"""v241 post-migration — extends the shared master-data migration
helper to cover the 6 new catalogue models added in Chunk 1a
(x_conditions, x_diagnosis_areas, x_diagnosis_codes, x_symptom_areas,
x_symptom_codes, x_resolutions). Flips their ir.model rows and
ir.model.fields rows from state='manual' -> 'base', drops
studio_customization pins, and creates Fix-repair ownership pins.

On stand-alone (bare Enterprise): the 6 models don't pre-exist via
Studio, so search returns 0 manual rows — no-op. The models get
created fresh by the ORM at module install.

On Clear-DB (production, if ever upgraded): existing rows in the
6 catalogue tables are preserved. Ownership transfers from
studio_customization to Fix-repair. Same pattern as the earlier
5-model repair-master-data cluster.
"""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    if 'x_repair_master_data.migration' in env:
        env['x_repair_master_data.migration']._migrate_studio_repair_master_data_to_base()
