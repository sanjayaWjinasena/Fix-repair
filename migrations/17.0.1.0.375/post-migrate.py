# -*- coding: utf-8 -*-
"""v1.0.375: the general Helpdesk stages are shared by all companies.

Created by v1.0.373, they were stamped with the installing company (Jinasena (Pvt) Ltd), so
the helpdesk.stage company rule hid them from JAM and a JAM general team showed no stages.
Clear their company. ORM only; no-op when the stages are missing.
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

STAGES = ('new', 'in_progress', 'on_hold', 'solved', 'cancelled')


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    stages = env['helpdesk.stage']
    for name in STAGES:
        stages |= env.ref('Fix-repair.helpdesk_stage_general_%s' % name, raise_if_not_found=False) or env['helpdesk.stage']
    stages = stages.filtered('x_studio_company_id')
    stages.write({'x_studio_company_id': False})
    _logger.info('Fix-repair: %s general helpdesk stages shared by all companies', len(stages))
