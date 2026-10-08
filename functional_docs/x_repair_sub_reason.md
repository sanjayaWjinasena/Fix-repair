# Fix-repair — `x_repair_sub_reason`

[← back to Functional_Documentation.md](../Functional_Documentation.md)

### `x_repair_sub_reason` — Repair Sub Reason

*Created by this repo.* Python: `models/repair_master_data.py`. Record name field: `x_name`.

**Summary:**

<!-- SUMMARY:model:x_repair_sub_reason -->
A Repair Sub Reason is a more detailed reason under a parent Repair Reason (`x_studio_reason_code`). It is picked on Task Diagnosis lines (`x_studio_sub_reason`). Company (`x_studio_company_id`) is filled with the user's current company by the `create` override, which replaces the archived Studio automation "JIN - Company Id in Repair Sub Reason". A multi-company record rule limits visibility to the user's companies (or rows without a company), and initial rows are seeded from `data/repair_diagnosis_seed.xml` (noupdate). It is maintained under Helpdesk > Repair Diagnosis.
<!-- /SUMMARY -->

**Fields (35):**

| Field | Label | Type | Function | How it gets its value | Depends on | Used by |
|---|---|---|---|---|---|---|
| `activity_calendar_event_id` | Next Activity Calendar Event | many2one → `calendar.event` | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored | `model calendar.event` (calendar) |  |
| `activity_date_deadline` | Next Activity Deadline | date | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored |  |  |
| `activity_exception_decoration` | Activity Exception Decoration | selection: warning=Alert; danger=Error | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored |  |  |
| `activity_exception_icon` | Icon | char | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored |  |  |
| `activity_ids` | Activities | one2many → `mail.activity` | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | stored | `model mail.activity` (mail) | `view Fix-repair.view_4973_default_form_view_for_x_repair_sub_reason_e`<br>`x_repair_sub_reason.activity_summary`<br>`x_repair_sub_reason.activity_type_icon`<br>`x_repair_sub_reason.activity_type_id` |
| `activity_state` | Activity State | selection: overdue=Overdue; today=Today; planned=Planned | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored |  |  |
| `activity_summary` | Next Activity Summary | char | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | related `activity_ids.summary`; not stored | `mail.activity.summary` (mail)<br>`x_repair_sub_reason.activity_ids` |  |
| `activity_type_icon` | Activity Type Icon | char | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | related `activity_ids.icon`; not stored | `mail.activity.icon` (mail)<br>`x_repair_sub_reason.activity_ids` |  |
| `activity_type_id` | Next Activity Type | many2one → `mail.activity.type` | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | related `activity_ids.activity_type_id`; not stored | `mail.activity.activity_type_id` (mail)<br>`model mail.activity.type` (mail)<br>`x_repair_sub_reason.activity_ids` |  |
| `activity_user_id` | Responsible User | many2one → `res.users` | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored | `model res.users` (base) |  |
| `create_date` | Created on | datetime | Date and time the record was created (automatic). | stored |  |  |
| `create_uid` | Created by | many2one → `res.users` | User who created the record (automatic). | stored | `model res.users` (base) |  |
| `display_name` | Display Name | char | Name shown for the record in lists, dropdowns and links (computed automatically by Odoo). | not stored |  |  |
| `has_message` | Has Message | boolean | Standard chatter field: tells whether the record has messages. | not stored |  |  |
| `id` | ID | integer | Unique database ID of the record (automatic). | stored |  |  |
| `message_attachment_count` | Attachment Count | integer | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_follower_ids` | Followers | one2many → `mail.followers` | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | stored | `model mail.followers` (mail) | `view Fix-repair.view_4973_default_form_view_for_x_repair_sub_reason_e` |
| `message_has_error` | Message Delivery error | boolean | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_has_error_counter` | Number of errors | integer | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_has_sms_error` | SMS Delivery error | boolean | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_ids` | Messages | one2many → `mail.message` | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | stored | `model mail.message` (mail) | `view Fix-repair.view_4973_default_form_view_for_x_repair_sub_reason_e` |
| `message_is_follower` | Is Follower | boolean | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_needaction` | Action Needed | boolean | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_needaction_counter` | Number of Actions | integer | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_partner_ids` | Followers (Partners) | many2many → `res.partner` | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored | `model res.partner` (base) |  |
| `my_activity_date_deadline` | My Activity Deadline | date | Standard activity field: deadline of the current user’s next activity on the record. | not stored |  |  |
| `rating_ids` | Ratings | one2many → `rating.rating` | Standard customer-rating field provided by Odoo’s rating mixin. | stored | `model rating.rating` (rating) |  |
| `website_message_ids` | Website Messages | one2many → `mail.message` | Standard chatter field: messages shown on the website/portal for this record. | stored | `model mail.message` (mail) |  |
| `write_date` | Last Updated on | datetime | Date and time the record was last changed (automatic). | stored |  |  |
| `write_uid` | Last Updated by | many2one → `res.users` | User who last changed the record (automatic). | stored | `model res.users` (base) |  |
| `x_active` | Active | boolean | Active flag of a Repair Sub Reason record; unticking it archives the entry so it no longer appears in selection lists (it can still be found with the Archived filter). | default `True`; stored |  | `default Fix-repair.default_343_x_repair_sub_reason_x_active`<br>`view Fix-repair.view_4973_default_form_view_for_x_repair_sub_reason_e`<br>`view Fix-repair.view_4974_default_search_view_for_x_repair_sub_reason_e` |
| `x_name` | Sub Reason Code | char | Name (Sub Reason Code) of the Repair Sub Reason entry; it is the record's display name and is shown in the list, form and search views. | stored |  | `view Fix-repair.view_4972_default_list_view_for_x_repair_sub_reason_e`<br>`view Fix-repair.view_4973_default_form_view_for_x_repair_sub_reason_e`<br>`view Fix-repair.view_4974_default_search_view_for_x_repair_sub_reason_e` |
| `x_studio_company_id` | Company | many2one → `res.company` | Company that owns the Repair Sub Reason entry, filled automatically on create by `_jin_set_company_id`; multi-company record rules use it to show users only their companies' entries. | stored | `model res.company` (base) | `record rule Fix-repair.rule_559_jin_multi_company_repair_sub_reason`<br>`record rule Fix-repair.rule_f7_x_repair_sub_reason_jin_multi_company_repair_sub_reason`<br>`view Fix-repair.view_final_x_repair_sub_reason_odoo_studio_default_list_view_for_x_repair_sub_reason_custo`<br>`x_repair_sub_reason._jin_set_company_id()` |
| `x_studio_reason_code` | Reason Code | many2one → `x_repair_reason` | Parent repair reason this sub-reason belongs to; shown in the sub-reason list. | stored | `model x_repair_reason` | `view Fix-repair.view_final_x_repair_sub_reason_odoo_studio_default_list_view_for_x_repair_sub_reason_custo` |
| `x_studio_sequence` | Sequence | integer | Ordering number that sorts Repair Sub Reason entries in the list view. | stored |  | `default Fix-repair.default_344_x_repair_sub_reason_x_studio_sequence`<br>`view Fix-repair.view_4972_default_list_view_for_x_repair_sub_reason_e` |

**Python methods (2):**

| Method | Function | Decorators | Extends standard | Depends on | Used by | Where |
|---|---|---|---|---|---|---|
| `_jin_set_company_id` | Sets the repair sub reason's Company field to the user's currently selected company. |  |  | `x_repair_sub_reason.x_studio_company_id` | `x_repair_sub_reason.create()` | `models/repair_master_data.py:157` |
| `create` | Override of repair sub reason creation: stamps the current company after creating (replaces Studio automation 'JIN Company Id in Repair Sub Reason'). | api.model_create_multi | yes | `x_repair_sub_reason._jin_set_company_id()` |  | `models/repair_master_data.py:166` |

**Server actions (1):**

- **JIN - Company Id in Repair Sub Reason** (`server_action_2668_jin_company_id_in_repair_sub_reason`, type `code`)
  - Function: Sets the record's Company field to the user's currently selected company. Delegates to the native company setter for repair sub reason (record creation now does this automatically).
  - Depends on: `model x_repair_sub_reason`
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
| JIN - Company Id in Repair Sub Reason | `base_automation_304_jin_company_id_in_repair_sub_reason` | archived | When a record is created or updated on Repair Sub Reason, runs nothing (no action linked). **Archived — does not run.** | `model x_repair_sub_reason` |  |

**Window actions (2):**

| Name | Record name | Function | Depends on | Used by |
|---|---|---|---|---|
| Repair Sub Reason | `action_x_repair_sub_reason` | Opens **Repair Sub Reason** records (tree,form). | `model x_repair_sub_reason` | `menu Fix-repair.menu_repair_diagnosis_repair_sub_reason` |
| Repair Sub Reason | `act_window_2214_repair_sub_reason` | Opens **Repair Sub Reason** records (tree,form). | `model x_repair_sub_reason` | `menu Fix-repair.menu_f6_repair_sub_reason` |

**Views (4):**

| Name | Record name | Type | What it changes | Function | Depends on | Used by |
|---|---|---|---|---|---|---|
| Default form view for x_repair_sub_reason | `view_4973_default_form_view_for_x_repair_sub_reason_e` | form | full form layout with 5 fields | Base form screen for the Repair Sub Reason configuration list (`x_repair_sub_reason`): Name as the title, an Archived ribbon when inactive, two empty groups that Studio extensions fill, and chatter. | `x_repair_sub_reason.activity_ids`<br>`x_repair_sub_reason.message_follower_ids`<br>`x_repair_sub_reason.message_ids`<br>`x_repair_sub_reason.x_active`<br>`x_repair_sub_reason.x_name` |  |
| Default list view for x_repair_sub_reason | `view_4972_default_list_view_for_x_repair_sub_reason_e` | tree | full tree layout with 2 fields | Base list screen for Repair Sub Reason (`x_repair_sub_reason`): shows the Name column with a drag handle on Sequence for manual reordering. | `x_repair_sub_reason.x_name`<br>`x_repair_sub_reason.x_studio_sequence` | `view Fix-repair.view_final_x_repair_sub_reason_odoo_studio_default_list_view_for_x_repair_sub_reason_custo` |
| Default search view for x_repair_sub_reason | `view_4974_default_search_view_for_x_repair_sub_reason_e` | search | full search layout with 1 fields | Search screen for Repair Sub Reason (`x_repair_sub_reason`): search by Name plus an Archived filter to show inactive records. | `x_repair_sub_reason.x_active`<br>`x_repair_sub_reason.x_name` |  |
| Odoo Studio: Default list view for x_repair_sub_reason customization | `view_final_x_repair_sub_reason_odoo_studio_default_list_view_for_x_repair_sub_reason_custo` | tree | set editable=bottom on `//tree[1]`; set string=Sub Reason Code on `//field[@name='x_name']`; after `//field[@name='x_name']`: add field x_studio_reason_code, field x_studio_company_id | Makes the Repair Sub Reason list editable inline, relabels Name as 'Sub Reason Code', and adds optional Reason Code (parent reason, no quick-create) and Company columns. | `view Fix-repair.view_4972_default_list_view_for_x_repair_sub_reason_e`<br>`x_repair_sub_reason.x_studio_company_id`<br>`x_repair_sub_reason.x_studio_reason_code` |  |

