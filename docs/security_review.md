# Security review: privileged writes (sudo) in Fix-repair

Branch `Refactor-Security`. OWASP A01 (access control) and ISO/IEC 5055
(reliability). Reviewed the places where Fix-repair writes with `sudo()`,
i.e. bypassing the current user's access rights.

## Kept, by design (cross-application workflow)

The user acts on a record they have rights to; the module then updates a
*related* record in another application the user may not have rights to.
The user-facing entry point is checked by Odoo's normal access rules.

| Method | Writes with sudo | Reached from | Why sudo |
|---|---|---|---|
| `helpdesk_ticket.action_change_to_rug` | ticket type | button on the ticket | access to the ticket is checked first (`check_access_rights` / `check_access_rule`) |
| `helpdesk_ticket.action_create_repair_serial` | `stock.lot` | button on the ticket | users without inventory rights; ticket access checked first |
| `helpdesk_ticket._move_to_stage` | ticket stage | repair workflow buttons on the ticket | stage changes for repair staff with limited ticket rights |
| `sale_order._move_ticket_to_stage` | linked ticket stage | `action_quotation_send`, `action_confirm`, `write` on the sale order | salespeople usually have no helpdesk write rights |
| `project_task._sync_repair_flags` | linked sale order flags | `write` / `_fsm_ensure_sale_order` on the task | field-service technicians usually have no sales write rights |
| `stock_return_picking._create_returns` | new return picking, ticket link | return wizard | rename/stamp the picking the user just created |

## Needs a decision (data integrity, not access)

These write `state = "done"` directly on stock moves and pickings, which
skips Odoo's validation (`_action_done`): no stock quantities (quants) or
valuation entries are created for those moves.

| Method | What it does |
|---|---|
| `helpdesk_ticket._create_repair_transfer` | creates the repair transfer and sets its move and picking to `done` |
| `stock_return_picking.default_get` | creates a "fake" picking/move and sets them to `done` so the return wizard has a source |

If these transfers are only meant as a tracking trail, document that on
the picking type. If stock levels must follow the item, replace the direct
state write with the standard validation (`picking.button_validate()` /
`move._action_done()`).

## Logic bugs found (not changed)

In Odoo 17 a record compared with `False` is never equal, so these
conditions are always True (`!= False`) or always False (`== True`).
Changing them changes behaviour, so they need a functional decision:

- `models/project_task.py`: `rec.sale_order_id != False` (5 places): always True
- `models/helpdesk_ticket.py`: `invoices.sale_order_id != False`: always True
- `models/helpdesk_ticket.py`: `rec.x_studio_sale_order == True`: always False

The intended check is almost certainly `if rec.sale_order_id:`.
