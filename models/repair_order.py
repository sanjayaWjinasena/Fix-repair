# -*- coding: utf-8 -*-
"""repair.order Studio-field port (v299).

Clear-DB has a single Studio-created `x_studio_confirm_draft_quotation`
boolean on the stock `repair.order` model. This file ports it so
`ir.model.fields` on a fresh install matches Clear-DB verbatim
(state='base' after this module loads).

No compute, no default, no help — matches Clear-DB exactly (a plain
boolean flag). Studio pinned it via ir.model.data.module='studio_customization';
declaring it here in Python takes ownership and the eventual migration
step to unlink the studio_customization pin can follow the same
pattern as the other repair.* clusters (see MIGRATION.md v145).
"""
from odoo import fields, models


class RepairOrder(models.Model):
    _inherit = 'repair.order'

    x_studio_confirm_draft_quotation = fields.Boolean(
        string='Confirm Draft Quotation',
    )
