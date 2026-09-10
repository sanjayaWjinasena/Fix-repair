# -*- coding: utf-8 -*-
from odoo import models, fields

class XConditionsGap(models.Model):
    _inherit = 'x_conditions'

    x_active = fields.Boolean(string='Active')
    x_name = fields.Char(string='Condition')
