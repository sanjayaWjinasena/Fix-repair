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

# View files loaded via post_init phase (deferred past manifest 'data')
# so xpath validation runs after every module's sibling inherits are
# applied to the parent view. ORDER MATTERS — ported.xml adds field
# placements that field_hides.xml then targets.
#
# v242: sentinel-gate dropped. helpdesk_ticket_studio_ported.xml no
# longer references any Clear-DB-specific numeric action IDs (view
# #4013 removed entirely, #4012's one //button[@name='195'] xpath
# stripped). Files are safe to load on any DB now.
_STUDIO_DEPENDENT_VIEW_FILES = [
    # 3 helpdesk.ticket views repinned to Fix-repair during earlier
    # migration but whose arch_db never landed in on-disk XML:
    #   view_helpdesk_ticket_form_4012  (form  — ~90 field placements)
    #   view_helpdesk_ticket_kanban_4735 (kanban)
    #   view_helpdesk_ticket_tree_5027  (tree)
    'views/helpdesk_ticket_studio_ported.xml',

    # v228: hides for 9 Studio-added fields. Loads AFTER ported.xml —
    # its xpaths target fields that ported.xml adds.
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


# v243: 12 repair-pipeline stage xmlids from data/repair_stages.xml.
# Kept in sync with that file. Used by attach_repair_stages_to_all_teams
# to iterate over the newly-seeded stages.
_REPAIR_STAGE_XMLIDS = (
    'Fix-repair.stage_sent_to_factory',
    'Fix-repair.stage_received_at_factory',
    'Fix-repair.stage_diagnosis',
    'Fix-repair.stage_estimation_sent_to_customer',
    'Fix-repair.stage_estimation_approval_received',
    'Fix-repair.stage_advance_received',
    'Fix-repair.stage_repair_started',
    'Fix-repair.stage_repair_completed',
    'Fix-repair.stage_sent_to_sales_centre',
    'Fix-repair.stage_received_at_sales_centre',
    'Fix-repair.stage_handed_over_to_customer',
    'Fix-repair.stage_cancelled',
)


def attach_repair_stages_to_all_teams(env):
    """Attach the 12 seeded repair-pipeline stages to every existing
    helpdesk.team record.

    Odoo's helpdesk.stage only shows on a team's statusbar when the
    stage is in that team's team_ids m2m. We ship the stages via XML
    without team_ids (so the seed works even before any team exists)
    and then attach them here.

    Idempotent — re-runs find the team already in stage.team_ids and
    no-op via set() semantics on the m2m write.
    """
    Stage = env['helpdesk.stage'].sudo()
    Team = env['helpdesk.team'].sudo()

    stage_ids = []
    for xmlid in _REPAIR_STAGE_XMLIDS:
        stage = env.ref(xmlid, raise_if_not_found=False)
        if stage:
            stage_ids.append(stage.id)
    if not stage_ids:
        _logger.warning(
            "Fix-repair: no repair-pipeline stages found via ir.model.data — "
            "skipping team attachment. Was data/repair_stages.xml loaded?"
        )
        return

    team_ids = Team.search([]).ids
    if not team_ids:
        _logger.info(
            "Fix-repair: no helpdesk.team records exist yet — "
            "repair-pipeline stages seeded but unattached. Attach via "
            "Configuration → Stages once teams exist."
        )
        return

    stages = Stage.browse(stage_ids)
    for stage in stages:
        current = set(stage.team_ids.ids)
        needed = current | set(team_ids)
        if needed != current:
            stage.team_ids = [(6, 0, sorted(needed))]

    _logger.info(
        "Fix-repair: attached %d repair-pipeline stages to %d team(s).",
        len(stage_ids), len(team_ids),
    )


def post_init_hook(env):
    """Odoo 17 post-install hook signature: (env)."""
    strip_studio_xmlids_for_ported_fields(env)
    load_post_init_view_files(env)
    attach_repair_stages_to_all_teams(env)
