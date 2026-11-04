from odoo import fields, models


class XConditionsGap(models.Model):
    _inherit = "conditions"

    active = fields.Boolean(string="Active")
    name = fields.Char(string="Condition")
