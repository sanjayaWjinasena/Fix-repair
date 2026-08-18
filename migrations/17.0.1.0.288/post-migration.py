# -*- coding: utf-8 -*-
"""v288 upgrade -- narrow v286's RUG-invoice settle guard so background
writes (v287's SO -> invoice compute propagation) don't trip it.

v286 guard fired on ANY write that included one of the four watched
fields:
    {x_studio_rug_confirmed, x_studio_rug_acc_updated,
     state, payment_state}
which meant v287's SO-side rug_confirmed propagation cascaded into
the invoice and hit "Cannot settle RUG invoice ... SO must be locked"
even though the user hadn't asked to settle anything.

v288 narrows the guard: it only fires when the current write is
explicitly setting rug_acc_updated to True. That's the actual
Studio-automation intent (settle when the accounts team clicks
'Change to RUG Account'), and background computes / propagations
that touch only rug_confirmed no longer trip it.

No data migration required -- code-only fix.
"""


def migrate(cr, version):
    if not version:
        return
    return
