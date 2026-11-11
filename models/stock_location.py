from odoo import fields, models


class StockLocation(models.Model):
    _inherit = "stock.location"

    usage = fields.Selection(
        selection_add=[("repair", "Repair")],
        ondelete={"repair": "set default"},
    )

    # v246 — port of the 8 Studio-manual x_studio_* fields on
    # stock.location. These drive repair-workflow domain filters
    # (Return Receipt Location dropdown, factory-repair validation,
    # user-scoped internal transfers) that Fix-repair's helpdesk_ticket
    # and stock_picking Python code reads via ilike/in on _uid.
    #
    # Field shapes and names taken verbatim from Clear-DB
    # ir.model.fields (all state='manual', modules='studio_customization'
    # there); on stand-alone the ORM creates them fresh at install.
    # On Clear-DB the migrator flips state='manual'->'base' and reassigns
    # ownership to Fix-repair — see _migrate_studio_stock_location_cluster.

    # Flags: mark a stock.location for a specific repair-flow role
    finished_good_location = fields.Boolean()
    repair_factory_location = fields.Boolean()
    repair_return_location = fields.Boolean()
    temp_location = fields.Boolean()

    # Chained locations used by the repair-flow picking routing
    return_receipt_location = fields.Many2one(
        "stock.location",
        ondelete="set null",
    )
    return_sequence = fields.Many2one(
        "ir.sequence",
        ondelete="set null",
    )

    # User-scope m2m — Fix-repair's helpdesk_ticket._get_view and
    # stock_picking domain filters read these via
    # ('users_stock_location', 'in', user_id) / ilike self._uid.
    users_stock_location = fields.Many2many(
        "res.users",
        relation="stock_location_users_stock_location_rel",
        column1="location_id",
        column2="user_id",
        string="Users (Stock Location)",
    )
    users_internal_transfer = fields.Many2many(
        "res.users",
        relation="stock_location_users_internal_transfer_rel",
        column1="location_id",
        column2="user_id",
        string="Users (Internal Transfer)",
    )

    # v276: third Studio-generated m2m to res.users. Cryptic name kept
    # verbatim to match Clear-DB. Distinct relation table from the two
    # above so writes on this field don't leak into stock/internal
    # transfer scopes. Purpose: additional per-user location scope
    # referenced by Studio view arch; no Python consumer today, but
    # declared so install-time view validation and future Studio arch
    # ports (Clear-DB upgrade) resolve cleanly.
    many2many_field_7kpUe = fields.Many2many(
        "res.users",
        relation="stock_location_users_scope_7kpue_rel",
        column1="location_id",
        column2="user_id",
        string="Users (Scope 7kpUe)",
    )
