"""v374: give a number to what was created while the repair sequences were missing.

Before v373 a database set up from this branch had no repair.seq / repair.serial.seq, so tickets kept the
name 'New', and so did their field service tasks and the repair serials they created. This renames them:
tickets via hooks.assign_names_to_stale_new_tickets (their own company's REPAIR/<year>/ number), then each
renamed ticket's tasks still named 'New' get the ticket's name, and its repair serial still named 'New'
gets the company's next REP-SERIAL/<year>/ number. Nothing else is changed; no-op where nothing is 'New'.
"""
import importlib
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    Ticket = env["helpdesk.ticket"].sudo().with_context(active_test=False)
    stale = Ticket.search(["|", ("name", "=", "New"), ("name", "=", False)])
    if not stale:
        return
    hooks = importlib.import_module("odoo.addons.Fix-repair.hooks")
    hooks.assign_names_to_stale_new_tickets(env)
    renamed = stale.filtered(lambda t: t.name and t.name != "New")
    tasks = lots = 0
    for ticket in renamed:
        for task in ticket.fsm_task_ids.filtered(lambda t: t.name in ("New", False)):
            task.name = ticket.name
            tasks += 1
        lot = ticket.serial_no if "serial_no" in ticket._fields else ticket.lot_id
        if ticket.repair_serial_created and lot and lot.name == "New":
            seq = env["ir.sequence"].sudo().with_company(ticket.company_id).next_by_code("repair.serial.seq")
            if seq:
                lot.name = seq
                lots += 1
    _logger.info("Fix-repair v374: %d tickets renamed, %d tasks, %d repair serials", len(renamed), tasks, lots)
