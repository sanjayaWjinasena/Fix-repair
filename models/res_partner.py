"""res.partner Studio-field port into Fix-repair.

Twelve x_studio_* fields on res.partner that were still Studio-only after
the BugFix-Sales v30-v32 port (which claimed the 4 bank-guarantee gates:
amount, expiry_date, payment_method, valid_bank_guarantee). What lands
here is the remainder — bank-guarantee docs, vendor master, and VAT/SVAT
tax compliance.

Deliberately NOT ported here (blocked by Studio-only target models):
  - customer_group (m2o -> customer_group, Studio-only model)
  - vendor_group  (m2o -> vendor_group,  Studio-only model)
  - group_type    (stored related through customer_group)

Porting those would require also declaring customer_group /
vendor_group as Python models — separate scope.
"""

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    # --- Bank guarantee documents (complements BugFix-Sales' 4 BG fields) ---
    bank_guarantee_docs = fields.Binary(
        string="Bank Guarantee Docs.",
    )
    bank_guarantee_docs_filename = fields.Char()
    mandatory_bank_guarantee = fields.Boolean()

    # --- Vendor master (skips vendor_group by design) ------------
    vendor_account = fields.Many2one(
        "res.partner",
        ondelete="set null",
    )
    vendor_name = fields.Char(
        string="Vendor Name",
        related="vendor_account.complete_name",
        store=True,
        readonly=True,
    )
    address = fields.Char(
        string="Address",
        related="vendor_account.contact_address",
        readonly=True,
    )

    # --- VAT / SVAT tax compliance ----------------------------------------
    vat_registered = fields.Boolean(
        string="VAT Registered",
    )
    vat_registration_number = fields.Char(
        string="VAT Registration Number",
    )
    vat_registration_status = fields.Selection(
        # 'Excempted' spelling preserved to match existing DB values.
        [
            ("VAT Registered", "VAT Registered"),
            ("VAT Not Registered", "VAT Not Registered"),
            ("VAT Excempted", "VAT Excempted"),
        ],
        string="VAT Registration Status",
    )
    vat_exempted_number = fields.Char(
        string="VAT Exempted Number",
    )
    svat_registration_number = fields.Char(
        string="SVAT Registration Number",
    )
    svat_registration_status = fields.Selection(
        # 'SVAT Nor Registered' key preserved to match existing DB values.
        [
            ("SVAT Nor Registered", "SVAT Not Registered"),
            ("SVAT Registered", "SVAT Registered"),
        ],
        string="SVAT Registration Status",
    )
