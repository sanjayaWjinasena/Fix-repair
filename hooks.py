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

# View inherits whose xpath targets are Studio-added fields on the
# base view arch. These only resolve when studio_customization is
# installed (that module's own view inherits add the fields to the
# helpdesk.ticket form arch). On stand-alone Odoo installs no such
# module exists → xpath fails → view load aborts.
#
# We can't use "field exists in ir.model.fields" as the sentinel: the
# Fix-repair port declares several of these as Python fields, so the
# metadata exists even where studio_customization is absent. The only
# reliable proxy is the studio_customization module itself.
_STUDIO_DEPENDENT_VIEW_FILES = [
    'views/helpdesk_ticket_studio_field_hides.xml',
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
    """Load view inherits whose xpaths only resolve when the
    studio_customization module has extended the parent view arch
    with its Studio-added field cluster.

    Sentinel: `ir.module.module.state == 'installed'` for
    studio_customization. That's the only reliable signal — a Python
    port of a Studio field (state='base') doesn't imply the field
    is present in the base view's arch, so an ir.model.fields lookup
    would produce false positives on stand-alone DBs.
    """
    Module = env['ir.module.module'].sudo()
    studio = Module.search([
        ('name', '=', 'studio_customization'),
        ('state', '=', 'installed'),
    ], limit=1)
    if not studio:
        _logger.info(
            "Fix-repair: skipping Studio-dependent view hides — "
            "studio_customization module not installed on this DB "
            "(stand-alone install)."
        )
        return

    module_path = get_module_path('Fix-repair')
    for rel_path in _STUDIO_DEPENDENT_VIEW_FILES:
        full_path = os.path.join(module_path, rel_path)
        if not os.path.exists(full_path):
            _logger.warning(
                "Fix-repair: %s listed as conditional data but missing "
                "on disk — skipping.", rel_path,
            )
            continue
        _logger.info("Fix-repair: loading %s (studio_customization installed).",
                     rel_path)
        # Odoo 17: convert_file(env, module, filename, idref, mode,
        # noupdate, kind, pathname). First arg is the env, NOT the
        # cursor — passing env.cr triggers AttributeError on the first
        # `env.context` access inside xml_import.__init__.
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
