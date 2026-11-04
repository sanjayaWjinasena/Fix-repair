from odoo import api, fields, models


class XRepairAccounts(models.Model):
    """Per-company RUG account mapping. Read by Fix-repair's
    account_move.py to find the RUG receivable account for a
    warranty-repair invoice. 2 rows on staging today (one per
    company).
    """

    _name = "repair_accounts"
    _description = "Repair Accounts"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "name"
    _order = "sequence, id"

    active = fields.Boolean(string="Active", default=True)
    name = fields.Char(string="Name")
    accounting_company_id = fields.Many2one("res.company", string="Company")
    rug_account = fields.Many2one("account.account", string="RUG Account")
    sequence = fields.Integer(string="Sequence")

    def _jin_set_company_id(self):
        """Studio server action id 2790 native port."""
        for record in self:
            company_id = self.env.context.get(
                "allowed_company_ids", [self.env.user.company_id.id]
            )[0]
            record.accounting_company_id = company_id

    @api.model_create_multi
    def create(self, vals_list):
        """Replaces automation 331 'JIN - Company Id in Repair Accounts'."""
        records = super().create(vals_list)
        records._jin_set_company_id()
        return records


class XRepairReason(models.Model):
    """Master catalogue of repair reasons. Referenced by
    project.task's repair_reason M2M and by
    repair_sub_reason's reason_code M2o.
    """

    _name = "repair_reason"
    _description = "Repair Reason"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "name"
    _order = "sequence, id"

    active = fields.Boolean(string="Active", default=True)
    color = fields.Integer(string="Color")
    name = fields.Char(string="Repair Reason")
    accounting_company_id = fields.Many2one("res.company", string="Company")
    sequence = fields.Integer(string="Sequence")

    def _jin_set_company_id(self):
        """Studio server action id 2666 native port."""
        for record in self:
            company_id = self.env.context.get(
                "allowed_company_ids", [self.env.user.company_id.id]
            )[0]
            record.accounting_company_id = company_id

    @api.model_create_multi
    def create(self, vals_list):
        """Replaces automation 302 'JIN - Company Id in Repair Reason'."""
        records = super().create(vals_list)
        records._jin_set_company_id()
        return records


class XRepairReasonCustom(models.Model):
    """Customer-facing repair reason catalogue. Referenced by
    helpdesk.ticket's repair_reason M2M. Parallel to
    repair_reason but presented to end customers.
    """

    _name = "repair_reason_custom"
    _description = "Repair Reason - Customer"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "name"
    _order = "sequence, id"

    active = fields.Boolean(string="Active", default=True)
    color = fields.Integer(string="Color")
    name = fields.Char(string="Repair Reason")
    accounting_company_id = fields.Many2one("res.company", string="Company")
    sequence = fields.Integer(string="Sequence")

    def _jin_set_company_id(self):
        """Studio server action id 2667 native port."""
        for record in self:
            company_id = self.env.context.get(
                "allowed_company_ids", [self.env.user.company_id.id]
            )[0]
            record.accounting_company_id = company_id

    @api.model_create_multi
    def create(self, vals_list):
        """Replaces automation 303 'JIN - Company Id in Repair Reason - Customer'."""
        records = super().create(vals_list)
        records._jin_set_company_id()
        return records


class XRepairStages(models.Model):
    """Alternative repair-stages catalogue (distinct from Odoo's
    native helpdesk.stage). Standalone master data, no direct
    references from other migrated models.
    """

    _name = "repair_stages"
    _description = "Repair Stages"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "name"
    _order = "sequence, id"

    active = fields.Boolean(string="Active", default=True)
    name = fields.Char(string="Repair Stage")
    accounting_company_id = fields.Many2one("res.company", string="Company")
    description = fields.Char(string="Description")
    sequence = fields.Integer(string="Sequence")

    def _jin_set_company_id(self):
        """Studio server action id 2670 native port."""
        for record in self:
            company_id = self.env.context.get(
                "allowed_company_ids", [self.env.user.company_id.id]
            )[0]
            record.accounting_company_id = company_id

    @api.model_create_multi
    def create(self, vals_list):
        """Replaces automation 306 'JIN - Company Id in Repair Stages'."""
        records = super().create(vals_list)
        records._jin_set_company_id()
        return records


