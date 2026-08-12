# -*- coding: utf-8 -*-
"""Minimal Python declaration of the Studio-created x_task_diagnosis
catalogue model.

Why this file exists
--------------------
project.task.x_studio_diagnosis_ids is a One2many onto x_task_diagnosis
via its x_studio_task_id inverse. On the Jinasena production DB both
were provisioned by Studio (state='manual'); on a stand-alone Odoo
install neither is present and Fix-repair's setup_nonrelated crashes:

    KeyError: 'x_studio_task_id'
    File "odoo/fields.py", line 4458, in setup_nonrelated
        invf = comodel._fields[self.inverse_name]

Declaring the model and the inverse field here gives every DB a real
model at Python setup time. On production the state=manual Studio row
gets upgraded to state=base and Fix-repair takes ownership — same
pattern as the v30-v33 sale.order / res.partner ports. Existing rows
in the x_task_diagnosis table are preserved because the table name
and the x_studio_task_id column name are unchanged.

v259 extension
--------------
The Repair Diagnosis notebook tab on project.task renders this model
as an editable one2many with 9 catalogue m2o dropdowns plus a
description and sequence. Those fields were left as Studio-manual
on Clear-DB until this chunk. Ported verbatim (types + relations)
from Clear-DB ir.model.fields (state='manual', modules=
'studio_customization') so Fix-repair now owns them state='base'
on both environments.
"""
from odoo import fields, models


class XTaskDiagnosis(models.Model):
    _name = 'x_task_diagnosis'
    _description = 'Task Diagnosis'
    _order = 'x_studio_sequence, id'

    # Odoo requires a _rec_name field. Studio uses x_name by convention
    # on all custom models; declared here so search-by-name UI still
    # works and the model doesn't fall back to id-only display_name.
    x_name = fields.Char(string='Name', required=True)

    # The back-reference project.task.x_studio_diagnosis_ids traverses
    # into on load-time setup_nonrelated. Must exist as a real Python
    # field for Fix-repair to install cleanly.
    x_studio_task_id = fields.Many2one(
        'project.task',
        string='Task',
        ondelete='cascade',
        index=True,
    )

    # v259: catalogue m2os matching Clear-DB schema. All targets are
    # already Python-declared (Chunk 1a v241 for the 6 diagnosis
    # catalogues, v227 for the 3 repair-master ones).
    x_studio_sequence = fields.Integer(string='Sequence', default=10)
    x_studio_description = fields.Char(string='Description')
    x_studio_condition = fields.Many2one(
        'x_conditions', string='Condition', ondelete='set null',
    )
    x_studio_symptom_area = fields.Many2one(
        'x_symptom_areas', string='Symptom Area', ondelete='set null',
    )
    x_studio_symptom_code = fields.Many2one(
        'x_symptom_codes', string='Symptom Code', ondelete='set null',
    )
    x_studio_diagnosis_area = fields.Many2one(
        'x_diagnosis_areas', string='Diagnosis Area', ondelete='set null',
    )
    x_studio_diagnosis_code = fields.Many2one(
        'x_diagnosis_codes', string='Diagnosis Code', ondelete='set null',
    )
    x_studio_reason = fields.Many2one(
        'x_repair_reason', string='Reason', ondelete='set null',
    )
    x_studio_sub_reason = fields.Many2one(
        'x_repair_sub_reason', string='Sub Reason', ondelete='set null',
    )
    x_studio_resolution = fields.Many2one(
        'x_resolutions', string='Resolution', ondelete='set null',
    )
    x_studio_repair_stage = fields.Many2one(
        'x_repair_stages', string='Repair Stage', ondelete='set null',
    )
