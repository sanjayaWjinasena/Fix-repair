# -*- coding: utf-8 -*-
"""Post-install cleanup hook for Fix-repair.

Once the 12 res.partner x_studio_* fields ported in v225 have Python
declarations here, the `studio_customization` ir.model.data (xmlid) rows
that used to own them are pure duplicate metadata. This hook removes
those redundant xmlids so `ir.model.fields.modules` no longer reads
"Fix-repair, studio_customization" for the ported fields.

Same pattern as BugFix-Sales' hook (hooks.py in that module).

Scope: only the 12 fields listed below, only their ir.model.data rows
where module='studio_customization'. Field records themselves and
their column data are left alone. Idempotent.
"""
import logging
import os

from odoo.modules.module import get_module_path
from odoo.tools import convert_file

_logger = logging.getLogger(__name__)

# (relative XML path, field on helpdesk.ticket that must exist for the
# view inherit to have targets in the base view arch)
_CONDITIONAL_DATA = [
    ('views/helpdesk_ticket_studio_field_hides.xml', 'x_studio_rug_repair'),
]

# Kept in sync with models/res_partner.py.
_PORTED_PARTNER_FIELDS = (
    # bank guarantee documents
    'x_studio_bank_guarantee_docs',
    'x_studio_bank_guarantee_docs_filename',
    'x_studio_mandatory_bank_guarantee',
    # vendor master
    'x_studio_vendor_account',
    'x_studio_vendor_name',
    'x_studio_address',
    # VAT / SVAT compliance
    'x_studio_vat_registered',
    'x_studio_vat_registration_number',
    'x_studio_vat_registration_status',
    'x_studio_vat_exempted_number',
    'x_studio_svat_registration_number',
    'x_studio_svat_registration_status',
)


def strip_studio_xmlids_for_ported_fields(env):
    """Delete studio_customization ir.model.data rows for the 12 ported fields.

    Called from post_init_hook (fresh install) and from
    migrations/17.0.1.0.225/post-migration.py (existing DB upgrade).
    """
    Fields = env['ir.model.fields'].sudo()
    IMD = env['ir.model.data'].sudo()

    field_ids = Fields.search([
        ('model', '=', 'res.partner'),
        ('name', 'in', list(_PORTED_PARTNER_FIELDS)),
    ]).ids
    if not field_ids:
        return

    stale = IMD.search([
        ('module', '=', 'studio_customization'),
        ('model', '=', 'ir.model.fields'),
        ('res_id', 'in', field_ids),
    ])
    if not stale:
        return

    _logger.info(
        "Fix-repair: unlinking %d studio_customization xmlids for the "
        "res.partner x_studio_* fields now owned by Fix-repair.",
        len(stale),
    )
    stale.unlink()


def load_conditional_studio_view_hides(env):
    """Load view inherits whose xpaths only resolve when Studio-added
    fields are present in the parent view arch.

    On the Jinasena production DB the target Studio fields exist and the
    xpath resolves; on a stand-alone install those fields aren't there
    and any unresolved xpath aborts the whole view load with:

      Element '<xpath expr="//field[@name='x_studio_rug_repair']">'
      cannot be located in parent view

    Each entry in _CONDITIONAL_DATA names a sentinel Studio field. If
    it exists on helpdesk.ticket (state=manual OR base), the whole view
    inherit is loaded; otherwise skipped.
    """
    Fields = env['ir.model.fields'].sudo()
    module_path = get_module_path('Fix-repair')

    for rel_path, sentinel in _CONDITIONAL_DATA:
        exists = Fields.search([
            ('model', '=', 'helpdesk.ticket'),
            ('name', '=', sentinel),
        ], limit=1)
        if not exists:
            _logger.info(
                "Fix-repair: skipping %s (sentinel field %r not present "
                "on this DB — stand-alone install).",
                rel_path, sentinel,
            )
            continue
        full_path = os.path.join(module_path, rel_path)
        if not os.path.exists(full_path):
            _logger.warning(
                "Fix-repair: %s listed as conditional data but missing "
                "on disk — skipping.", rel_path,
            )
            continue
        _logger.info("Fix-repair: loading %s (sentinel %r present).",
                     rel_path, sentinel)
        # Odoo 17 signature: convert_file(env, module, filename, idref,
        # mode, noupdate, kind, pathname). First arg is the env, NOT
        # the cursor — passing env.cr triggers AttributeError on the
        # first `env.context` access inside xml_import.__init__.
        convert_file(
            env,
            'Fix-repair',
            rel_path,
            {},
            mode='init',
            noupdate=False,
            kind='data',
            pathname=full_path,
        )


def post_init_hook(env):
    """Odoo 17 post-install hook signature: (env)."""
    strip_studio_xmlids_for_ported_fields(env)
    load_conditional_studio_view_hides(env)
