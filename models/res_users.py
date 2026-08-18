# -*- coding: utf-8 -*-
"""res.users Studio-port surface fully relocated to
`studio_usermodel_migration` — this module now owns nothing on
res.users.

Historical context:
  v215-v275: this file declared 6 Studio fields on res.users
    (4 location m2o + 2 super-user booleans) plus the
    _super_user_validate guard and create/write overrides that
    replaced automation 250.
  v289: fields, guard, and overrides moved to
    studio_usermodel_migration/models/res_users.py so that
    module's res.users form view arch (which references those
    fields) can validate cleanly at load time (SUM loads BEFORE
    Fix-repair in the dep graph — the fields must exist by then).
  v290 (this file): removed the ResUsers class entirely to prevent
    accidental double-declaration or drift.

helpdesk.ticket related='user_id.x_studio_virtual_location' chains
still work because SUM declares the underlying user field first.

Kept as a stub so:
  * imports (from . import res_users in models/__init__.py) don't
    KeyError
  * any git history reference to this path resolves
"""
