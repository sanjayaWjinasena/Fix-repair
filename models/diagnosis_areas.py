from odoo import fields, models


class XDiagnosisAreasGap(models.Model):
    _inherit = "diagnosis_areas"

    active = fields.Boolean(string="Active")
    name = fields.Char(string="Diagnosis Area")
