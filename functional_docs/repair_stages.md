# Fix-repair — `repair_stages`

[← back to Functional_Documentation.md](../Functional_Documentation.md)

### `repair_stages` — Repair Stages

*Created by this repo.* Python: `models/repair_master_data.py`. Record name field: `name`.

**Summary:**

<!-- SUMMARY:model:repair_stages -->
A Repair Stage is an entry in a repair-stage catalogue that is separate from the helpdesk ticket stages. It can be picked on Task Diagnosis lines (`repair_stage`). Company (`accounting_company_id`) is filled with the user's current company by the `create` override, which replaces the archived Studio automation "JIN - Company Id in Repair Stages". A multi-company record rule limits visibility to the user's companies (or rows without a company), and initial rows are seeded from `data/repair_diagnosis_seed.xml` (noupdate). It is maintained under Helpdesk > Repair Diagnosis.
<!-- /SUMMARY -->

**Fields (35):**

| Field | Label | Type | Function | How it gets its value | Depends on | Used by |
|---|---|---|---|---|---|---|
| `activity_calendar_event_id` | Next Activity Calendar Event | many2one → `calendar.event` | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored | `model calendar.event` (calendar) |  |
| `activity_date_deadline` | Next Activity Deadline | date | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored |  |  |
| `activity_exception_decoration` | Activity Exception Decoration | selection: warning=Alert; danger=Error | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored |  |  |
| `activity_exception_icon` | Icon | char | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored |  |  |
| `activity_ids` | Activities | one2many → `mail.activity` | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | stored | `model mail.activity` (mail) | `view Fix-repair.view_repair_stages_form`<br>`repair_stages.activity_summary`<br>`repair_stages.activity_type_icon`<br>`repair_stages.activity_type_id` |
| `activity_state` | Activity State | selection: overdue=Overdue; today=Today; planned=Planned | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored |  |  |
| `activity_summary` | Next Activity Summary | char | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | related `activity_ids.summary`; not stored | `mail.activity.summary` (mail)<br>`repair_stages.activity_ids` |  |
| `activity_type_icon` | Activity Type Icon | char | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | related `activity_ids.icon`; not stored | `mail.activity.icon` (mail)<br>`repair_stages.activity_ids` |  |
| `activity_type_id` | Next Activity Type | many2one → `mail.activity.type` | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | related `activity_ids.activity_type_id`; not stored | `mail.activity.activity_type_id` (mail)<br>`model mail.activity.type` (mail)<br>`repair_stages.activity_ids` |  |
| `activity_user_id` | Responsible User | many2one → `res.users` | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored | `model res.users` (base) |  |
| `create_date` | Created on | datetime | Date and time the record was created (automatic). | stored |  |  |
| `create_uid` | Created by | many2one → `res.users` | User who created the record (automatic). | stored | `model res.users` (base) |  |
| `display_name` | Display Name | char | Name shown for the record in lists, dropdowns and links (computed automatically by Odoo). | not stored |  |  |
| `has_message` | Has Message | boolean | Standard chatter field: tells whether the record has messages. | not stored |  |  |
| `id` | ID | integer | Unique database ID of the record (automatic). | stored |  |  |
| `message_attachment_count` | Attachment Count | integer | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_follower_ids` | Followers | one2many → `mail.followers` | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | stored | `model mail.followers` (mail) | `view Fix-repair.view_repair_stages_form` |
| `message_has_error` | Message Delivery error | boolean | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_has_error_counter` | Number of errors | integer | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_has_sms_error` | SMS Delivery error | boolean | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_ids` | Messages | one2many → `mail.message` | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | stored | `model mail.message` (mail) | `view Fix-repair.view_repair_stages_form` |
| `message_is_follower` | Is Follower | boolean | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_needaction` | Action Needed | boolean | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_needaction_counter` | Number of Actions | integer | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_partner_ids` | Followers (Partners) | many2many → `res.partner` | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored | `model res.partner` (base) |  |
| `my_activity_date_deadline` | My Activity Deadline | date | Standard activity field: deadline of the current user’s next activity on the record. | not stored |  |  |
| `rating_ids` | Ratings | one2many → `rating.rating` | Standard customer-rating field provided by Odoo’s rating mixin. | stored | `model rating.rating` (rating) |  |
| `website_message_ids` | Website Messages | one2many → `mail.message` | Standard chatter field: messages shown on the website/portal for this record. | stored | `model mail.message` (mail) |  |
| `write_date` | Last Updated on | datetime | Date and time the record was last changed (automatic). | stored |  |  |
| `write_uid` | Last Updated by | many2one → `res.users` | User who last changed the record (automatic). | stored | `model res.users` (base) |  |
| `active` | Active | boolean | Active flag of a Repair Stages record; unticking it archives the entry so it no longer appears in selection lists (it can still be found with the Archived filter). | default `True`; stored |  | `default Fix-repair.default_repair_stages_active`<br>`view Fix-repair.view_repair_stages_form`<br>`view Fix-repair.view_repair_stages_search` |
| `name` | Repair Stage | char | Name (Repair Stage) of the Repair Stages entry; it is the record's display name and is shown in the list, form and search views. | stored |  | `view Fix-repair.view_repair_stages_list`<br>`view Fix-repair.view_repair_stages_form`<br>`view Fix-repair.view_repair_stages_search` |
| `accounting_company_id` | Company | many2one → `res.company` | Company that owns the Repair Stages entry, filled automatically on create by `_jin_set_company_id`; multi-company record rules use it to show users only their companies' entries. | stored | `model res.company` (base) | `record rule Fix-repair.rule_jin_multi_company_repair_stages`<br>`record rule Fix-repair.rule_f7_repair_stages_jin_multi_company_repair_stages`<br>`view Fix-repair.view_default_list_view_for_repair_stages_inherit`<br>`repair_stages._jin_set_company_id()` |
| `description` | Description | char | Free-text description of the Repair Stages entry, shown in the list view. | stored |  | `view Fix-repair.view_default_list_view_for_repair_stages_inherit` |
| `sequence` | Sequence | integer | Ordering number that sorts Repair Stages entries in the list view. | stored |  | `default Fix-repair.default_repair_stages_sequence`<br>`view Fix-repair.view_repair_stages_list` |

**Python methods (2):**

| Method | Function | Decorators | Extends standard | Depends on | Used by | Where |
|---|---|---|---|---|---|---|
| `_jin_set_company_id` | Sets the repair stage's Company field to the user's currently selected company. |  |  | `repair_stages.accounting_company_id` | `repair_stages.create()` | `models/repair_master_data.py:122` |
| `create` | Override of repair stage creation: stamps the current company after creating (replaces Studio automation 'JIN Company Id in Repair Stages'). | api.model_create_multi | yes | `repair_stages._jin_set_company_id()` |  | `models/repair_master_data.py:131` |

**Server actions (1):**

- **JIN - Company Id in Repair Stages** (`action_jin_company_id_in_repair_stages`, type `code`)
  - Function: Sets the record's Company field to the user's currently selected company. Delegates to the native company setter for repair stages (record creation now does this automatically).
  - Depends on: `model repair_stages`
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
| JIN - Company Id in Repair Stages | `automation_jin_company_id_in_repair_stages` | archived | When a record is created or updated on Repair Stages, runs nothing (no action linked). **Archived — does not run.** | `model repair_stages` |  |

**Window actions (2):**

| Name | Record name | Function | Depends on | Used by |
|---|---|---|---|---|
| Repair Stages | `action_repair_stages` | Opens **Repair Stages** records (tree,form). | `model repair_stages` | `menu Fix-repair.menu_repair_stages`<br>`menu Fix-repair.menu_repair_diagnosis_repair_stages` |
| Repair Stages | `action_repair_stages_2` | Opens **Repair Stages** records (tree,form). | `model repair_stages` |  |

**Views (4):**

| Name | Record name | Type | What it changes | Function | Depends on | Used by |
|---|---|---|---|---|---|---|
| Default form view for repair_stages | `view_repair_stages_form` | form | full form layout with 5 fields | Base form screen for the Repair Stages configuration list (`repair_stages`): Name as the title, an Archived ribbon when inactive, two empty groups that Studio extensions fill, and chatter. | `repair_stages.activity_ids`<br>`repair_stages.message_follower_ids`<br>`repair_stages.message_ids`<br>`repair_stages.active`<br>`repair_stages.name` |  |
| Default list view for repair_stages | `view_repair_stages_list` | tree | full tree layout with 2 fields | Base list screen for Repair Stages (`repair_stages`): shows the Name column with a drag handle on Sequence for manual reordering. | `repair_stages.name`<br>`repair_stages.sequence` | `view Fix-repair.view_default_list_view_for_repair_stages_inherit` |
| Default search view for repair_stages | `view_repair_stages_search` | search | full search layout with 1 fields | Search screen for Repair Stages (`repair_stages`): search by Name plus an Archived filter to show inactive records. | `repair_stages.active`<br>`repair_stages.name` |  |
| Odoo Studio: Default list view for repair_stages customization | `view_default_list_view_for_repair_stages_inherit` | tree | set editable=bottom on `//tree[1]`; set column_invisible=1 on `//field[@name='sequence']`; set string=Repair Stage on `//field[@name='name']`; after `//field[@name='name']`: add field description, field accounting_company_id | Makes the Repair Stages list editable inline, hides the Sequence column, relabels Name as 'Repair Stage', and adds optional Description and Company columns. | `view Fix-repair.view_repair_stages_list`<br>`repair_stages.accounting_company_id`<br>`repair_stages.description` |  |

