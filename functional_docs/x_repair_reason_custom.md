# Fix-repair — `x_repair_reason_custom`

[← back to Functional_Documentation.md](../Functional_Documentation.md)

### `x_repair_reason_custom` — Repair Reason - Customer

*Created by this repo.* Python: `models/repair_master_data.py`. Record name field: `x_name`.

**Summary:**

<!-- SUMMARY:model:x_repair_reason_custom -->
A Repair Reason - Customer is a customer-facing repair reason, parallel to Repair Reason. It is picked on the helpdesk ticket's Repair Reason field (`x_studio_repair_reason`). Company (`x_studio_company_id`) is filled with the user's current company by the `create` override, which replaces the archived Studio automation "JIN - Company Id in Repair Reason - Customer". A multi-company record rule limits visibility to the user's companies (or rows without a company), and initial rows are seeded from `data/repair_diagnosis_seed.xml` (noupdate). It is maintained under Helpdesk > Repair Diagnosis.
<!-- /SUMMARY -->

**Fields (35):**

| Field | Label | Type | Function | How it gets its value | Depends on | Used by |
|---|---|---|---|---|---|---|
| `activity_calendar_event_id` | Next Activity Calendar Event | many2one → `calendar.event` | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored | `model calendar.event` (calendar) |  |
| `activity_date_deadline` | Next Activity Deadline | date | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored |  |  |
| `activity_exception_decoration` | Activity Exception Decoration | selection: warning=Alert; danger=Error | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored |  |  |
| `activity_exception_icon` | Icon | char | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored |  |  |
| `activity_ids` | Activities | one2many → `mail.activity` | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | stored | `model mail.activity` (mail) | `view Fix-repair.view_4991_default_form_view_for_x_repair_reason_custom_e`<br>`x_repair_reason_custom.activity_summary`<br>`x_repair_reason_custom.activity_type_icon`<br>`x_repair_reason_custom.activity_type_id` |
| `activity_state` | Activity State | selection: overdue=Overdue; today=Today; planned=Planned | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored |  |  |
| `activity_summary` | Next Activity Summary | char | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | related `activity_ids.summary`; not stored | `mail.activity.summary` (mail)<br>`x_repair_reason_custom.activity_ids` |  |
| `activity_type_icon` | Activity Type Icon | char | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | related `activity_ids.icon`; not stored | `mail.activity.icon` (mail)<br>`x_repair_reason_custom.activity_ids` |  |
| `activity_type_id` | Next Activity Type | many2one → `mail.activity.type` | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | related `activity_ids.activity_type_id`; not stored | `mail.activity.activity_type_id` (mail)<br>`model mail.activity.type` (mail)<br>`x_repair_reason_custom.activity_ids` |  |
| `activity_user_id` | Responsible User | many2one → `res.users` | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored | `model res.users` (base) |  |
| `create_date` | Created on | datetime | Date and time the record was created (automatic). | stored |  |  |
| `create_uid` | Created by | many2one → `res.users` | User who created the record (automatic). | stored | `model res.users` (base) |  |
| `display_name` | Display Name | char | Name shown for the record in lists, dropdowns and links (computed automatically by Odoo). | not stored |  |  |
| `has_message` | Has Message | boolean | Standard chatter field: tells whether the record has messages. | not stored |  |  |
| `id` | ID | integer | Unique database ID of the record (automatic). | stored |  |  |
| `message_attachment_count` | Attachment Count | integer | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_follower_ids` | Followers | one2many → `mail.followers` | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | stored | `model mail.followers` (mail) | `view Fix-repair.view_4991_default_form_view_for_x_repair_reason_custom_e` |
| `message_has_error` | Message Delivery error | boolean | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_has_error_counter` | Number of errors | integer | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_has_sms_error` | SMS Delivery error | boolean | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_ids` | Messages | one2many → `mail.message` | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | stored | `model mail.message` (mail) | `view Fix-repair.view_4991_default_form_view_for_x_repair_reason_custom_e` |
| `message_is_follower` | Is Follower | boolean | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_needaction` | Action Needed | boolean | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_needaction_counter` | Number of Actions | integer | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_partner_ids` | Followers (Partners) | many2many → `res.partner` | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored | `model res.partner` (base) |  |
| `my_activity_date_deadline` | My Activity Deadline | date | Standard activity field: deadline of the current user’s next activity on the record. | not stored |  |  |
| `rating_ids` | Ratings | one2many → `rating.rating` | Standard customer-rating field provided by Odoo’s rating mixin. | stored | `model rating.rating` (rating) |  |
| `website_message_ids` | Website Messages | one2many → `mail.message` | Standard chatter field: messages shown on the website/portal for this record. | stored | `model mail.message` (mail) |  |
| `write_date` | Last Updated on | datetime | Date and time the record was last changed (automatic). | stored |  |  |
| `write_uid` | Last Updated by | many2one → `res.users` | User who last changed the record (automatic). | stored | `model res.users` (base) |  |
| `x_active` | Active | boolean | Active flag of a Repair Reason - Customer record; unticking it archives the entry so it no longer appears in selection lists (it can still be found with the Archived filter). | default `True`; stored |  | `default Fix-repair.default_357_x_repair_reason_custom_x_active`<br>`view Fix-repair.view_4991_default_form_view_for_x_repair_reason_custom_e`<br>`view Fix-repair.view_4992_default_search_view_for_x_repair_reason_custom_e` |
| `x_color` | Color | integer | Colour index of the Repair Reason - Customer tag; only affects how the tag is coloured, no other logic. | stored |  |  |
| `x_name` | Repair Reason | char | Name (Repair Reason) of the Repair Reason - Customer entry; it is the record's display name and is shown in the list, form and search views. | stored |  | `view Fix-repair.view_4990_default_list_view_for_x_repair_reason_custom_e`<br>`view Fix-repair.view_4991_default_form_view_for_x_repair_reason_custom_e`<br>`view Fix-repair.view_4992_default_search_view_for_x_repair_reason_custom_e` |
| `x_studio_company_id` | Company | many2one → `res.company` | Company that owns the Repair Reason - Customer entry, filled automatically on create by `_jin_set_company_id`; multi-company record rules use it to show users only their companies' entries. | stored | `model res.company` (base) | `record rule Fix-repair.rule_558_jin_multi_company_repair_reason_customer`<br>`record rule Fix-repair.rule_f7_x_repair_reason_custom_jin_multi_company_repair_reason_customer`<br>`view Fix-repair.view_final_x_repair_reason_custom_odoo_studio_default_list_view_for_x_repair_reason_custom`<br>`x_repair_reason_custom._jin_set_company_id()` |
| `x_studio_sequence` | Sequence | integer | Ordering number that sorts Repair Reason - Customer entries in the list view. | stored |  | `default Fix-repair.default_358_x_repair_reason_custom_x_studio_sequence`<br>`view Fix-repair.view_4990_default_list_view_for_x_repair_reason_custom_e` |

**Python methods (2):**

| Method | Function | Decorators | Extends standard | Depends on | Used by | Where |
|---|---|---|---|---|---|---|
| `_jin_set_company_id` | Sets the customer repair reason's Company field to the user's currently selected company. |  |  | `x_repair_reason_custom.x_studio_company_id` | `x_repair_reason_custom.create()` | `models/repair_master_data.py:89` |
| `create` | Override of customer repair reason creation: stamps the current company after creating (replaces Studio automation 'JIN Company Id in Repair Reason - Customer'). | api.model_create_multi | yes | `x_repair_reason_custom._jin_set_company_id()` |  | `models/repair_master_data.py:98` |

**Server actions (1):**

- **JIN - Company Id in Repair Reason - Customer** (`server_action_2667_jin_company_id_in_repair_reason_customer`, type `code`)
  - Function: Sets the record's Company field to the user's currently selected company. Delegates to the native company setter for customer repair reason (record creation now does this automatically).
  - Depends on: `model x_repair_reason_custom`
  - Used by: — (not linked to a button, menu or automation)
  <details><summary>code (2 lines)</summary>

```python
# fix_repair:idempotent-v1
record._jin_set_company_id()
```
  </details>
**Automations (1):**

| Name | Record name | State | Function | Depends on | Used by |
|---|---|---|---|---|---|
| JIN - Company Id in Repair Reason - Customer | `base_automation_303_jin_company_id_in_repair_reason_customer` | archived | When a record is created or updated on Repair Reason - Customer, runs nothing (no action linked). **Archived — does not run.** | `model x_repair_reason_custom` |  |

**Window actions (2):**

| Name | Record name | Function | Depends on | Used by |
|---|---|---|---|---|
| Repair Reason - Customer | `action_x_repair_reason_custom` | Opens **Repair Reason - Customer** records (tree,form). | `model x_repair_reason_custom` | `menu Fix-repair.menu_repair_diagnosis_repair_reason_custom` |
| Repair Reason - Customer | `act_window_2218_repair_reason_customer` | Opens **Repair Reason - Customer** records (tree,form). | `model x_repair_reason_custom` | `menu Fix-repair.menu_f6_repair_reason_customer` |

**Views (4):**

| Name | Record name | Type | What it changes | Function | Depends on | Used by |
|---|---|---|---|---|---|---|
| Default form view for x_repair_reason_custom | `view_4991_default_form_view_for_x_repair_reason_custom_e` | form | full form layout with 5 fields | Base form screen for the Repair Reason - Customer configuration list (`x_repair_reason_custom`): Name as the title, an Archived ribbon when inactive, two empty groups that Studio extensions fill, and chatter. | `x_repair_reason_custom.activity_ids`<br>`x_repair_reason_custom.message_follower_ids`<br>`x_repair_reason_custom.message_ids`<br>`x_repair_reason_custom.x_active`<br>`x_repair_reason_custom.x_name` |  |
| Default list view for x_repair_reason_custom | `view_4990_default_list_view_for_x_repair_reason_custom_e` | tree | full tree layout with 2 fields | Base list screen for Repair Reason - Customer (`x_repair_reason_custom`): shows the Name column with a drag handle on Sequence for manual reordering. | `x_repair_reason_custom.x_name`<br>`x_repair_reason_custom.x_studio_sequence` | `view Fix-repair.view_final_x_repair_reason_custom_odoo_studio_default_list_view_for_x_repair_reason_custom` |
| Default search view for x_repair_reason_custom | `view_4992_default_search_view_for_x_repair_reason_custom_e` | search | full search layout with 1 fields | Search screen for Repair Reason - Customer (`x_repair_reason_custom`): search by Name plus an Archived filter to show inactive records. | `x_repair_reason_custom.x_active`<br>`x_repair_reason_custom.x_name` |  |
| Odoo Studio: Default list view for x_repair_reason_custom customization | `view_final_x_repair_reason_custom_odoo_studio_default_list_view_for_x_repair_reason_custom` | tree | set editable=bottom on `//tree[1]`; set column_invisible=1 on `//field[@name='x_studio_sequence']`; set string=Repair Reason on `//field[@name='x_name']`; after `//field[@name='x_name']`: add field x_studio_company_id | Makes the Repair Reason - Customer list editable inline, hides the Sequence column, relabels Name as 'Repair Reason', and adds an optional Company column. | `view Fix-repair.view_4990_default_list_view_for_x_repair_reason_custom_e`<br>`x_repair_reason_custom.x_studio_company_id` |  |

