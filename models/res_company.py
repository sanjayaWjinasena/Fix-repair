# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    factory_repair_location_id = fields.Many2one(
        'stock.location',
        string='Factory Repair Location',
        domain="[('usage', '=', 'internal'), ('company_id', 'in', (False, id))]",
        help="Stock location items are moved to when a repair ticket reaches "
             "'Received at Factory'. Source for the reverse leg too.",
    )
