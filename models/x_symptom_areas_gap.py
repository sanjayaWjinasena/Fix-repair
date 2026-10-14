from odoo import fields, models


class XSymptomAreasGap(models.Model):
    _inherit = "x_symptom_areas"

    x_active = fields.Boolean(string="Active")
    x_name = fields.Char(string="Symptom Area")
