# -*- coding: utf-8 -*-
from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        if self.env.context.get('create_as_quotation'):
            return True
        return super().action_confirm()
