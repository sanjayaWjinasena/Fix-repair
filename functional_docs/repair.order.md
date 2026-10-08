# Fix-repair — `repair.order`

[← back to Functional_Documentation.md](../Functional_Documentation.md)

### `repair.order` — Repair Order

*Extends a model created by `repair`.* Python: `models/repair_order.py`.

Other repos that use this model: `report BugFix-Studio-Misc.action_report_3447_template_c09_repair_receipt` (BugFix-Studio-Misc)<br>`report BugFix-Studio-Misc.action_report_3448_template_c10_repair_estimate` (BugFix-Studio-Misc)<br>`report BugFix-Studio-Misc.action_report_3451_template_c11_repair_quotation` (BugFix-Studio-Misc)<br>`report BugFix-Studio-Misc.action_report_3452_template_c12_repair_invoice` (BugFix-Studio-Misc)<br>`report BugFix-Studio-Misc.action_report_3453_template_c13_repair_aod` (BugFix-Studio-Misc)<br>`report BugFix-Studio-Misc.action_report_3457_template_c14_ready_for_collection_letter` (BugFix-Studio-Misc)<br>`report BugFix-Studio-Misc.action_report_3458_template_c15_final_notice` (BugFix-Studio-Misc)<br>`report BugFix-Studio-Misc.action_report_3463_template_c16_final_notice_estimated` (BugFix-Studio-Misc)<details><summary>+4 more</summary>`report BugFix-Studio-Misc.action_report_3464_template_c17_final_notice_scrappage` (BugFix-Studio-Misc)<br>`report BugFix-Studio-Misc.action_report_3465_template_c18_final_notice_estimated_scrappage` (BugFix-Studio-Misc)<br>`report BugFix-Studio-Misc.action_report_3466_template_c19_reminder_repair_reminding_letter` (BugFix-Studio-Misc)<br>`server action BugFix-Studio-Misc.server_action_2799_mst_odoo_data_clean_up` (BugFix-Studio-Misc)</details>

**Summary:**

<!-- SUMMARY:model:repair.order -->
Adds one checkbox, Confirm Draft Quotation (`x_studio_confirm_draft_quotation`), which is shown on the repair order form. The ported Studio form customization hides the standard Validate button unless the order is in draft. The repo also ships the Studio server actions "RR - Add Draft Quotation Confirm Button", "RR - Update SO in RO" and "RR - Notify Customer in RO End - Final" (with its -2 variant), plus the automation that creates a "Repair Completed Confirmation" activity, two repair.order window actions and the multi-company record rule.
<!-- /SUMMARY -->

**Fields (1):**

| Field | Label | Type | Function | How it gets its value | Depends on | Used by |
|---|---|---|---|---|---|---|
| `x_studio_confirm_draft_quotation` | Confirm Draft Quotation | boolean | Flag on the repair order used by the 'Add Draft Quotation Confirm Button' server action and the repair form customizations to control the draft quotation confirm button. | stored |  | `server action Fix-repair.server_action_1814_rr_add_draft_quotation_confirm_button`<br>`view Fix-repair.view_4014_odoo_studio_repair_form_customization_e`<br>`view Fix-repair.view_4015_odoo_studio_repair_form_customization_button_e` |

**Server actions (5):**

- **Create activity: Repair Completed Confirmation.** (`server_action_1817_rr_notify_customer_in_ro_end_final`, type `next_activity`)
  - Function: Schedules a 'Repair Completed Confirmation' activity on the repair order; no code. Triggered by the automation 'RR - Notify Customer in RO End - Final'.
  - Depends on: `model repair.order` (repair)
  - Used by: `automation Fix-repair.base_automation_149_rr_notify_customer_in_ro_end_final`
  <details><summary>code (11 lines)</summary>

```python

# Available variables:
#  - env: Odoo Environment on which the action is triggered
#  - model: Odoo Model of the record on which the action is triggered; is a void recordset
#  - record: record on which the action is triggered; may be void
#  - records: recordset of all records on which the action is triggered in multi-mode; may be void
#  - time, datetime, dateutil, timezone: useful Python libraries
#  - float_compare: Odoo function to compare floats based on specific precisions
#  - log: log(message, level='info'): logging function to record debug information in ir.logging table
#  - UserError: Warning Exception to use with raise
# To return an action, assign: action = {...}
```
  </details>
- **RR - Add Draft Quotation Confirm Button** (`server_action_1814_rr_add_draft_quotation_confirm_button`, type `code`)
  - Function: Ticks Confirm Draft Quotation on the repair order.
  - Depends on: `model repair.order` (repair), `repair.order.x_studio_confirm_draft_quotation`
  - Used by: — (not linked to a button, menu or automation)
  <details><summary>code (2 lines)</summary>

```python
if record.id:
  record['x_studio_confirm_draft_quotation'] = True
```
  </details>
