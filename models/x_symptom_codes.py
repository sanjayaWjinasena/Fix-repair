from odoo import fields, models


class XSymptomCodesGap(models.Model):
    _inherit = "symptom_codes"

    active = fields.Boolean(string="Active")
    name = fields.Char(string="Symptom Code")