**Access rights (4):**

| Name | Record name | Function | Depends on | Used by |
|---|---|---|---|---|
| Repair Sub Reason group_system | `access_1792_repair_sub_reason_group_system` | Gives **Administration / Settings** read/write/create/delete access to Repair Sub Reason records. | `group base.group_system` (base)<br>`model x_repair_sub_reason` |  |
| Repair Sub Reason group_user | `access_1793_repair_sub_reason_group_user` | Gives **User types / Internal User** read access to Repair Sub Reason records. | `group base.group_user` (base)<br>`model x_repair_sub_reason` |  |
| x_repair_sub_reason manager | `access_x_repair_sub_reason_manager` | Gives **Helpdesk / Administrator** read/write/create/delete access to Repair Sub Reason records. | `group helpdesk.group_helpdesk_manager` (helpdesk)<br>`model x_repair_sub_reason` |  |
| x_repair_sub_reason user | `access_x_repair_sub_reason_user` | Gives **Helpdesk / User** read/write/create/delete access to Repair Sub Reason records. | `group helpdesk.group_helpdesk_user` (helpdesk)<br>`model x_repair_sub_reason` |  |

**Record rules (2):**

| Name | Record name | Function | Depends on | Used by |
|---|---|---|---|---|
| JIN - Multi-Company - Repair Sub Reason | `rule_f7_x_repair_sub_reason_jin_multi_company_repair_sub_reason` | For everyone (global rule): read/write/create/delete on Repair Sub Reason only where `['|', ('x_studio_company_id', 'in', company_ids), ('x_studio_company_id', '=', False)]`. | `model x_repair_sub_reason`<br>`x_repair_sub_reason.x_studio_company_id` |  |
| JIN - Multi-Company - Repair Sub Reason | `rule_559_jin_multi_company_repair_sub_reason` | For everyone (global rule): read/write/create/delete on Repair Sub Reason only where `['|', ('x_studio_company_id', 'in', company_ids), ('x_studio_company_id', '=', False)]`. | `model x_repair_sub_reason`<br>`x_repair_sub_reason.x_studio_company_id` |  |
