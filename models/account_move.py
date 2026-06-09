# -*- coding: utf-8 -*-
from lxml import etree
from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_rug_invoice = fields.Boolean(compute='_compute_is_rug_invoice')

    @api.depends('invoice_origin', 'move_type')
    def _compute_is_rug_invoice(self):
        for move in self:
            if move.move_type != 'out_invoice' or not move.invoice_origin:
                move.is_rug_invoice = False
                continue
            so = self.env['sale.order'].sudo().search(
                [('name', '=', move.invoice_origin)], limit=1
            )
            move.is_rug_invoice = so.x_studio_quotation_type == 'Repair'

    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            for sheet in arch.xpath('//sheet'):
                fld = etree.Element('field')
                fld.set('name', 'is_rug_invoice')
                fld.set('invisible', '1')
                sheet.insert(0, fld)
                break
            for header in arch.xpath('//header'):
                btn = etree.Element('button')
                btn.set('name', 'action_change_to_rug_account')
                btn.set('string', 'Change to RUG Account')
                btn.set('type', 'object')
                btn.set('class', 'btn-secondary')
                btn.set('invisible', 'not is_rug_invoice or state != "draft"')
                header.insert(0, btn)
                break
        return arch, view

    def action_change_to_rug_account(self):
        for move in self:
            config = self.env['x_repair_accounts'].sudo().search(
                [('x_studio_company_id', '=', move.company_id.id)], limit=1
            )
            if not config or not config.x_studio_rug_account:
                raise UserError(
                    f"No RUG account configured for company '{move.company_id.name}'. "
                    "Please set it up in Repair Accounts."
                )
            rug_account = config.x_studio_rug_account
            product_lines = move.invoice_line_ids.filtered(
                lambda l: l.display_type not in ('line_section', 'line_note')
            )
            product_lines.write({'account_id': rug_account.id})
