from odoo import fields, models


class XDiagnosisAreasGap(models.Model):
    _inherit = "x_diagnosis_areas"

    x_active = fields.Boolean(string="Active")
    x_name = fields.Char(string="Diagnosis Area")
