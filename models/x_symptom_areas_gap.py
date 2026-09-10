# -*- coding: utf-8 -*-
from odoo import models, fields

class XSymptomAreasGap(models.Model):
    _inherit = 'x_symptom_areas'

    x_active = fields.Boolean(string='Active')
    x_name = fields.Char(string='Symptom Area')
