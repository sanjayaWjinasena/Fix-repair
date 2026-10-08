# -*- coding: utf-8 -*-
"""v17.0.1.0.368: remove the hard-xpath "hide dev extras" views.

They are replaced by _get_view overrides (BugFix-Stock and Fix-repair
models/hide_dev_extras.py). When an app they target is not installed, the
views break the transfer / product / contact forms. They must be gone before
any view of this upgrade is validated, otherwise validation of a sibling
inherit view hits the same error. BugFix-Stock upgrades before Fix-repair, so
Fix-repair's two views are removed here too. ORM only.
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

BROKEN_VIEWS = (
    'BugFix-Stock.view_stock_picking_form_hide_dev_extras',
    'Fix-repair.view_product_template_form_hide_dev_extras',
    'Fix-repair.view_partner_form_hide_dev_extras',
)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    for xmlid in BROKEN_VIEWS:
        view = env.ref(xmlid, raise_if_not_found=False)
        if view:
            view.unlink()
            _logger.info("Fix-repair v368: removed view %s", xmlid)
