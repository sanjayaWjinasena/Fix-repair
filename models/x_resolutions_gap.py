# -*- coding: utf-8 -*-
from odoo import models, fields

class XResolutionsGap(models.Model):
    _inherit = 'x_resolutions'

    x_active = fields.Boolean(string='Active')
    x_name = fields.Char(string='Resolution')
