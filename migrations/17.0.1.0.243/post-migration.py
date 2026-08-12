# -*- coding: utf-8 -*-
"""v243 post-migration — attach the 12 newly-seeded repair-pipeline
helpdesk.stage records to every existing helpdesk.team so they show
up on ticket statusbars. The stages themselves are created by
data/repair_stages.xml during the normal upgrade load; this script
just finishes the team wiring for existing DBs where post_init_hook
doesn't fire (post_init_hook is install-only).

Idempotent — the underlying function re-attaches only teams that
aren't already in the stage's team_ids m2m.
"""
import importlib.util
import os

from odoo import api, SUPERUSER_ID
from odoo.modules.module import get_module_path


def migrate(cr, version):
    if not version:
        return
    hooks_path = os.path.join(get_module_path('Fix-repair'), 'hooks.py')
    spec = importlib.util.spec_from_file_location(
        'fix_repair_hooks', hooks_path,
    )
    hooks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hooks)
    env = api.Environment(cr, SUPERUSER_ID, {})
    hooks.attach_repair_stages_to_all_teams(env)
