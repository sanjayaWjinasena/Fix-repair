# -*- coding: utf-8 -*-
from odoo import api, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            for field_el in arch.xpath("//field[@name='x_studio_order_payment_method']"):
                field_el.set('readonly', "state in ('cancel', 'done', 'sale')")
        return arch, view