**Access rights (4):**

| Name | Record name | Function | Depends on | Used by |
|---|---|---|---|---|
| Repair Stages group_system | `access_repair_stages_group_system` | Gives **Administration / Settings** read/write/create/delete access to Repair Stages records. | `group base.group_system` (base)<br>`model repair_stages` |  |
| Repair Stages group_user | `access_repair_stages_group_user` | Gives **User types / Internal User** read access to Repair Stages records. | `group base.group_user` (base)<br>`model repair_stages` |  |
| repair_stages manager | `access_repair_stages_manager` | Gives **Helpdesk / Administrator** read/write/create/delete access to Repair Stages records. | `group helpdesk.group_helpdesk_manager` (helpdesk)<br>`model repair_stages` |  |
| repair_stages user | `access_repair_stages_user` | Gives **Helpdesk / User** read/write/create/delete access to Repair Stages records. | `group helpdesk.group_helpdesk_user` (helpdesk)<br>`model repair_stages` |  |

**Record rules (2):**

| Name | Record name | Function | Depends on | Used by |
|---|---|---|---|---|
| JIN - Multi-Company - Repair Stages | `rule_f7_repair_stages_jin_multi_company_repair_stages` | For everyone (global rule): read/write/create/delete on Repair Stages only where `['|', ('accounting_company_id', 'in', company_ids), ('accounting_company_id', '=', False)]`. | `model repair_stages`<br>`repair_stages.accounting_company_id` |  |
| JIN - Multi-Company - Repair Stages | `rule_jin_multi_company_repair_stages` | For everyone (global rule): read/write/create/delete on Repair Stages only where `['|', ('accounting_company_id', 'in', company_ids), ('accounting_company_id', '=', False)]`. | `model repair_stages`<br>`repair_stages.accounting_company_id` |  |
