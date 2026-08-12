# -*- coding: utf-8 -*-
"""v242 post-migration — re-runs the post-init view loader with the
sanitised ported.xml (view #4013 removed, //button[@name='195']
xpath stripped from #4012). Existing DBs get the sanitised arch
applied via convert_file(mode='init'), which updates records in
place by external ID.
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
    hooks.load_post_init_view_files(env)
