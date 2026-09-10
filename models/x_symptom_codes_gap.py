# -*- coding: utf-8 -*-
from odoo import models, fields

class XSymptomCodesGap(models.Model):
    _inherit = 'x_symptom_codes'

    x_active = fields.Boolean(string='Active')
    x_name = fields.Char(string='Symptom Code')
