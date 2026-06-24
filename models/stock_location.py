# -*- coding: utf-8 -*-
from odoo import fields, models


class StockLocation(models.Model):
    _inherit = 'stock.location'

    usage = fields.Selection(
        selection_add=[('repair', 'Repair')],
        ondelete={'repair': 'set default'},
    )
