# -*- coding: utf-8 -*-
"""sale.order.line repair-flow overrides.

v279: port of Studio automation 193 / server action 2144
'RR - Sales Price For RUG Items'.

Clear-DB code:
    if record.x_studio_quotation_type == 'Repair':
      original_price = record.price_unit
      if record.x_studio_rug_confirmed == True:
        record.write({'price_unit': record.product_template_id.standard_price,
                      'x_studio_price_unit_original': original_price})

Fires on every sale.order.line create + write. When the parent SO is
a Repair quotation AND rug_confirmed is True on the header, resets
the line's price_unit to the product's standard cost and captures the
previous price in x_studio_price_unit_original (audit trail for the
customer-facing quote before RUG locked it).

Fix-repair's sale_order.py already resets prices when the HEADER
x_studio_rug_approved flips True (a later stage). This line-side
override catches the earlier trigger (rug_confirmed) AND handles
lines added AFTER rug_confirmed — the header-side write() only fires
when the flag flips, not on subsequent line adds.

Fields x_studio_quotation_type / x_studio_rug_confirmed live on the
parent sale.order (declared in BugFix-Sales), not on the line — the
override navigates via record.order_id. x_studio_price_unit_original
is declared on sale.order.line by BugFix-Sales v43.
"""
from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _fix_repair_maybe_reprice_rug_line(self):
        """Studio automation 193 port. Reset price to product cost on
        RUG-confirmed repair lines, capture original in
        x_studio_price_unit_original.

        Idempotent guards:
          - only fires for Repair-type SOs
          - only fires when parent's rug_confirmed is True
          - only fires when price_unit differs from product standard
            cost (avoids infinite recursion via write())
        """
        for line in self:
            order = line.order_id
            if not order:
                continue
            if order.x_studio_quotation_type != 'Repair':
                continue
            if not getattr(order, 'x_studio_rug_confirmed', False):
                continue
            product = line.product_template_id
            if not product:
                continue
            target_price = product.standard_price
            if line.price_unit == target_price:
                continue
            line.with_context(_fix_repair_rug_reprice=True).write({
                'price_unit': target_price,
                'x_studio_price_unit_original': line.price_unit,
            })

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        # Skip when a parent recursion is already in flight.
        if not self.env.context.get('_fix_repair_rug_reprice'):
            lines._fix_repair_maybe_reprice_rug_line()
        return lines

    def write(self, vals):
        res = super().write(vals)
        # Skip when we're the ones firing the write (recursion guard).
        if self.env.context.get('_fix_repair_rug_reprice'):
            return res
        # Only re-evaluate when a relevant field changed. product_uom_qty
        # doesn't affect price, so skipping saves cycles on qty edits.
        triggers = {'price_unit', 'product_id', 'product_template_id'}
        if not (triggers & set(vals or ())):
            return res
        self._fix_repair_maybe_reprice_rug_line()
        return res
