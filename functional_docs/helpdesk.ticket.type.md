# Fix-repair — `helpdesk.ticket.type`

[← back to Functional_Documentation.md](../Functional_Documentation.md)

### `helpdesk.ticket.type` — Helpdesk Ticket Type

*Extends a model created by `helpdesk`.* Python: `models/helpdesk_type_stage.py`.

Other repos that use this model: `x_test02.x_studio_types` (BugFix-Studio-Misc)

**Summary:**

<!-- SUMMARY:model:helpdesk.ticket.type -->
Adds four repair-configuration checkboxes to ticket types: RUG (`x_studio_rug`), RUG Confirmed (`x_studio_rug_confirmed`), With Serial No (`x_studio_with_serial_no`) and Without Serial No (`x_studio_without_serial_no`). They appear on the ticket type form and list. The ticket logic reads them to decide the repair path (warranty/RUG, with or without serial number). `_migrate_studio_ticket_type_cluster_to_base` moves these fields from Studio to this module, keeping their data.
<!-- /SUMMARY -->

**Fields (4):**

| Field | Label | Type | Function | How it gets its value | Depends on | Used by |
|---|---|---|---|---|---|---|
| `x_studio_rug` | RUG | boolean | Marks the ticket type as Repair Under Guarantee (warranty); copied to tickets as Repair Under Warranty and shown in the ticket type form and list. | stored |  | `helpdesk.ticket.x_studio_rug_repair`<br>`view Fix-repair.helpdesk_ticket_type_view_form_repair_config`<br>`view Fix-repair.helpdesk_ticket_type_view_tree_repair_config`<br>`view Fix-repair.view_4610_odoo_studio_helpdesk_ticket_type_tree_customization_e` |
| `x_studio_rug_confirmed` | RUG Confirmed | boolean | Marks the ticket type as RUG Confirmed; copied to tickets of this type and shown in the ticket type form and list. | stored |  | `helpdesk.ticket.x_studio_rug_confirmed`<br>`view Fix-repair.helpdesk_ticket_type_view_form_repair_config`<br>`view Fix-repair.helpdesk_ticket_type_view_tree_repair_config`<br>`view Fix-repair.view_4610_odoo_studio_helpdesk_ticket_type_tree_customization_e` |
| `x_studio_with_serial_no` | With Serial No | boolean | Marks the ticket type as a normal repair for items with a serial number; copied to tickets and shown in the ticket type form and list. | stored |  | `helpdesk.ticket.x_studio_normal_repair_with_serial_no`<br>`view Fix-repair.helpdesk_ticket_type_view_form_repair_config`<br>`view Fix-repair.helpdesk_ticket_type_view_tree_repair_config`<br>`view Fix-repair.view_4610_odoo_studio_helpdesk_ticket_type_tree_customization_e` |
| `x_studio_without_serial_no` | Without Serial No | boolean | Marks the ticket type as a normal repair for items without a serial number; copied to tickets and shown in the ticket type form and list. | stored |  | `helpdesk.ticket.x_studio_normal_repair_without_serial_no`<br>`view Fix-repair.helpdesk_ticket_type_view_form_repair_config`<br>`view Fix-repair.helpdesk_ticket_type_view_tree_repair_config`<br>`view Fix-repair.view_4610_odoo_studio_helpdesk_ticket_type_tree_customization_e` |

**Python methods (1):**

| Method | Function | Decorators | Extends standard | Depends on | Used by | Where |
|---|---|---|---|---|---|---|
| `_migrate_studio_ticket_type_cluster_to_base` | One-off migration helper: makes the four Studio fields on Ticket Type (RUG, RUG Confirmed, With/Without Serial No) code-owned and removes their Studio external ids. Data kept. | api.model |  | `model ir.model.data` (base)<br>`model ir.model.fields` (base) |  | `models/helpdesk_type_stage.py:23` |

**Views (3):**

| Name | Record name | Type | What it changes | Function | Depends on | Used by |
|---|---|---|---|---|---|---|
| Odoo Studio: helpdesk.ticket.type.tree customization | `view_4610_odoo_studio_helpdesk_ticket_type_tree_customization_e` | tree | after `//tree[1]/field[@name='name']`: add field x_studio_rug, field x_studio_rug_confirmed, field x_studio_with_serial_no, field x_studio_without_serial_no, field id | Ticket Type list: adds RUG, RUG Confirmed, With Serial No, Without Serial No and a hidden ID column after the name. | `helpdesk.ticket.type.x_studio_rug_confirmed`<br>`helpdesk.ticket.type.x_studio_rug`<br>`helpdesk.ticket.type.x_studio_with_serial_no`<br>`helpdesk.ticket.type.x_studio_without_serial_no`<br>`view helpdesk.helpdesk_ticket_type_view_tree` (helpdesk) |  |
| helpdesk.ticket.type.form.repair.config | `helpdesk_ticket_type_view_form_repair_config` | form | after `//field[@name='name']`: add field x_studio_rug, field x_studio_rug_confirmed, field x_studio_with_serial_no, field x_studio_without_serial_no | Ticket Type form: adds RUG, RUG Confirmed, With Serial No and Without Serial No checkboxes after the name. | `helpdesk.ticket.type.x_studio_rug_confirmed`<br>`helpdesk.ticket.type.x_studio_rug`<br>`helpdesk.ticket.type.x_studio_with_serial_no`<br>`helpdesk.ticket.type.x_studio_without_serial_no`<br>`view helpdesk.helpdesk_ticket_type_view_form` (helpdesk) |  |
| helpdesk.ticket.type.tree.repair.config | `helpdesk_ticket_type_view_tree_repair_config` | tree | after `//tree[1]/field[@name='name']`: add field x_studio_rug, field x_studio_rug_confirmed, field x_studio_with_serial_no, field x_studio_without_serial_no | Ticket Type list: adds RUG, RUG Confirmed, With Serial No and Without Serial No columns after the name. | `helpdesk.ticket.type.x_studio_rug_confirmed`<br>`helpdesk.ticket.type.x_studio_rug`<br>`helpdesk.ticket.type.x_studio_with_serial_no`<br>`helpdesk.ticket.type.x_studio_without_serial_no`<br>`view helpdesk.helpdesk_ticket_type_view_tree` (helpdesk) |  |
