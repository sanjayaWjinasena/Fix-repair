# Fix-repair — `x_conditions`

[← back to Functional_Documentation.md](../Functional_Documentation.md)

### `x_conditions` — Conditions

*Created by this repo.* Python: `models/repair_master_data.py`, `models/x_conditions_gap.py`. Record name field: `x_name`.

**Summary:**

<!-- SUMMARY:model:x_conditions -->
A Condition records when a fault occurs (for example "When switched on"). It is picked on Task Diagnosis lines (`x_studio_condition`). It is a company-scoped lookup list maintained under Helpdesk > Repair Diagnosis, with list, form and search views and an editable list layout. The "JIN - Company Id in Conditions" automation stamps Company (`x_studio_company_id`) with the user's current company on create, and a multi-company record rule limits visibility to the user's companies (or rows without a company). Initial rows are seeded from `data/repair_diagnosis_seed.xml` (noupdate, so user edits are kept).
<!-- /SUMMARY -->

**Fields (35):**

| Field | Label | Type | Function | How it gets its value | Depends on | Used by |
|---|---|---|---|---|---|---|
| `activity_calendar_event_id` | Next Activity Calendar Event | many2one → `calendar.event` | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored | `model calendar.event` (calendar) |  |
| `activity_date_deadline` | Next Activity Deadline | date | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored |  |  |
| `activity_exception_decoration` | Activity Exception Decoration | selection: warning=Alert; danger=Error | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored |  |  |
| `activity_exception_icon` | Icon | char | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored |  |  |
| `activity_ids` | Activities | one2many → `mail.activity` | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | stored | `model mail.activity` (mail) | `view Fix-repair.view_4951_default_form_view_for_x_conditions_e`<br>`view Fix-repair.view_x_conditions_form`<br>`x_conditions.activity_summary`<br>`x_conditions.activity_type_icon`<br>`x_conditions.activity_type_id` |
| `activity_state` | Activity State | selection: overdue=Overdue; today=Today; planned=Planned | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored |  |  |
| `activity_summary` | Next Activity Summary | char | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | related `activity_ids.summary`; not stored | `mail.activity.summary` (mail)<br>`x_conditions.activity_ids` |  |
| `activity_type_icon` | Activity Type Icon | char | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | related `activity_ids.icon`; not stored | `mail.activity.icon` (mail)<br>`x_conditions.activity_ids` |  |
| `activity_type_id` | Next Activity Type | many2one → `mail.activity.type` | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | related `activity_ids.activity_type_id`; not stored | `mail.activity.activity_type_id` (mail)<br>`model mail.activity.type` (mail)<br>`x_conditions.activity_ids` |  |
| `activity_user_id` | Responsible User | many2one → `res.users` | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored | `model res.users` (base) |  |
| `create_date` | Created on | datetime | Date and time the record was created (automatic). | stored |  | `automation Fix-repair.base_automation_293_jin_company_id_in_conditions` |
| `create_uid` | Created by | many2one → `res.users` | User who created the record (automatic). | stored | `model res.users` (base) |  |
| `display_name` | Display Name | char | Name shown for the record in lists, dropdowns and links (computed automatically by Odoo). | not stored |  |  |
| `has_message` | Has Message | boolean | Standard chatter field: tells whether the record has messages. | not stored |  |  |
| `id` | ID | integer | Unique database ID of the record (automatic). | stored |  |  |
| `message_attachment_count` | Attachment Count | integer | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_follower_ids` | Followers | one2many → `mail.followers` | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | stored | `model mail.followers` (mail) | `view Fix-repair.view_4951_default_form_view_for_x_conditions_e`<br>`view Fix-repair.view_x_conditions_form` |
| `message_has_error` | Message Delivery error | boolean | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_has_error_counter` | Number of errors | integer | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_has_sms_error` | SMS Delivery error | boolean | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_ids` | Messages | one2many → `mail.message` | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | stored | `model mail.message` (mail) | `view Fix-repair.view_4951_default_form_view_for_x_conditions_e`<br>`view Fix-repair.view_x_conditions_form` |
| `message_is_follower` | Is Follower | boolean | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_needaction` | Action Needed | boolean | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_needaction_counter` | Number of Actions | integer | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_partner_ids` | Followers (Partners) | many2many → `res.partner` | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored | `model res.partner` (base) |  |
| `my_activity_date_deadline` | My Activity Deadline | date | Standard activity field: deadline of the current user’s next activity on the record. | not stored |  |  |
| `rating_ids` | Ratings | one2many → `rating.rating` | Standard customer-rating field provided by Odoo’s rating mixin. | stored | `model rating.rating` (rating) |  |
| `website_message_ids` | Website Messages | one2many → `mail.message` | Standard chatter field: messages shown on the website/portal for this record. | stored | `model mail.message` (mail) |  |
| `write_date` | Last Updated on | datetime | Date and time the record was last changed (automatic). | stored |  |  |
| `write_uid` | Last Updated by | many2one → `res.users` | User who last changed the record (automatic). | stored | `model res.users` (base) |  |
| `x_active` | Active | boolean | Active flag of a Conditions record; unticking it archives the entry so it no longer appears in selection lists (it can still be found with the Archived filter). | stored |  | `default Fix-repair.default_332_x_conditions_x_active`<br>`view Fix-repair.view_4951_default_form_view_for_x_conditions_e`<br>`view Fix-repair.view_4952_default_search_view_for_x_conditions_e`<br>`view Fix-repair.view_x_conditions_form`<br>`view Fix-repair.view_x_conditions_search` |
| `x_name` | Condition | char | Name (Condition) of the Conditions entry; it is the record's display name and is shown in the list, form and search views. | stored |  | `view Fix-repair.view_4950_default_list_view_for_x_conditions_e`<br>`view Fix-repair.view_4951_default_form_view_for_x_conditions_e`<br>`view Fix-repair.view_4952_default_search_view_for_x_conditions_e`<br>`view Fix-repair.view_x_conditions_form`<br>`view Fix-repair.view_x_conditions_search`<details><summary>+1 more</summary>`view Fix-repair.view_x_conditions_tree`</details> |
| `x_studio_company_id` | Company | many2one → `res.company` | Company that owns the Conditions entry, filled by the Jin Company Id server action; multi-company record rules use it to show users only their companies' entries. | stored | `model res.company` (base) | `record rule Fix-repair.rule_552_jin_multi_company_conditions`<br>`server action Fix-repair.sa_f5_x_conditions_jin_company_id_in_conditions`<br>`server action Fix-repair.server_action_2656_jin_company_id_in_conditions`<br>`view Fix-repair.view_final_x_conditions_odoo_studio_default_list_view_for_x_conditions_customization`<br>`view Fix-repair.view_x_conditions_tree_inherit` |
| `x_studio_description` | Description | char | Free-text description of the Conditions entry, shown in the list view. | stored |  | `view Fix-repair.view_final_x_conditions_odoo_studio_default_list_view_for_x_conditions_customization`<br>`view Fix-repair.view_x_conditions_tree_inherit` |
| `x_studio_sequence` | Sequence | integer | Ordering number that sorts Conditions entries in the list view. | stored |  | `default Fix-repair.default_333_x_conditions_x_studio_sequence`<br>`view Fix-repair.view_4950_default_list_view_for_x_conditions_e`<br>`view Fix-repair.view_x_conditions_tree` |

**Server actions (2):**

- **Execute Code** (`server_action_2656_jin_company_id_in_conditions`, type `code`)
  - Function: Sets the record's Company field to the user's currently selected company. Run by the automation that stamps the company on Conditions.
  - Depends on: `model res.company` (base), `model x_conditions`, `x_conditions.x_studio_company_id`
  - Used by: `automation Fix-repair.base_automation_293_jin_company_id_in_conditions`
  <details><summary>code (5 lines)</summary>

```python

