from odoo import fields, models


class XSymptomAreasGap(models.Model):
    _inherit = "symptom_areas"

    active = fields.Boolean(string="Active")
    name = fields.Char(string="Symptom Area")
