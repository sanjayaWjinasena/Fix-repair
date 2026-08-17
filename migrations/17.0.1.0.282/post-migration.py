# -*- coding: utf-8 -*-
"""v282 upgrade -- port Studio automation 174 'RR - Auto Select Product
for RUG Repairs-3' as a stock.return.picking create/write override on
Fix-repair.

Validates that the wizard's return location_id matches the ticket's
suggested return location (per-company variant) whenever the flow is
RUG or Normal-with-Serial-No. Fields referenced were already declared
in Fix-repair v256, so no schema migration is required -- the
automation itself is what's being ported.
"""


def migrate(cr, version):
    if not version:
        return
    return
