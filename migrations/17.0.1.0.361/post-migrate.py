# -*- coding: utf-8 -*-
"""Fix-repair v17.0.1.0.361: seed ir.model.fields.selection rows via ORM.

Same content as post_init_hook in ../hooks.py; this covers the version-upgrade
path (post-migrate runs on upgrade; hooks.py runs on fresh install). Uses the
ORM (no direct SQL) per the project's no-direct-SQL rule.

Idempotent: skips rows whose (field_id, value) already exists.
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

_FIELD_SELECTIONS = [
    ('helpdesk.ticket', 'x_studio_tracking', 'serial', 'By Unique Serial Number', 10),
    ('helpdesk.ticket', 'x_studio_tracking', 'lot', 'By Lots', 1),
    ('helpdesk.ticket', 'x_studio_tracking', 'none', 'No Tracking', 2),
]


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    Fld = env['ir.model.fields']
    Sel = env['ir.model.fields.selection']
    for model, fname, value, label, seq in _FIELD_SELECTIONS:
        fld = Fld.search(
            [('model', '=', model), ('name', '=', fname)], limit=1,
        )
        if not fld:
            continue
        exists = Sel.search(
            [('field_id', '=', fld.id), ('value', '=', value)], limit=1,
        )
        if exists:
            continue
        try:
            with cr.savepoint():
                Sel.create({
                    'field_id': fld.id, 'value': value,
                    'name': label, 'sequence': seq,
                })
        except Exception as e:
            _logger.warning(
                "Fix-repair v17.0.1.0.361: seed failed %s.%s=%r (%s).",
                model, fname, value, e,
            )
