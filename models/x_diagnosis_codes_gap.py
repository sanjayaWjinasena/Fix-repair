# -*- coding: utf-8 -*-
from odoo import models, fields

class XDiagnosisCodesGap(models.Model):
    _inherit = 'x_diagnosis_codes'

    x_active = fields.Boolean(string='Active')
    x_name = fields.Char(string='Diagnosis Code')
