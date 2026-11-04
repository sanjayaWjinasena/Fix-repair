from odoo import fields, models


class XResolutionsGap(models.Model):
    _inherit = "resolutions"

    active = fields.Boolean(string="Active")
    name = fields.Char(string="Resolution")
