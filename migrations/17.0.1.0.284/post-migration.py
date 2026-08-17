# -*- coding: utf-8 -*-
"""v284 upgrade -- port Studio automation 241 / server action 2427
(RR - Validate Payment %) as an onchange handler on account.payment.

Belt-and-braces on the direct-form-edit path. Fix-repair's
account.payment.register wizard override already enforces the same
advance-payment threshold; this port catches manual account.payment
edits that skip the wizard.

Requires BugFix-Sales v45 for x_studio_sales_order and
x_studio_quotation_type on account.payment. No data migration
required -- onchange fires only on user form interaction.
"""


def migrate(cr, version):
    if not version:
        return
    return
