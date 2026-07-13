# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HelpdeskTicketType(models.Model):
    """Studio fields migrated to Python on helpdesk.ticket.type.

    These four Booleans configure the semantics of a ticket type:
    whether it's an under-warranty repair (RUG), whether the RUG has
    been confirmed at type setup, and whether the type requires a
    serial number. HelpdeskTicket's related chains
    (x_studio_rug_repair, x_studio_rug_confirmed,
    x_studio_normal_repair_with/without_serial_no) walk here.
    """
    _inherit = 'helpdesk.ticket.type'

    x_studio_rug = fields.Boolean(string='RUG')
    x_studio_rug_confirmed = fields.Boolean(string='RUG Confirmed')
    x_studio_with_serial_no = fields.Boolean(string='With Serial No')
    x_studio_without_serial_no = fields.Boolean(string='Without Serial No')

    @api.model
    def _migrate_studio_ticket_type_cluster_to_base(self):
        """Flip state='manual'→'base' and unlink studio_customization
        pins for the four x_studio_* fields on helpdesk.ticket.type.
        Idempotent; DB columns and data preserved."""
        cluster = [
            'x_studio_rug',
            'x_studio_rug_confirmed',
            'x_studio_with_serial_no',
            'x_studio_without_serial_no',
        ]
        Field = self.env['ir.model.fields'].sudo()
        rows = Field.search([
            ('model', '=', 'helpdesk.ticket.type'),
            ('name', 'in', cluster),
        ])
        manual_rows = rows.filtered(lambda f: f.state == 'manual')
        if manual_rows:
            manual_rows.write({'state': 'base'})

        ModelData = self.env['ir.model.data'].sudo()
        studio_pins = ModelData.search([
            ('model', '=', 'ir.model.fields'),
            ('res_id', 'in', rows.ids),
            ('module', '=', 'studio_customization'),
        ])
        if studio_pins:
            studio_pins.unlink()


class HelpdeskStage(models.Model):
    """Studio field migrated to Python on helpdesk.stage.

    x_studio_company_id enables per-company stage filtering. The
    Cluster 5 stage-validation computes on helpdesk.ticket use
    hardcoded stage ids per company (id 1 vs id 2) — this field
    is the master data that maps a stage to its owning company.
    """
    _inherit = 'helpdesk.stage'

    x_studio_company_id = fields.Many2one(
        'res.company',
        string='Company',
    )

    @api.model
    def _migrate_studio_stage_cluster_to_base(self):
        """Flip state='manual'→'base' and unlink studio_customization
        pins for x_studio_company_id on helpdesk.stage.
        Idempotent; DB column and data preserved."""
        Field = self.env['ir.model.fields'].sudo()
        rows = Field.search([
            ('model', '=', 'helpdesk.stage'),
            ('name', 'in', ['x_studio_company_id']),
        ])
        manual_rows = rows.filtered(lambda f: f.state == 'manual')
        if manual_rows:
            manual_rows.write({'state': 'base'})

        ModelData = self.env['ir.model.data'].sudo()
        studio_pins = ModelData.search([
            ('model', '=', 'ir.model.fields'),
            ('res_id', 'in', rows.ids),
            ('module', '=', 'studio_customization'),
        ])
        if studio_pins:
            studio_pins.unlink()
