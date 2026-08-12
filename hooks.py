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
    # ORDER MATTERS. Odoo validates each new view's xpath against the
    # CURRENT composed arch at load time. field_hides.xml xpaths into
    # fields like x_studio_rug_repair, x_studio_quick_repair_status,
    # etc. — which only exist in the composed arch AFTER ported.xml
    # has been loaded. So ported.xml must load first.

    # v233-v235: 4 helpdesk.ticket views repinned to Fix-repair during
    # earlier migration but whose arch_db never landed in on-disk XML.
    # Adds the full Studio field cluster (Return Receipt Location,
    # Repair Reason, Job Location, Serial Number, Warranty Details
    # tab, Cancel/Reopen Log tab, ~90 field placements total) and
    # rewires several buttons.
    #
    # Loaded here instead of manifest data because contains xpath
    # references to //button[@name='195'] (Studio-added return button
    # injected by helpdesk_stock's OWN sibling inherit at a different
    # priority) — Odoo's strict init-time xml validation composes the
    # parent view without sibling inherits and rejects the xpath.
    # convert_file at post-init runs after ALL inherits are applied,
    # so the xpath resolves cleanly.
    'views/helpdesk_ticket_studio_ported.xml',

    # v228: hides for 9 Studio-added fields that we don't want visible
    # on the ticket form. xpath targets must exist in the composed arch
    # → depends on ported.xml having loaded first.
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


def load_post_init_view_files(env):
    """Load view inherits whose xpaths reference elements that only
    exist AFTER the full inherit chain has been applied to the parent
    view. Loading these at manifest-'data' time triggers Odoo's
    init-time xml validation, which composes the parent view arch
    WITHOUT sibling inherits and rejects xpaths pointing at
    still-missing elements (e.g. `//button[@name='195']` added by
    helpdesk_stock's own inherit).

    Running via convert_file at post_init phase side-steps that
    validation — every module's own data has already been loaded by
    the time this hook runs, so the composed arch has all buttons
    and fields present.

    v235: dropped the `studio_customization installed` gate. On
    stand-alone Odoo installs we WANT these view arches loaded too
    (they define the full repair-flow field layout on
    helpdesk.ticket). The gate was defensive when the arches used
    to hit fields that weren't Python-declared; the field audit
    (2026-08-12) confirmed all 91 x_studio_* refs already have
    Python declarations in Fix-repair (state=base), so loading is
    safe on both envs.
    """
    module_path = get_module_path('Fix-repair')
    for rel_path in _STUDIO_DEPENDENT_VIEW_FILES:
        full_path = os.path.join(module_path, rel_path)
        if not os.path.exists(full_path):
            _logger.warning(
                "Fix-repair: %s listed as conditional data but missing "
                "on disk — skipping.", rel_path,
            )
            continue
        _logger.info("Fix-repair: loading %s.", rel_path)
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


# Backward-compat shim — external references (migration scripts,
# tests) may still call the old name.
load_conditional_studio_view_hides = load_post_init_view_files


def post_init_hook(env):
    """Odoo 17 post-install hook signature: (env)."""
    strip_studio_xmlids_for_ported_fields(env)
    load_post_init_view_files(env)
