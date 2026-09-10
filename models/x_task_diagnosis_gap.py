# -*- coding: utf-8 -*-
from odoo import models, fields

class XTaskDiagnosisGap(models.Model):
    _inherit = 'x_task_diagnosis'

    x_active = fields.Boolean(string='Active')
    x_name = fields.Char(string='Name')