**Access rights (4):**

| Name | Record name | Function | Depends on | Used by |
|---|---|---|---|---|
| Repair Reason - Customer group_system | `access_1800_repair_reason___customer_group_system` | Gives **Administration / Settings** read/write/create/delete access to Repair Reason - Customer records. | `group base.group_system` (base)<br>`model x_repair_reason_custom` |  |
| Repair Reason - Customer group_user | `access_1801_repair_reason___customer_group_user` | Gives **User types / Internal User** read access to Repair Reason - Customer records. | `group base.group_user` (base)<br>`model x_repair_reason_custom` |  |
| x_repair_reason_custom manager | `access_x_repair_reason_custom_manager` | Gives **Helpdesk / Administrator** read/write/create/delete access to Repair Reason - Customer records. | `group helpdesk.group_helpdesk_manager` (helpdesk)<br>`model x_repair_reason_custom` |  |
| x_repair_reason_custom user | `access_x_repair_reason_custom_user` | Gives **Helpdesk / User** read/write/create/delete access to Repair Reason - Customer records. | `group helpdesk.group_helpdesk_user` (helpdesk)<br>`model x_repair_reason_custom` |  |

**Record rules (2):**

| Name | Record name | Function | Depends on | Used by |
|---|---|---|---|---|
| JIN - Multi-Company - Repair Reason - Customer | `rule_f7_x_repair_reason_custom_jin_multi_company_repair_reason_customer` | For everyone (global rule): read/write/create/delete on Repair Reason - Customer only where `['|', ('x_studio_company_id', 'in', company_ids), ('x_studio_company_id', '=', False)]`. | `model x_repair_reason_custom`<br>`x_repair_reason_custom.x_studio_company_id` |  |
| JIN - Multi-Company - Repair Reason - Customer | `rule_558_jin_multi_company_repair_reason_customer` | For everyone (global rule): read/write/create/delete on Repair Reason - Customer only where `['|', ('x_studio_company_id', 'in', company_ids), ('x_studio_company_id', '=', False)]`. | `model x_repair_reason_custom`<br>`x_repair_reason_custom.x_studio_company_id` |  |
