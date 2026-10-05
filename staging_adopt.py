# -*- coding: utf-8 -*-
"""Staging_Migration: adopt existing models for this module's ir.model pins.

On a database that still carries the Studio customizations (an Odoo.sh
staging copy of production), the custom models this module ships already
exist as Studio models. The pin file (data/ir_model_pins.xml) then tries to CREATE them
and fails:
    duplicate key value violates unique constraint "ir_model_obj_name_uniq"

pre_init_hook runs before this module's data loads. For each pin whose
model already exists, it registers this module's xmlid on that ir.model
row, so the pin finds it instead of creating a duplicate. Nothing else is
written. Pins whose model does not exist yet are created as usual, and on
a fresh database nothing matches, so this is a no-op there.

Lives on the Staging_Migration branch only. ORM only.
"""
import logging
import os

from lxml import etree

_logger = logging.getLogger(__name__)

MODULE = 'Fix-repair'
PINS = os.path.join(os.path.dirname(os.path.abspath(__file__)), *'data/ir_model_pins.xml'.split('/'))


def pre_init_hook(env):
    IrModel = env['ir.model'].sudo()
    IMD = env['ir.model.data'].sudo()
    adopted = 0
    for rec in etree.parse(PINS).iter('record'):
        if rec.get('model') != 'ir.model':
            continue
        xmlid = rec.get('id')
        model_name = rec.find("field[@name='model']").text
        if IMD.search_count([('module', '=', MODULE), ('name', '=', xmlid)]):
            continue
        model = IrModel.search([('model', '=', model_name)], limit=1)
        if not model:
            continue
        IMD.create({'module': MODULE, 'name': xmlid, 'model': 'ir.model', 'res_id': model.id, 'noupdate': True})
        adopted += 1
    _logger.info("%s pre_init_hook: adopted %d existing models for ir.model pins", MODULE, adopted)
