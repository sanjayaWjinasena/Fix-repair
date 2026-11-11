from odoo import fields, models


class XConditionsGap(models.Model):
    _inherit = "conditions"

    active = fields.Boolean()
    name = fields.Char(string="Condition")