company_id = env.context.get('allowed_company_ids', [env.user.company_id.id])[0]
company = env['res.company'].browse(company_id)

record['x_studio_company_id'] = company.id
```
  </details>
- **JIN - Company Id in Conditions** (`sa_f5_x_conditions_jin_company_id_in_conditions`, type `code`)
  - Function: Sets the record's Company field to the user's currently selected company. Defined for Conditions; not referenced by any automation or view.
  - Depends on: `model res.company` (base), `model x_conditions`, `x_conditions.x_studio_company_id`
  - Used by: — (not linked to a button, menu or automation)
  <details><summary>code (4 lines)</summary>

```python
company_id = env.context.get('allowed_company_ids', [env.user.company_id.id])[0]
company = env['res.company'].browse(company_id)

record['x_studio_company_id'] = company.id
```
  </details>
**Automations (1):**

| Name | Record name | State | Function | Depends on | Used by |
|---|---|---|---|---|---|
| JIN - Company Id in Conditions | `base_automation_293_jin_company_id_in_conditions` |  | When a record is created or updated on Conditions, runs _Execute Code_. | `model x_conditions`<br>`server action Fix-repair.server_action_2656_jin_company_id_in_conditions`<br>`x_conditions.create_date` |  |

**Window actions (2):**

| Name | Record name | Function | Depends on | Used by |
|---|---|---|---|---|
| Conditions | `action_x_conditions` | Opens **Conditions** records (tree,form). | `model x_conditions` | `menu Fix-repair.menu_repair_diagnosis_conditions` |
| Conditions | `act_window_2209_conditions` | Opens **Conditions** records (tree,form). | `model x_conditions` | `menu Fix-repair.menu_f6_conditions` |

**Views (8):**

| Name | Record name | Type | What it changes | Function | Depends on | Used by |
|---|---|---|---|---|---|---|
| Default form view for x_conditions | `view_4951_default_form_view_for_x_conditions_e` | form | full form layout with 5 fields | Form view for Conditions: name (required), archived ribbon and chatter; the field groups are empty. Duplicate of the Conditions form view. | `x_conditions.activity_ids`<br>`x_conditions.message_follower_ids`<br>`x_conditions.message_ids`<br>`x_conditions.x_active`<br>`x_conditions.x_name` |  |
| Default list view for x_conditions | `view_4950_default_list_view_for_x_conditions_e` | tree | full tree layout with 2 fields | Base list view for Conditions: drag handle for sequence and name. Duplicate of the Conditions list view. | `x_conditions.x_name`<br>`x_conditions.x_studio_sequence` | `view Fix-repair.view_final_x_conditions_odoo_studio_default_list_view_for_x_conditions_customization` |
| Default search view for x_conditions | `view_4952_default_search_view_for_x_conditions_e` | search | full search layout with 1 fields | Search view for Conditions: search by name, plus an Archived filter. Duplicate of the Conditions search view. | `x_conditions.x_active`<br>`x_conditions.x_name` |  |
| Odoo Studio: Default list view for x_conditions customization | `view_final_x_conditions_odoo_studio_default_list_view_for_x_conditions_customization` | tree | set editable=bottom on `//tree[1]`; set column_invisible=1 on `//field[@name='x_studio_sequence']`; set string=Condition on `//field[@name='x_name']`; after `//field[@name='x_name']`: add field x_studio_description, field x_studio_company_id | Makes the Conditions list editable inline (new rows at bottom), hides the Sequence column, relabels Name as 'Condition', and adds optional Description and Company columns. | `view Fix-repair.view_4950_default_list_view_for_x_conditions_e`<br>`x_conditions.x_studio_company_id`<br>`x_conditions.x_studio_description` |  |
| x_conditions.form | `view_x_conditions_form` | form | full form layout with 5 fields | Form view for Conditions: name (required), archived ribbon and chatter; the field groups are empty. | `x_conditions.activity_ids`<br>`x_conditions.message_follower_ids`<br>`x_conditions.message_ids`<br>`x_conditions.x_active`<br>`x_conditions.x_name` |  |
| x_conditions.search | `view_x_conditions_search` | search | full search layout with 1 fields | Search view for Conditions: search by name, plus an Archived filter. | `x_conditions.x_active`<br>`x_conditions.x_name` |  |
| x_conditions.tree | `view_x_conditions_tree` | tree | full tree layout with 2 fields | Base list view for Conditions: drag handle for sequence and name. | `x_conditions.x_name`<br>`x_conditions.x_studio_sequence` | `view Fix-repair.view_x_conditions_tree_inherit` |
| x_conditions.tree.inherit | `view_x_conditions_tree_inherit` | tree | set editable=bottom on `//tree[1]`; set column_invisible=1 on `//field[@name='x_studio_sequence']`; set string=Condition on `//field[@name='x_name']`; after `//field[@name='x_name']`: add field x_studio_description, field x_studio_company_id | Makes the Conditions list editable inline, hides the sequence column, labels the name 'Condition', and adds Description and Company columns. | `view Fix-repair.view_x_conditions_tree`<br>`x_conditions.x_studio_company_id`<br>`x_conditions.x_studio_description` |  |

