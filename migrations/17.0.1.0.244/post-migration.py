# -*- coding: utf-8 -*-
"""v244 post-migration — no-op on upgrade path.

v244 moved helpdesk_ticket_studio_ported.xml + _studio_field_hides.xml
into manifest 'data'. That means the normal manifest-data load created
the ir.model.data entries fresh at upgrade time — no need for
post-migration action here.

This file exists only so Odoo runs its version-bump housekeeping;
the actual load happens during manifest-data processing before this
script fires.
"""


def migrate(cr, version):
    pass
