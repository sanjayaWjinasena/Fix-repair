# -*- coding: utf-8 -*-
from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _get_report(self, report_ref):
        if report_ref == 'sale.action_report_saleorder':
            try:
                return super()._get_report(report_ref)
            except ValueError:
                # The standard sale.action_report_saleorder XML ID is missing —
                # this happens when Studio replaces the standard report and the
                # ir.model.data record is lost. Fall back to the first available
                # qweb-pdf report for sale.order so the portal accept flow works.
                fallback = self.sudo().search(
                    [('model', '=', 'sale.order'), ('report_type', '=', 'qweb-pdf')],
                    order='sequence asc, id asc',
                    limit=1,
                )
                if fallback:
                    return fallback
        return super()._get_report(report_ref)
