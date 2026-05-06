# -*- coding: utf-8 -*-
from odoo import models


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    def action_assign_to_me(self):
        self.write({'user_id': self.env.uid})
