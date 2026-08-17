# -*- coding: utf-8 -*-
"""v286 upgrade -- Odoo-17 gap in RUG-invoice validation port.

Same pattern as v285's fix for the Track Lock Status trio: Studio
automation 215 gated on `sale.order.state == 'done'`. Odoo 17 removed
the `done` state (states are draft/sent/sale/cancel) and moved the
lock semantic to a Boolean `locked`. My v281 port faithfully
reproduced the broken gate; v286 swaps it for `so.locked` so the
RUG-invoice auto-settle actually fires.

No data migration required -- code-only fix.
"""


def migrate(cr, version):
    if not version:
        return
    return