class XRepairSubReason(models.Model):
    """Sub-reasons under a repair reason. Each row links to a
    parent repair_reason via reason_code.
    """

    _name = "repair_sub_reason"
    _description = "Repair Sub Reason"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "name"
    _order = "sequence, id"

    active = fields.Boolean(string="Active", default=True)
    name = fields.Char(string="Sub Reason Code")
    accounting_company_id = fields.Many2one("res.company", string="Company")
    reason_code = fields.Many2one(
        "repair_reason",
        string="Reason Code",
    )
    sequence = fields.Integer(string="Sequence")

    def _jin_set_company_id(self):
        """Studio server action id 2668 native port."""
        for record in self:
            company_id = self.env.context.get(
                "allowed_company_ids", [self.env.user.company_id.id]
            )[0]
            record.accounting_company_id = company_id

    @api.model_create_multi
    def create(self, vals_list):
        """Replaces automation 304 'JIN - Company Id in Repair Sub Reason'."""
        records = super().create(vals_list)
        records._jin_set_company_id()
        return records


# ---------------------------------------------------------------------------
# v241 — Diagnosis/repair master-data catalogues (Chunk 1a of the
# chunk-by-chunk Studio→Python port).
#
# These 6 catalogues are pure lookup tables — no company scoping,
# no automations, no server actions. On Clear-DB they exist as
# Studio-manual models used by project.task.diagnosis_ids
# / task_diagnosis to categorise a repair diagnosis by area,
# code, symptom, condition, and resolution. Porting them here
# unblocks the eventual project.task view port (Chunk 5) which
# references these via m2o traversal.
# ---------------------------------------------------------------------------


class XConditions(models.Model):
    """Repair-condition catalogue. Referenced by
    task_diagnosis.condition (m2o)."""

    _name = "conditions"
    _description = "Conditions"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "name"
    _order = "sequence, id"

    active = fields.Boolean(string="Active", default=True)
    name = fields.Char(string="Condition")
    description = fields.Char(string="Description")
    sequence = fields.Integer(string="Sequence")
    accounting_company_id = fields.Many2one("res.company", string="Company")


class XDiagnosisAreas(models.Model):
    """Diagnosis-area catalogue. Referenced by
    task_diagnosis.diagnosis_area (m2o) and by
    diagnosis_codes.diagnosis_area_1."""

    _name = "diagnosis_areas"
    _description = "Diagnosis Areas"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "name"
    _order = "sequence, id"

    active = fields.Boolean(string="Active", default=True)
    name = fields.Char(string="Diagnosis Area")
    description = fields.Char(string="Description")
    sequence = fields.Integer(string="Sequence")
    accounting_company_id = fields.Many2one("res.company", string="Company")


class XDiagnosisCodes(models.Model):
    """Diagnosis-code catalogue. Each code belongs to one area.
    Referenced by task_diagnosis.diagnosis_code (m2o)."""

    _name = "diagnosis_codes"
    _description = "Diagnosis Codes"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "name"
    _order = "sequence, id"

    active = fields.Boolean(string="Active", default=True)
    name = fields.Char(string="Diagnosis Code")
    description = fields.Char(string="Description")
    sequence = fields.Integer(string="Sequence")
    diagnosis_area_1 = fields.Many2one(
        "diagnosis_areas",
        string="Diagnosis Area",
    )
    accounting_company_id = fields.Many2one("res.company", string="Company")


class XSymptomAreas(models.Model):
    """Symptom-area catalogue. Referenced by
    task_diagnosis.symptom_area (m2o) and by
    symptom_codes.symptom_area."""

    _name = "symptom_areas"
    _description = "Symptom Areas"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "name"
    _order = "sequence, id"

    active = fields.Boolean(string="Active", default=True)
    name = fields.Char(string="Symptom Area")
    description = fields.Char(string="Description")
    sequence = fields.Integer(string="Sequence")
    accounting_company_id = fields.Many2one("res.company", string="Company")


class XSymptomCodes(models.Model):
    """Symptom-code catalogue. Each code belongs to one area.
    Referenced by task_diagnosis.symptom_code (m2o)."""

    _name = "symptom_codes"
    _description = "Symptom Codes"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "name"
    _order = "sequence, id"

    active = fields.Boolean(string="Active", default=True)
    name = fields.Char(string="Symptom Code")
    description = fields.Char(string="Description")
    sequence = fields.Integer(string="Sequence")
    symptom_area = fields.Many2one(
        "symptom_areas",
        string="Symptom Area",
    )
    accounting_company_id = fields.Many2one("res.company", string="Company")


class XResolutions(models.Model):
    """Resolution catalogue. Referenced by
    task_diagnosis.resolution (m2o)."""

    _name = "resolutions"
    _description = "Resolutions"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "name"
    _order = "sequence, id"

    active = fields.Boolean(string="Active", default=True)
    name = fields.Char(string="Resolution")
    description = fields.Char(string="Description")
    sequence = fields.Integer(string="Sequence")
    accounting_company_id = fields.Many2one("res.company", string="Company")


