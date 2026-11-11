from odoo import fields, models


class XSymptomCodesGap(models.Model):
    _inherit = "symptom_codes"

    active = fields.Boolean()
    name = fields.Char(string="Symptom Code")
