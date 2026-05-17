# -*- coding: utf-8 -*-
from odoo import models


class ProjectTask(models.Model):
    _inherit = 'project.task'

    def action_create_sale_order(self):
        return super(ProjectTask, self.with_context(create_as_quotation=True)).action_create_sale_order()

    def action_fsm_validate(self, stop_running_timers=False):
        return super(ProjectTask, self.with_context(create_as_quotation=True)).action_fsm_validate(
            stop_running_timers=stop_running_timers
        )
