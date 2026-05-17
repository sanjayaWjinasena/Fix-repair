# -*- coding: utf-8 -*-
from odoo import models


class ProjectTask(models.Model):
    _inherit = 'project.task'

    def action_create_sale_order(self):
        return super(ProjectTask, self.with_context(create_as_quotation=True)).action_create_sale_order()
