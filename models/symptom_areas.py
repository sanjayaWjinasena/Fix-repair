from odoo import fields, models


class XSymptomAreasGap(models.Model):
    _inherit = "symptom_areas"

    active = fields.Boolean()
    name = fields.Char(string="Symptom Area")
