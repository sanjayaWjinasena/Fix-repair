"""Drop the helpdesk.ticket views that this version re-parents, so they reload clean.

Why this exists
---------------
Up to .371 every Fix-repair helpdesk.ticket form view inherited helpdesk's own
form (``helpdesk.helpdesk_ticket_view_form``) directly, and the Studio fields
(``rug_repair``, ``rug_confirmed``, ``quick_repair_status`` ...) were injected
into that one shared arch.

The .372-.381 helpdesk-general-tickets port introduces an intermediate primary
view, ``Fix-repair.helpdesk_ticket_view_form_repair``, and moves the repair
views onto it, so repair tickets and general tickets stop sharing one arch.

An existing database cannot make that move while its data file loads. The views
are written one record at a time, and each write revalidates the whole
helpdesk.ticket inheritance tree. The moment
``view_helpdesk_ticket_form_inherit`` is re-parented onto the new primary view,
the Studio fields leave the base-form arch -- but the sibling views further
down the same file still carry their old ``inherit_id`` pointing at the base
form, and their xpaths go looking for fields that are no longer there:

    Element '<xpath expr="//field[@name='rug_repair']">' cannot be located
    in parent view

The sibling that fails (``helpdesk_ticket_form_hide_studio_fields``) is only
corrected later in the same file, which it never reaches.

Fix
---
Delete the affected view records before the data loads. Every one of them is
declared in full in views/helpdesk_ticket_views.xml with noupdate unset, so the
data load recreates each with the correct parent -- and because the stale rows
are gone, nothing dangles mid-load to fail validation.

Checked safe to delete: none is referenced by an act_window (``view_id`` or
``ir_act_window_view``), none is the parent of another view, and none is
noupdate-protected. These are view definitions owned by code, holding no user
data.

Idempotent: once the views are reloaded with the new parent they no longer
match the stale-parent condition, so a re-run deletes nothing.

Relation to migrations/17.0.1.0.372/pre-migrate.py
-------------------------------------------------
That script does the same removal, naming the same six views by their
pre-rename xmlids (``ported_view_helpdesk_ticket_form_4012``,
``view_4013_odoo_studio_helpdesk_ticket_form_button_e``, ...). It only runs for
a database below .372, so any database installed from the rename trial -- which
is already past it -- never got the fix and fails on upgrade. This is the same
gap that 17.0.1.0.386/post-migrate.py closes for the two 'post' steps, which it
re-runs explicitly; the 'pre' step was missed.

This script covers it from the other side, using the post-rename xmlids, and
guards on the parent instead of assuming the views are untouched. On a database
below .372 both run: .372 removes the views first and this one then finds
nothing to do.
"""

import logging

_logger = logging.getLogger(__name__)

MODULE = "Fix-repair"

# Views moved from helpdesk's own form onto Fix-repair.helpdesk_ticket_view_form_repair.
REPARENTED = (
    "view_helpdesk_ticket_form_inherit",
    "helpdesk_ticket_form_hide_studio_fields",
    "helpdesk_ticket_form_assign_to_me",
    "helpdesk_ticket_form_statusbar_readonly",
    "helpdesk_ticket_form_hide_fields",
    "view_helpdesk_ticket_form_button",
)

OLD_PARENT = "helpdesk.helpdesk_ticket_view_form"


def _old_parent_id(cr):
    module, name = OLD_PARENT.split(".")
    cr.execute(
        "SELECT res_id FROM ir_model_data "
        "WHERE module = %s AND name = %s AND model = 'ir.ui.view'",
        (module, name),
    )
    row = cr.fetchone()
    return row and row[0]


def migrate(cr, version):
    if not version:
        return

    parent_id = _old_parent_id(cr)
    if not parent_id:
        # helpdesk not installed, or its form is gone: nothing to re-parent.
        return

    # Only the rows still hanging off the old parent. Views already moved (or
    # created fresh) are left alone, which keeps a re-run a no-op.
    cr.execute(
        """
        SELECT d.id, d.name, v.id
          FROM ir_model_data d
          JOIN ir_ui_view v ON v.id = d.res_id
         WHERE d.module = %s
           AND d.model = 'ir.ui.view'
           AND d.name IN %s
           AND v.inherit_id = %s
        """,
        (MODULE, REPARENTED, parent_id),
    )
    rows = cr.fetchall()
    if not rows:
        return

    view_ids = tuple(view_id for _d, _n, view_id in rows)
    data_ids = tuple(data_id for data_id, _n, _v in rows)

    _logger.info(
        "Re-parenting onto %s.helpdesk_ticket_view_form_repair: dropping %s stale "
        "view(s) so the data load recreates them -- %s",
        MODULE,
        len(rows),
        ", ".join(f"{MODULE}.{name}" for _d, name, _v in rows),
    )

    cr.execute("DELETE FROM ir_ui_view WHERE id IN %s", (view_ids,))
    cr.execute("DELETE FROM ir_model_data WHERE id IN %s", (data_ids,))
