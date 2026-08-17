# -*- coding: utf-8 -*-
"""v280 upgrade — port Studio automation 215 'RR - Validate RUG in
Customer Invoice' + declare x_studio_rug_confirmed and
x_studio_rug_acc_updated on account.move.

No data migration script needed; declarations take effect via Odoo's
normal module upgrade path. On Clear-DB the corresponding state='manual'
rows already exist and get flipped to state='base' owned by Fix-repair.
"""


def migrate(cr, version):
    if not version:
        return
    return
