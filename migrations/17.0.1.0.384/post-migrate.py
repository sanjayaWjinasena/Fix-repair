"""v384 (trial v373): repair ticket and repair serial number sequences on databases where Fix-repair is already installed.

data/repair_sequence_data.xml (the company-less templates for repair.seq / repair.serial.seq) is loaded again;
the per-company copies are made by hooks.seed_repair_sequences_per_company, which so far ran only on a fresh
install (post_init_hook). Without them next_by_code('repair.seq') returns False and new repair tickets keep the
name 'New'. Idempotent: a company that already has its own sequence for a code (Clear-DB, upgrade-testing)
is skipped, so its counter is untouched.
"""
import importlib

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    hooks = importlib.import_module("odoo.addons.Fix-repair.hooks")
    hooks.seed_repair_sequences_per_company(env)
