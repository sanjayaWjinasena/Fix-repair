# -*- coding: utf-8 -*-
"""v17.0.1.0.366: the 7 sale.order Studio check fields are now real computed
fields (models/studio_computes.py). Their columns already exist, so Odoo does
not fill them by itself: recompute every sales order once. ORM only."""
import importlib
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    mod = importlib.import_module('odoo.addons.Fix-repair.models.studio_computes')
    count = mod.recompute_stored_studio_computes(env)
    _logger.info("Fix-repair v366: recomputed Studio check fields on %d sales orders", count)
