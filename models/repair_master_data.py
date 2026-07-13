# -*- coding: utf-8 -*-
from odoo import api, fields, models


class XRepairAccounts(models.Model):
    """Per-company RUG account mapping. Read by Fix-repair's
    account_move.py to find the RUG receivable account for a
    warranty-repair invoice. 2 rows on staging today (one per
    company).
    """
    _name = 'x_repair_accounts'
    _description = 'Repair Accounts'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'x_name'
    _order = 'x_studio_sequence, id'

    x_active = fields.Boolean(string='Active', default=True)
    x_name = fields.Char(string='Name')
    x_studio_company_id = fields.Many2one('res.company', string='Company')
    x_studio_rug_account = fields.Many2one('account.account', string='RUG Account')
    x_studio_sequence = fields.Integer(string='Sequence')


class XRepairReason(models.Model):
    """Master catalogue of repair reasons. Referenced by
    project.task's x_studio_repair_reason M2M and by
    x_repair_sub_reason's x_studio_reason_code M2o.
    """
    _name = 'x_repair_reason'
    _description = 'Repair Reason'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'x_name'
    _order = 'x_studio_sequence, id'

    x_active = fields.Boolean(string='Active', default=True)
    x_color = fields.Integer(string='Color')
    x_name = fields.Char(string='Repair Reason')
    x_studio_company_id = fields.Many2one('res.company', string='Company')
    x_studio_sequence = fields.Integer(string='Sequence')


class XRepairReasonCustom(models.Model):
    """Customer-facing repair reason catalogue. Referenced by
    helpdesk.ticket's x_studio_repair_reason M2M. Parallel to
    x_repair_reason but presented to end customers.
    """
    _name = 'x_repair_reason_custom'
    _description = 'Repair Reason - Customer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'x_name'
    _order = 'x_studio_sequence, id'

    x_active = fields.Boolean(string='Active', default=True)
    x_color = fields.Integer(string='Color')
    x_name = fields.Char(string='Repair Reason')
    x_studio_company_id = fields.Many2one('res.company', string='Company')
    x_studio_sequence = fields.Integer(string='Sequence')


class XRepairStages(models.Model):
    """Alternative repair-stages catalogue (distinct from Odoo's
    native helpdesk.stage). Standalone master data, no direct
    references from other migrated models.
    """
    _name = 'x_repair_stages'
    _description = 'Repair Stages'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'x_name'
    _order = 'x_studio_sequence, id'

    x_active = fields.Boolean(string='Active', default=True)
    x_name = fields.Char(string='Repair Stage')
    x_studio_company_id = fields.Many2one('res.company', string='Company')
    x_studio_description = fields.Char(string='Description')
    x_studio_sequence = fields.Integer(string='Sequence')


class XRepairSubReason(models.Model):
    """Sub-reasons under a repair reason. Each row links to a
    parent x_repair_reason via x_studio_reason_code.
    """
    _name = 'x_repair_sub_reason'
    _description = 'Repair Sub Reason'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'x_name'
    _order = 'x_studio_sequence, id'

    x_active = fields.Boolean(string='Active', default=True)
    x_name = fields.Char(string='Sub Reason Code')
    x_studio_company_id = fields.Many2one('res.company', string='Company')
    x_studio_reason_code = fields.Many2one(
        'x_repair_reason',
        string='Reason Code',
    )
    x_studio_sequence = fields.Integer(string='Sequence')


class _RepairMasterDataMigration(models.AbstractModel):
    """Shared migration entrypoint for the five custom repair
    catalogue models. Flips state 'manual'→'base' on:
      1. ir.model rows for the 5 model definitions
      2. All ir.model.fields rows for the 5 models
    and unlinks studio_customization ir.model.data pins on both
    layers.

    Idempotent. DB tables and existing data preserved.
    """
    _name = 'x_repair_master_data.migration'
    _description = 'Repair Master Data — Studio→Python migration helper'

    @api.model
    def _migrate_studio_repair_master_data_to_base(self):
        model_names = [
            'x_repair_accounts',
            'x_repair_reason',
            'x_repair_reason_custom',
            'x_repair_stages',
            'x_repair_sub_reason',
        ]
        Model = self.env['ir.model'].sudo()
        Field = self.env['ir.model.fields'].sudo()
        ModelData = self.env['ir.model.data'].sudo()

        # 1. Model rows: state='manual' → 'base'.
        # ir.model.write() blocks 'state' via a hard UserError
        # ("Field 'Type' cannot be modified on models."), so we go
        # around the ORM with raw SQL. Safe here because we only
        # touch the state column on rows we own, and the Python
        # classes are already registered — the flip just aligns the
        # metadata with the actual runtime state.
        model_rows = Model.search([('model', 'in', model_names)])
        manual_models = model_rows.filtered(lambda m: m.state == 'manual')
        if manual_models:
            self.env.cr.execute(
                "UPDATE ir_model SET state = 'base' WHERE id IN %s",
                (tuple(manual_models.ids),),
            )
            manual_models.invalidate_recordset(['state'])

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
        #   KeyError: 'x_repair_reason_custom'
        # Same raw-SQL workaround as for ir.model — direct UPDATE
        # bypasses the descendants traversal and the registry lookup.
        field_rows = Field.search([('model', 'in', model_names)])
        manual_fields = field_rows.filtered(lambda f: f.state == 'manual')
        if manual_fields:
            self.env.cr.execute(
                "UPDATE ir_model_fields SET state = 'base' WHERE id IN %s",
                (tuple(manual_fields.ids),),
            )
            manual_fields.invalidate_recordset(['state'])

        # 3. Drop studio_customization pins on both layers.
        studio_model_pins = ModelData.search([
            ('model', '=', 'ir.model'),
            ('res_id', 'in', model_rows.ids),
            ('module', '=', 'studio_customization'),
        ])
        if studio_model_pins:
            studio_model_pins.unlink()

        studio_field_pins = ModelData.search([
            ('model', '=', 'ir.model.fields'),
            ('res_id', 'in', field_rows.ids),
            ('module', '=', 'studio_customization'),
        ])
        if studio_field_pins:
            studio_field_pins.unlink()
