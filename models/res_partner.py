# -*- coding: utf-8 -*-
"""res.partner Studio-field port into Fix-repair.

Twelve x_studio_* fields on res.partner that were still Studio-only after
the BugFix-Sales v30-v32 port (which claimed the 4 bank-guarantee gates:
amount, expiry_date, payment_method, valid_bank_guarantee). What lands
here is the remainder — bank-guarantee docs, vendor master, and VAT/SVAT
tax compliance.

Deliberately NOT ported here (blocked by Studio-only target models):
  - x_studio_customer_group (m2o -> x_customer_group, Studio-only model)
  - x_studio_vendor_group  (m2o -> x_vendor_group,  Studio-only model)
  - x_studio_group_type    (stored related through x_studio_customer_group)

Porting those would require also declaring x_customer_group /
x_vendor_group as Python models — separate scope.
"""
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # --- Bank guarantee documents (complements BugFix-Sales' 4 BG fields) ---
    x_studio_bank_guarantee_docs = fields.Binary(
        string='Bank Guarantee Docs.',
    )
    x_studio_bank_guarantee_docs_filename = fields.Char(
        string='Bank Guarantee Docs Filename',
    )
    x_studio_mandatory_bank_guarantee = fields.Boolean(
        string='Mandatory Bank Guarantee',
    )

    # --- Vendor master (skips x_studio_vendor_group by design) ------------
    x_studio_vendor_account = fields.Many2one(
        'res.partner',
        string='Vendor Account',
        ondelete='set null',
    )
    x_studio_vendor_name = fields.Char(
        string='Vendor Name',
        related='x_studio_vendor_account.complete_name',
        store=True,
        readonly=True,
    )
    x_studio_address = fields.Char(
        string='Address',
        related='x_studio_vendor_account.contact_address',
        readonly=True,
    )

    # --- VAT / SVAT tax compliance ----------------------------------------
    x_studio_vat_registered = fields.Boolean(
        string='VAT Registered',
    )
    x_studio_vat_registration_number = fields.Char(
        string='VAT Registration Number',
    )
    x_studio_vat_registration_status = fields.Selection(
        # 'Excempted' spelling preserved to match existing DB values.
        [
            ('VAT Registered', 'VAT Registered'),
            ('VAT Not Registered', 'VAT Not Registered'),
            ('VAT Excempted', 'VAT Excempted'),
        ],
        string='VAT Registration Status',
    )
    x_studio_vat_exempted_number = fields.Char(
        string='VAT Exempted Number',
    )
    x_studio_svat_registration_number = fields.Char(
        string='SVAT Registration Number',
    )
    x_studio_svat_registration_status = fields.Selection(
        # 'SVAT Nor Registered' key preserved to match existing DB values.
        [
            ('SVAT Nor Registered', 'SVAT Not Registered'),
            ('SVAT Registered', 'SVAT Registered'),
        ],
        string='SVAT Registration Status',
    )
