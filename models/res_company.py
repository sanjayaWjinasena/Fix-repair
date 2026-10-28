# -*- coding: utf-8 -*-
"""Repair numbering sequences, one per company (as on Clear-DB).

Repair tickets get their number from ir.sequence 'repair.seq' (REPAIR/<year>/NNNNN, see
helpdesk.ticket._repair_seq_no_on_create_or_write) and auto-created repair serials from
'repair.serial.seq'. On Clear-DB both were made by hand per company, so wherever Fix-repair was
installed without them tickets kept the subject "New". They are now created by the module: on
install, on upgrade (migrations/17.0.1.0.377) and for every new company. A company that already
has a sequence for a code keeps it untouched (counter included).
"""
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

# Settings as on Clear-DB (ir.sequence 811/278 and 812/279, read 2026-10-28). Clear-DB's serial
# prefix starts with a stray tab character; it is left out here.
REPAIR_SEQUENCES = (
    {'code': 'repair.seq', 'name': 'Repair Sequence No', 'prefix': 'REPAIR/%(year)s/'},
    {'code': 'repair.serial.seq', 'name': 'Repair Serial Sequence No', 'prefix': 'REP-SERIAL/%(year)s/'},
)


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        companies._jin_ensure_repair_sequences()
        return companies

    def _jin_ensure_repair_sequences(self):
        """Create the missing repair sequences for these companies (all companies when empty)."""
        Sequence = self.env['ir.sequence'].sudo()
        companies = self or self.sudo().search([])
        created = 0
        for company in companies:
            for seq in REPAIR_SEQUENCES:
                if Sequence.search_count([('code', '=', seq['code']), ('company_id', '=', company.id)]):
                    continue
                Sequence.create(dict(seq, padding=5, number_increment=1, number_next=1,
                                     implementation='standard', company_id=company.id))
                created += 1
        if created:
            _logger.info('Fix-repair: created %s repair sequence(s) for %s', created, companies.mapped('name'))
        return created
