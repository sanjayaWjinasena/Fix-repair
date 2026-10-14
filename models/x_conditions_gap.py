from odoo import fields, models


class XConditionsGap(models.Model):
    _inherit = 'x_conditions'

    x_active = fields.Boolean(string='Active')
    x_name = fields.Char(string='Condition')