class _RepairMasterDataMigration(models.AbstractModel):
    """Shared migration entrypoint for the five custom repair
    catalogue models. Flips state 'manual'→'base' on:
      1. ir.model rows for the 5 model definitions
      2. All ir.model.fields rows for the 5 models
    and unlinks studio_customization ir.model.data pins on both
    layers.

    Idempotent. DB tables and existing data preserved.
    """

    _name = "repair_master_data.migration"
    _description = "Repair Master Data — Studio→Python migration helper"

    @api.model
    def _migrate_studio_repair_master_data_to_base(self):
        model_names = [
            "repair_accounts",
            "repair_reason",
            "repair_reason_custom",
            "repair_stages",
            "repair_sub_reason",
            # v241 chunk 1a additions
            "conditions",
            "diagnosis_areas",
            "diagnosis_codes",
            "symptom_areas",
            "symptom_codes",
            "resolutions",
        ]
        Model = self.env["ir.model"].sudo()
        Field = self.env["ir.model.fields"].sudo()
        ModelData = self.env["ir.model.data"].sudo()

        # 1. Model rows: state='manual' → 'base'.
        # ir.model.write() blocks 'state' via a hard UserError
        # ("Field 'Type' cannot be modified on models."), so we go
        # around the ORM with raw SQL. Safe here because we only
        # touch the state column on rows we own, and the Python
        # classes are already registered — the flip just aligns the
        # metadata with the actual runtime state.
        model_rows = Model.search([("model", "in", model_names)])
        manual_models = model_rows.filtered(lambda m: m.state == "manual")
        if manual_models:
            self.env.cr.execute(
                "UPDATE ir_model SET state = 'base' WHERE id IN %s",
                (tuple(manual_models.ids),),
            )
            manual_models.invalidate_recordset(["state"])

        # 2. All fields on those models: state='manual' → 'base'.
        # Previous cluster migrations used ir.model.fields.write for
        # this — that works when the fields' owning model is already
        # in registry.pool.models (proved on helpdesk.ticket,
        # project.task, res.users). But here the owning models are
        # our freshly-added Python-defined x_repair_* classes, which
        # are NOT yet in pool.models at data-XML-load time. The
        # ORM write internally calls pool.descendants(patched_models,
        # '_inherits'), which tries pool.models[name] and KeyError's
        # with:
        #   KeyError: 'repair_reason_custom'
        # Same raw-SQL workaround as for ir.model — direct UPDATE
        # bypasses the descendants traversal and the registry lookup.
        field_rows = Field.search([("model", "in", model_names)])
        manual_fields = field_rows.filtered(lambda f: f.state == "manual")
        if manual_fields:
            self.env.cr.execute(
                "UPDATE ir_model_fields SET state = 'base' WHERE id IN %s",
                (tuple(manual_fields.ids),),
            )
            manual_fields.invalidate_recordset(["state"])

        # 3. Drop studio_customization pins on both layers.
        studio_model_pins = ModelData.search(
            [
                ("model", "=", "ir.model"),
                ("res_id", "in", model_rows.ids),
                ("module", "=", "studio_customization"),
            ]
        )
        if studio_model_pins:
            studio_model_pins.unlink()

        studio_field_pins = ModelData.search(
            [
                ("model", "=", "ir.model.fields"),
                ("res_id", "in", field_rows.ids),
                ("module", "=", "studio_customization"),
            ]
        )
        if studio_field_pins:
            studio_field_pins.unlink()

        # 4. Create Fix-repair ir.model.data pins for the models and
        # their fields. Without an ownership pin, Odoo's registry
        # can't associate the ir.model row with our Python classes
        # at load time — the ir.model row exists with state='base'
        # but the class never registers into pool.models, producing
        # KeyError('repair_accounts') on any RPC call to it.
        #
        # Naming convention matches what Odoo auto-generates:
        #   ir.model row       → 'model_' + model.replace('.', '_')
        #   ir.model.fields    → 'field_' + model.replace('.', '_') + '__' + name
        for model_row in model_rows:
            xmlid = "model_" + model_row.model.replace(".", "_")
            existing = ModelData.search(
                [
                    ("module", "=", "Fix-repair"),
                    ("name", "=", xmlid),
                ],
                limit=1,
            )
            if not existing:
                ModelData.create(
                    {
                        "module": "Fix-repair",
                        "name": xmlid,
                        "model": "ir.model",
                        "res_id": model_row.id,
                        "noupdate": True,
                    }
                )

        for field_row in field_rows:
            xmlid = "field_" + field_row.model.replace(".", "_") + "__" + field_row.name
            existing = ModelData.search(
                [
                    ("module", "=", "Fix-repair"),
                    ("name", "=", xmlid),
                ],
                limit=1,
            )
            if not existing:
                ModelData.create(
                    {
                        "module": "Fix-repair",
                        "name": xmlid,
                        "model": "ir.model.fields",
                        "res_id": field_row.id,
                        "noupdate": True,
                    }
                )
