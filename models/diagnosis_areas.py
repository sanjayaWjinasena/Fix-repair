from odoo import fields, models


class XDiagnosisAreasGap(models.Model):
    _inherit = "diagnosis_areas"

    active = fields.Boolean()
    name = fields.Char(string="Diagnosis Area")