- **RR - Notify Customer in RO End - Final** (`sa_f5_repair_order_rr_notify_customer_in_ro_end_final`, type `next_activity`)
  - Function: Schedules an activity on the repair order (next-activity action); it contains no code, the activity details are set on the action record.
  - Depends on: `model repair.order` (repair)
  - Used by: — (not linked to a button, menu or automation)
  <details><summary>code (12 lines)</summary>

```python
# Available variables:
#  - env: environment on which the action is triggered
#  - model: model of the record on which the action is triggered; is a void recordset
#  - record: record on which the action is triggered; may be void
#  - records: recordset of all records on which the action is triggered in multi-mode; may be void
#  - time, datetime, dateutil, timezone: useful Python libraries
#  - float_compare: utility function to compare floats based on specific precision
#  - log: log(message, level='info'): logging function to record debug information in ir.logging table
#  - _logger: _logger.info(message): logger to emit messages in server logs
#  - UserError: exception class for raising user-facing warning messages
#  - Command: x2many commands namespace
# To return an action, assign: action = {...}
```
  </details>
- **RR - Notify Customer in RO End - Final - 2** (`server_action_1820_rr_notify_customer_in_ro_end_final_2`, type `code`)
  - Function: Creates and sends an email 'Repair Complete Confirmation' to a fixed address (janitharc@gmail.com) regardless of the repair order's customer.
  - Depends on: `model mail.mail` (mail), `model repair.order` (repair)
  - Used by: — (not linked to a button, menu or automation)
  <details><summary>code (19 lines)</summary>

```python

mail_pool = env['mail.mail']

values={}

values.update({'subject': 'Repair Complete Confirmation'})

values.update({'email_to': 'janitharc@gmail.com'})

values.update({'body_html': 'Repair Complete Confirmation' })

values.update({'body': 'Repair Complete Confirmation' })

msg_id = mail_pool.create(values)

# And then call send function of the mail.mail,

if msg_id:
  mail_pool.send([msg_id])
```
  </details>
- **RR - Update SO in RO** (`server_action_1979_rr_update_so_in_ro`, type `code`)
  - Function: Copies the sale order of the repair order's helpdesk ticket onto the repair order.
  - Depends on: `model repair.order` (repair), `repair.order.ticket_id` (helpdesk_repair)
  - Used by: — (not linked to a button, menu or automation)
  <details><summary>code (2 lines)</summary>

```python
if record.ticket_id.id:
  record['sale_order_id'] = record.ticket_id.sale_order_id.id
```
  </details>
**Automations (1):**

| Name | Record name | State | Function | Depends on | Used by |
|---|---|---|---|---|---|
| RR - Notify Customer in RO End - Final | `base_automation_149_rr_notify_customer_in_ro_end_final` |  | When a record is created or updated on Repair Order, runs _Create activity: Repair Completed Confirmation._. | `model repair.order` (repair)<br>`server action Fix-repair.server_action_1817_rr_notify_customer_in_ro_end_final` |  |

**Window actions (2):**

| Name | Record name | Function | Depends on | Used by |
|---|---|---|---|---|
| repair.order | `aw_f4_repair_order_repair_order` | Opens **Repair Order** records (kanban,tree,form,pivot,graph). | `model repair.order` (repair) |  |
| repair.order | `act_window_2807_repair_order` | Opens **Repair Order** records (kanban,tree,form,pivot,graph). | `model repair.order` (repair) | `menu BugFix-Studio-Misc.menu_f6r2_test_app_05_repair_order` (BugFix-Studio-Misc) |

**Views (2):**

| Name | Record name | Type | What it changes | Function | Depends on | Used by |
|---|---|---|---|---|---|---|
| Odoo Studio: repair.form customization | `view_4014_odoo_studio_repair_form_customization_e` | form | after `//field[@name='tag_ids']`: add field x_studio_confirm_draft_quotation; after `//field[@name='product_packaging_id']`: add | Repair order form: adds a read-only 'Confirm Draft Quotation' field after Tags; a second change was emptied during porting and adds nothing. | `repair.order.x_studio_confirm_draft_quotation`<br>`view repair.view_repair_order_form` (repair) |  |
| Odoo Studio: repair.form customization_button | `view_4015_odoo_studio_repair_form_customization_button_e` | form | inside `//form`: add field x_studio_confirm_draft_quotation; before `//header/button[@name='action_validate']`: add ; set invisible=state != 'draft' on `//header/button[@name='action_validate']` | Repair order form: adds a hidden Confirm Draft Quotation field and shows Validate only in draft; the original Studio button was stripped, leaving only stray text 'x_studio_confirm_draft_quotation' before Validate. | `repair.order.x_studio_confirm_draft_quotation`<br>`view repair.view_repair_order_form` (repair) |  |

**Record rules (1):**

| Name | Record name | Function | Depends on | Used by |
|---|---|---|---|---|
| repair order multi-company | `rule_223_repair_order_multi_company` | For everyone (global rule): read/write/create/delete on Repair Order only where `[('company_id', 'in', company_ids)]`. | `model repair.order` (repair)<br>`repair.order.company_id` (repair) |  |
