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

Fields on x_task_diagnosis beyond x_studio_task_id (diagnosis codes,
areas, notes, etc.) are left as Studio-manual for now — they only
matter on production DBs where Studio provisioned them, and any
stand-alone install has no rows in this catalogue at all so those
fields are inert. A later port can pull them in.
"""
from odoo import fields, models


class XTaskDiagnosis(models.Model):
    _name = 'x_task_diagnosis'
    _description = 'Task Diagnosis'

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
