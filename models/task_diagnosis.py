"""Minimal Python declaration of the Studio-created task_diagnosis
catalogue model.

Why this file exists
--------------------
project.task.diagnosis_ids is a One2many onto task_diagnosis
via its task_id inverse. On the Jinasena production DB both
were provisioned by Studio (state='manual'); on a stand-alone Odoo
install neither is present and Fix-repair's setup_nonrelated crashes:

    KeyError: 'task_id'
    File "odoo/fields.py", line 4458, in setup_nonrelated
        invf = comodel._fields[self.inverse_name]

Declaring the model and the inverse field here gives every DB a real
model at Python setup time. On production the state=manual Studio row
gets upgraded to state=base and Fix-repair takes ownership — same
pattern as the v30-v33 sale.order / res.partner ports. Existing rows
in the task_diagnosis table are preserved because the table name
and the task_id column name are unchanged.

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
    _name = "task_diagnosis"
    _rec_name = "name"  # Clear-DB Studio model: records are named by name
    _description = "Task Diagnosis"
    # v304: mail.thread + mail.activity.mixin match the sister
    # repair-diagnosis catalog models in repair_master_data.py
    # (conditions / diagnosis_codes / etc.) and match Clear-DB
    # verbatim. Without these mixins the Studio-generated form arch
    # (ported in v299 as repair_diagnosis_catalog_views.xml) fails
    # view validation with "Field 'message_follower_ids' does not
    # exist in model 'task_diagnosis'".
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, id"

    # Odoo requires a _rec_name field. Studio uses name by convention
    # on all custom models; declared here so search-by-name UI still
    # works and the model doesn't fall back to id-only display_name.
    # v262: Clear-DB has name required=False and all 586 existing
    # diagnosis rows carry name=False (empty). Match verbatim so the
    # tree-editable Repair Diagnosis tab can save rows without the UI
    # exposing an name input (Studio hides it via column_invisible).
    name = fields.Char()

    # v276: standard Odoo active pattern — mirrors Clear-DB's Studio
    # active. Diagnosis rows can be soft-deleted from catalogues
    # without cascading through project.task history.
    active = fields.Boolean(default=True)

    # The back-reference project.task.diagnosis_ids traverses
    # into on load-time setup_nonrelated. Must exist as a real Python
    # field for Fix-repair to install cleanly.
    task_id = fields.Many2one(
        "project.task",
        ondelete="set null",
        index=True,
    )

    # v259: catalogue m2os matching Clear-DB schema. All targets are
    # already Python-declared (Chunk 1a v241 for the 6 diagnosis
    # catalogues, v227 for the 3 repair-master ones).
    sequence = fields.Integer(default=10)
    description = fields.Char()
    condition = fields.Many2one(
        "conditions",
        ondelete="set null",
    )
    symptom_area = fields.Many2one(
        "symptom_areas",
        ondelete="set null",
    )
    symptom_code = fields.Many2one(
        "symptom_codes",
        ondelete="set null",
    )
    diagnosis_area = fields.Many2one(
        "diagnosis_areas",
        ondelete="set null",
    )
    diagnosis_code = fields.Many2one(
        "diagnosis_codes",
        ondelete="set null",
    )
    reason = fields.Many2one(
        "repair_reason",
        ondelete="set null",
    )
    sub_reason = fields.Many2one(
        "repair_sub_reason",
        ondelete="set null",
    )
    resolution = fields.Many2one(
        "resolutions",
        ondelete="set null",
    )
    repair_stage = fields.Many2one(
        "repair_stages",
        ondelete="set null",
    )


class XTaskDiagnosisGap(models.Model):
    _inherit = "task_diagnosis"
    _rec_name = "name"  # Clear-DB Studio model: records are named by name

    active = fields.Boolean()
    name = fields.Char()
