# -*- coding: utf-8 -*-
"""v1.0.372 (pre): move the Fix-repair ticket form customizations in one step.

v1.0.372 makes these six views inherit from the new Repair ticket form instead of Odoo's
standard ticket form. Updated one by one during the upgrade, the first one moved
(ported_view_helpdesk_ticket_form_4012, which adds the x_studio fields) leaves the ones not
yet moved (helpdesk_ticket_form_hide_studio_fields anchors on those fields) on the standard
form without their anchors, and view validation fails. Removing the six views first lets the
upgrade re-create them from the XML directly on the Repair form. Their content is unchanged.
ORM only; no-op on fresh installs and when the views are already gone.
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

MODULE = 'Fix-repair'
VIEWS = (
    'ported_view_helpdesk_ticket_form_4012',
    'helpdesk_ticket_form_hide_studio_fields',
    'helpdesk_ticket_form_assign_to_me',
    'helpdesk_ticket_form_statusbar_readonly',
    'helpdesk_ticket_form_hide_fields',
    'view_4013_odoo_studio_helpdesk_ticket_form_button_e',
)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    imd = env['ir.model.data'].sudo().search([
        ('module', '=', MODULE), ('model', '=', 'ir.ui.view'), ('name', 'in', VIEWS)])
    views = env['ir.ui.view'].sudo().with_context(active_test=False).browse(imd.mapped('res_id')).exists()
    if views:
        names = imd.mapped('name')
        views.unlink()
        imd.exists().unlink()
        _logger.info('%s: removed %s ticket form views to re-create them on the Repair form: %s',
                     MODULE, len(views), names)