**Access rights (4):**

| Name | Record name | Function | Depends on | Used by |
|---|---|---|---|---|
| Conditions group_system | `access_1782_conditions_group_system` | Gives **Administration / Settings** read/write/create/delete access to Conditions records. | `group base.group_system` (base)<br>`model x_conditions` |  |
| Conditions group_user | `access_1783_conditions_group_user` | Gives **User types / Internal User** read access to Conditions records. | `group base.group_user` (base)<br>`model x_conditions` |  |
| x_conditions manager | `access_x_conditions_manager` | Gives **Helpdesk / Administrator** read/write/create/delete access to Conditions records. | `group helpdesk.group_helpdesk_manager` (helpdesk)<br>`model x_conditions` |  |
| x_conditions user | `access_x_conditions_user` | Gives **Helpdesk / User** read/write/create/delete access to Conditions records. | `group helpdesk.group_helpdesk_user` (helpdesk)<br>`model x_conditions` |  |

**Record rules (1):**

| Name | Record name | Function | Depends on | Used by |
|---|---|---|---|---|
| JIN - Multi-Company - Conditions | `rule_552_jin_multi_company_conditions` | For everyone (global rule): read/write/create/delete on Conditions only where `['|', ('x_studio_company_id', 'in', company_ids), ('x_studio_company_id', '=', False)]`. | `model x_conditions`<br>`x_conditions.x_studio_company_id` |  |
