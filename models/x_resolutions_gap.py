from odoo import fields, models


class XResolutionsGap(models.Model):
    _inherit = 'x_resolutions'

    x_active = fields.Boolean(string='Active')
    x_name = fields.Char(string='Resolution')
