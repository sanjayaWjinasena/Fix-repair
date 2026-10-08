# Fix-repair — `stock.warehouse`

[← back to Functional_Documentation.md](../Functional_Documentation.md)

### `stock.warehouse` — Warehouse

*Extends a model created by `stock`.* Python: `models/stock_warehouse.py`.

Other repos that use this model: `account.analytic.account.bugfix_analytics_warehouse_id` (BugFix-Analytics)<br>`sale.order.line.x_studio_warehouse_id` (BugFix-Sales)<br>`server action BugFix-Sales.server_action_2096_rr_insufficient_transfer_inventory_details` (BugFix-Sales)<br>`server action BugFix-Sales.server_action_2162_proj_item_related_details_in_project_so` (BugFix-Sales)<br>`server action BugFix-Sales.server_action_2188_proj_create_pr_from_sales_quotation` (BugFix-Sales)<br>`stock.valuation.layer.x_studio_related_field_dGINH` (BugFix-Stock)<br>`window action BugFix-Stock.action_2468_warehouse` (BugFix-Stock)<br>`window action BugFix-Stock.action_2469_warehouse` (BugFix-Stock)<details><summary>+3 more</summary>`x_bve.salesreport.x_bve_t1_warehouse_id` (BugFix-Studio-Misc)<br>`x_consignment_line.x_studio_warehouse` (BugFix-Stock)<br>`x_material_request.x_studio_many2one_field_W3qKf` (BugFix-Stock)</details>

**Summary:**

<!-- SUMMARY:model:stock.warehouse -->
Adds helpers that create the repair locations: an Intransit (transit) and a Repair (repair-type) child location under every warehouse, created when the repair flow needs them and seeded at install. It also seeds the per-company Factory Repair Location setting (default `PW-JM` for Jinasena Agricultural Machinery). The repo also ships two Warehouse window actions, a Studio form customization on the warehouse view, and the "Stock data warehouse" rule for inventory administrators.
<!-- /SUMMARY -->

**Python methods (6):**

| Method | Function | Decorators | Extends standard | Depends on | Used by | Where |
|---|---|---|---|---|---|---|
| `_ensure_child_location` | Helper that returns the warehouse's child location with the given name under its view location, creating it with the given usage and the warehouse's company if missing. |  |  | `model stock.location` (stock)<br>`res.company.id` (base)<br>`stock.warehouse.company_id` (stock)<br>`stock.warehouse.view_location_id` (stock) | `stock.warehouse._ensure_intransit_location()`<br>`stock.warehouse._ensure_repair_location()` | `models/stock_warehouse.py:17` |
| `_ensure_intransit_location` | Returns the warehouse's 'Intransit' transit location, creating it if missing. |  |  | `stock.warehouse._ensure_child_location()` | `stock.warehouse._seed_intransit_locations()` | `models/stock_warehouse.py:41` |
| `_ensure_repair_location` | Returns the warehouse's 'Repair' location (usage repair), creating it if missing. |  |  | `stock.warehouse._ensure_child_location()` | `stock.warehouse._seed_repair_locations()` | `models/stock_warehouse.py:44` |
| `_seed_intransit_locations` | Setup helper: ensures every warehouse (except codes starting IT-, IW-, IB-) has an 'Intransit' transit location. Idempotent. | api.model |  | `stock.warehouse._ensure_intransit_location()` |  | `models/stock_warehouse.py:48` |
| `_seed_repair_locations` | Setup helper: ensures every warehouse (except codes starting IT-, IW-, IB-) has a 'Repair' location. Idempotent. | api.model |  | `stock.warehouse._ensure_repair_location()` |  | `models/stock_warehouse.py:59` |
| `_seed_factory_repair_locations` | Setup helper: for each company matched to a default factory warehouse code, stores that warehouse's stock location as the per-company Factory Repair Location system parameter, unless one is already set. | api.model |  | `model ir.config_parameter` (base)<br>`model res.company` (base)<br>`model stock.warehouse` (stock) |  | `models/stock_warehouse.py:70` |

**Window actions (2):**

| Name | Record name | Function | Depends on | Used by |
|---|---|---|---|---|
| WareHouse | `act_window_2468_warehouse` | Opens **Warehouse** records (tree,form). | `model stock.warehouse` (stock) |  |
| Warehouse | `act_window_2469_warehouse` | Opens **Warehouse** records (tree,form). | `model stock.warehouse` (stock) |  |

**Views (1):**

| Name | Record name | Type | What it changes | Function | Depends on | Used by |
|---|---|---|---|---|---|---|
| Odoo Studio: stock.warehouse customization | `view_5484_odoo_studio_stock_warehouse_customization_e` | form | set readonly= on `//field[@name='lot_stock_id']` | Warehouse form: clears the read-only setting on the Location Stock field, making it editable. | `view stock.view_warehouse` (stock) |  |

**Record rules (1):**

| Name | Record name | Function | Depends on | Used by |
|---|---|---|---|---|
| Stock data warehouse | `rule_921_stock_data_warehouse` | For Inventory / Administrator: read/write/create/delete on Warehouse with no record filter (empty domain = all records). | `group stock.group_stock_manager` (stock)<br>`model stock.warehouse` (stock) |  |
