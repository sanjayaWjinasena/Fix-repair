# -*- coding: utf-8 -*-
"""v296 post-migration — per-company repair sequence seed + backfill.

Fixes two symptoms on Clear-DB-style multi-company installs:

  1. ir.sequence records for code='repair.seq' / 'repair.serial.seq'
     inherited company_id from the installer's active company at
     initial-install time (typically the base 'My Company', id=1).
     helpdesk.ticket.create() records under any other company then
     call next_by_code() and get False back — the ticket's name
     stays at the sentinel 'New' instead of REPAIR/YYYY/NNNNN.

  2. All tickets accumulated under that broken state need a proper
     sequence-generated name assigned.

Runs after Odoo's normal manifest-data load, which — thanks to
`noupdate="1"` on data/repair_sequences.xml — does NOT overwrite the
existing sequence records with the newly-declared `company_id=False`
value. So we null out the templates here explicitly, then delegate to
hooks.seed_repair_sequences_per_company + assign_names_to_stale_new_tickets
for the actual seeding/backfill.
"""
import importlib.util
import logging
import os

from odoo import SUPERUSER_ID, api
from odoo.modules.module import get_module_path

_logger = logging.getLogger(__name__)


def _null_out_template_company_ids(env):
    """Clear company_id on the two 'template' ir.sequence records so
    they behave as the global fallback the XML now declares them to be.

    Idempotent — skips records already at company_id=False.
    """
    for xmlid in (
        'Fix-repair.seq_repair_ticket',
        'Fix-repair.seq_repair_serial',
    ):
        seq = env.ref(xmlid, raise_if_not_found=False)
        if not seq:
            _logger.warning(
                "Fix-repair v296 migration: sequence %s missing — "
                "cannot reset company_id.", xmlid,
            )
            continue
        if seq.company_id:
            prev = seq.company_id.display_name
            seq.sudo().write({'company_id': False})
            _logger.info(
                "Fix-repair v296 migration: cleared company_id on %s "
                "(was %s).", xmlid, prev,
            )


def migrate(cr, version):
    if not version:
        # Fresh install path — post_init_hook handles it.
        return

    # Dynamic-load hooks.py: the module name 'Fix-repair' has a dash,
    # which breaks `from odoo.addons.Fix-repair.hooks import ...`.
    # Same pattern as migrations/17.0.1.0.225/post-migration.py.
    hooks_path = os.path.join(get_module_path('Fix-repair'), 'hooks.py')
    spec = importlib.util.spec_from_file_location(
        'fix_repair_hooks', hooks_path,
    )
    hooks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hooks)

    env = api.Environment(cr, SUPERUSER_ID, {})
    _null_out_template_company_ids(env)
    hooks.seed_repair_sequences_per_company(env)
    hooks.assign_names_to_stale_new_tickets(env)
