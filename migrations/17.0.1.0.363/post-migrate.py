# -*- coding: utf-8 -*-
"""Fix-repair v17.0.1.0.363: seed ir.model.fields.selection rows via
Odoo's own _update_selection helper (framework API, not cr.execute).

Companion to _seed_field_selections in ../../hooks.py; this covers
version-upgrade path (post_init_hook covers fresh install).
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
    Sel = env['ir.model.fields.selection'].sudo()
    Fld = env['ir.model.fields'].sudo()
    grouped = {}
    for model, fname, value, label, seq in _FIELD_SELECTIONS:
        grouped.setdefault((model, fname), []).append((value, label, seq))
    for (model, fname), values in grouped.items():
        fld = Fld.search(
            [('model', '=', model), ('name', '=', fname)], limit=1,
        )
        if not fld:
            continue
        existing_recs = Sel.search(
            [('field_id', '=', fld.id)], order='sequence',
        )
        existing_pairs = [(r.value, r.name) for r in existing_recs]
        existing_values = {v for v, _ in existing_pairs}
        added = []
        for v, l, _seq in sorted(values, key=lambda t: t[2]):
            if v in existing_values:
                continue
            existing_pairs.append((v, l))
            existing_values.add(v)
            added.append(v)
        if not added:
            continue
        try:
            with cr.savepoint():
                Sel._update_selection(model, fname, existing_pairs)
                _logger.info(
                    "Fix-repair v17.0.1.0.363: seeded %s.%s += %s.",
                    model, fname, added,
                )
        except Exception as e:
            _logger.warning(
                "Fix-repair v17.0.1.0.363: seed failed %s.%s (%s).",
                model, fname, e,
            )
