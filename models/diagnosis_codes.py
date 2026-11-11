from odoo import fields, models


class XDiagnosisCodesGap(models.Model):
    _inherit = "diagnosis_codes"

    active = fields.Boolean()
    name = fields.Char(string="Diagnosis Code")
