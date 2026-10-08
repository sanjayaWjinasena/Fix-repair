# Fix-repair — `stock.lot`

[← back to Functional_Documentation.md](../Functional_Documentation.md)

### `stock.lot` — Lot/Serial

*Extends a model created by `stock`.* Python: `models/stock_lot.py`.

Other repos that use this model: `access right BugFix-Stock.access_6087_user` (BugFix-Stock)<br>`access right BugFix-Stock.access_7201_administrator` (BugFix-Stock)<br>`access right BugFix-Stock.access_7202_jin___administrator` (BugFix-Stock)<br>`record rule BugFix-Stock.rule_47_stock_production_lot_multi_company` (BugFix-Stock)<br>`server action BugFix-MRP.sa_f5_x_mass_produce_serial_mass_produce_serial_nos_find_last` (BugFix-MRP)<br>`server action BugFix-MRP.server_action_1151_mass_produce_serial_numbers_create_original` (BugFix-MRP)<br>`server action BugFix-MRP.server_action_1153_mass_produce_serial_nos_find_last` (BugFix-MRP)<br>`server action BugFix-MRP.server_action_3202_mass_produce_serial_numbers_cancel_serial_no` (BugFix-MRP)<details><summary>+5 more</summary>`window action BugFix-Stock.act_window_2225_inventory_holding_days` (BugFix-Stock)<br>`window action BugFix-Stock.action_2225_inventory_holding_days` (BugFix-Stock)<br>`window action BugFix-Stock.aw_f4_stock_lot_inventory_holding_days` (BugFix-Stock)<br>`x_mass_produce_serial.x_studio_last_serial_no_id` (BugFix-MRP)<br>`x_mass_produce_serial_.x_studio_lot_serial_id` (BugFix-MRP)</details>

**Summary:**

<!-- SUMMARY:model:stock.lot -->
Adds Is Issued (`is_issued`), a non-stored, searchable flag that is true when the serial/lot has a completed outgoing move line on a sales order delivery. The helpdesk ticket uses it to limit the serial number dropdown to serials already delivered to customers.
<!-- /SUMMARY -->

**Fields (1):**

| Field | Label | Type | Function | How it gets its value | Depends on | Used by |
|---|---|---|---|---|---|---|
| `is_issued` | Is Issued | boolean | Computed: true when the serial/lot has a done move line on a transfer linked to a sales order, i.e. it was already issued to a customer. | computed by `_compute_is_issued`; not stored | `stock.lot._compute_is_issued()`<br>`stock.lot._search_is_issued()` |  |

**Python methods (2):**

| Method | Function | Decorators | Extends standard | Depends on | Used by | Where |
|---|---|---|---|---|---|---|
| `_compute_is_issued` | Compute of Is Issued on lots/serials: True when the lot appears on a done stock move line of a picking linked to a sale order. |  |  | `model stock.move.line` (stock) | `stock.lot.is_issued` | `models/stock_lot.py:15` |
| `_search_is_issued` | Search method for Is Issued, so lots can be filtered by whether they were issued through a sale order delivery. |  |  | `model stock.move.line` (stock) | `stock.lot.is_issued` | `models/stock_lot.py:26` |
