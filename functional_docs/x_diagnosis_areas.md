# Fix-repair — `x_diagnosis_areas`

[← back to Functional_Documentation.md](../Functional_Documentation.md)

### `x_diagnosis_areas` — Diagnosis Areas

*Created by this repo.* Python: `models/repair_master_data.py`, `models/x_diagnosis_areas_gap.py`. Record name field: `x_name`.

**Summary:**

<!-- SUMMARY:model:x_diagnosis_areas -->
A Diagnosis Area is the part of the machine a diagnosis refers to. It is picked on Task Diagnosis lines and groups Diagnosis Codes (`x_studio_diagnosis_area_1`). It is a company-scoped lookup list maintained under Helpdesk > Repair Diagnosis, with list, form and search views and an editable list layout. The "JIN - Company Id in Diagnosis Areas" automation stamps Company (`x_studio_company_id`) with the user's current company on create, and a multi-company record rule limits visibility to the user's companies (or rows without a company). Initial rows are seeded from `data/repair_diagnosis_seed.xml` (noupdate, so user edits are kept).
<!-- /SUMMARY -->

**Fields (35):**

| Field | Label | Type | Function | How it gets its value | Depends on | Used by |
|---|---|---|---|---|---|---|
| `activity_calendar_event_id` | Next Activity Calendar Event | many2one → `calendar.event` | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored | `model calendar.event` (calendar) |  |
| `activity_date_deadline` | Next Activity Deadline | date | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored |  |  |
| `activity_exception_decoration` | Activity Exception Decoration | selection: warning=Alert; danger=Error | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored |  |  |
| `activity_exception_icon` | Icon | char | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored |  |  |
| `activity_ids` | Activities | one2many → `mail.activity` | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | stored | `model mail.activity` (mail) | `view Fix-repair.view_4965_default_form_view_for_x_diagnosis_areas_e`<br>`view Fix-repair.view_x_diagnosis_areas_form`<br>`x_diagnosis_areas.activity_summary`<br>`x_diagnosis_areas.activity_type_icon`<br>`x_diagnosis_areas.activity_type_id` |
| `activity_state` | Activity State | selection: overdue=Overdue; today=Today; planned=Planned | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored |  |  |
| `activity_summary` | Next Activity Summary | char | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | related `activity_ids.summary`; not stored | `mail.activity.summary` (mail)<br>`x_diagnosis_areas.activity_ids` |  |
| `activity_type_icon` | Activity Type Icon | char | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | related `activity_ids.icon`; not stored | `mail.activity.icon` (mail)<br>`x_diagnosis_areas.activity_ids` |  |
| `activity_type_id` | Next Activity Type | many2one → `mail.activity.type` | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | related `activity_ids.activity_type_id`; not stored | `mail.activity.activity_type_id` (mail)<br>`model mail.activity.type` (mail)<br>`x_diagnosis_areas.activity_ids` |  |
| `activity_user_id` | Responsible User | many2one → `res.users` | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored | `model res.users` (base) |  |
| `create_date` | Created on | datetime | Date and time the record was created (automatic). | stored |  | `automation Fix-repair.base_automation_300_jin_company_id_in_diagnosis_areas` |
| `create_uid` | Created by | many2one → `res.users` | User who created the record (automatic). | stored | `model res.users` (base) |  |
| `display_name` | Display Name | char | Name shown for the record in lists, dropdowns and links (computed automatically by Odoo). | not stored |  |  |
| `has_message` | Has Message | boolean | Standard chatter field: tells whether the record has messages. | not stored |  |  |
| `id` | ID | integer | Unique database ID of the record (automatic). | stored |  |  |
| `message_attachment_count` | Attachment Count | integer | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_follower_ids` | Followers | one2many → `mail.followers` | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | stored | `model mail.followers` (mail) | `view Fix-repair.view_4965_default_form_view_for_x_diagnosis_areas_e`<br>`view Fix-repair.view_x_diagnosis_areas_form` |
| `message_has_error` | Message Delivery error | boolean | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_has_error_counter` | Number of errors | integer | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_has_sms_error` | SMS Delivery error | boolean | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_ids` | Messages | one2many → `mail.message` | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | stored | `model mail.message` (mail) | `view Fix-repair.view_4965_default_form_view_for_x_diagnosis_areas_e`<br>`view Fix-repair.view_x_diagnosis_areas_form` |
| `message_is_follower` | Is Follower | boolean | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_needaction` | Action Needed | boolean | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_needaction_counter` | Number of Actions | integer | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_partner_ids` | Followers (Partners) | many2many → `res.partner` | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored | `model res.partner` (base) |  |
| `my_activity_date_deadline` | My Activity Deadline | date | Standard activity field: deadline of the current user’s next activity on the record. | not stored |  |  |
| `rating_ids` | Ratings | one2many → `rating.rating` | Standard customer-rating field provided by Odoo’s rating mixin. | stored | `model rating.rating` (rating) |  |
| `website_message_ids` | Website Messages | one2many → `mail.message` | Standard chatter field: messages shown on the website/portal for this record. | stored | `model mail.message` (mail) |  |
| `write_date` | Last Updated on | datetime | Date and time the record was last changed (automatic). | stored |  |  |
| `write_uid` | Last Updated by | many2one → `res.users` | User who last changed the record (automatic). | stored | `model res.users` (base) |  |
| `x_active` | Active | boolean | Active flag of a Diagnosis Areas record; unticking it archives the entry so it no longer appears in selection lists (it can still be found with the Archived filter). | stored |  | `default Fix-repair.default_338_x_diagnosis_areas_x_active`<br>`view Fix-repair.view_4965_default_form_view_for_x_diagnosis_areas_e`<br>`view Fix-repair.view_4966_default_search_view_for_x_diagnosis_areas_e`<br>`view Fix-repair.view_x_diagnosis_areas_form`<br>`view Fix-repair.view_x_diagnosis_areas_search` |
| `x_name` | Diagnosis Area | char | Name (Diagnosis Area) of the Diagnosis Areas entry; it is the record's display name and is shown in the list, form and search views. | stored |  | `view Fix-repair.view_4964_default_list_view_for_x_diagnosis_areas_e`<br>`view Fix-repair.view_4965_default_form_view_for_x_diagnosis_areas_e`<br>`view Fix-repair.view_4966_default_search_view_for_x_diagnosis_areas_e`<br>`view Fix-repair.view_x_diagnosis_areas_form`<br>`view Fix-repair.view_x_diagnosis_areas_search`<details><summary>+1 more</summary>`view Fix-repair.view_x_diagnosis_areas_tree`</details> |
| `x_studio_company_id` | Company | many2one → `res.company` | Company that owns the Diagnosis Areas entry, filled by the Jin Company Id server action; multi-company record rules use it to show users only their companies' entries. | stored | `model res.company` (base) | `record rule Fix-repair.rule_555_jin_multi_company_diagnosis_areas`<br>`record rule Fix-repair.rule_f7_x_diagnosis_areas_jin_multi_company_diagnosis_areas`<br>`server action Fix-repair.sa_f5_x_diagnosis_areas_jin_company_id_in_diagnosis_areas`<br>`server action Fix-repair.server_action_2664_jin_company_id_in_diagnosis_areas`<br>`view Fix-repair.view_final_x_diagnosis_areas_odoo_studio_default_list_view_for_x_diagnosis_areas_customiz`<details><summary>+1 more</summary>`view Fix-repair.view_x_diagnosis_areas_tree_inherit`</details> |
| `x_studio_description` | Description | char | Free-text description of the Diagnosis Areas entry, shown in the list view. | stored |  | `view Fix-repair.view_final_x_diagnosis_areas_odoo_studio_default_list_view_for_x_diagnosis_areas_customiz`<br>`view Fix-repair.view_x_diagnosis_areas_tree_inherit` |
| `x_studio_sequence` | Sequence | integer | Ordering number that sorts Diagnosis Areas entries in the list view. | stored |  | `default Fix-repair.default_339_x_diagnosis_areas_x_studio_sequence`<br>`view Fix-repair.view_4964_default_list_view_for_x_diagnosis_areas_e`<br>`view Fix-repair.view_x_diagnosis_areas_tree` |

**Server actions (2):**

- **Execute Code** (`server_action_2664_jin_company_id_in_diagnosis_areas`, type `code`)
  - Function: Sets the record's Company field to the user's currently selected company. Run by the automation that stamps the company on Diagnosis Areas.
  - Depends on: `model res.company` (base), `model x_diagnosis_areas`, `x_diagnosis_areas.x_studio_company_id`
  - Used by: `automation Fix-repair.base_automation_300_jin_company_id_in_diagnosis_areas`
  <details><summary>code (5 lines)</summary>

```python

company_id = env.context.get('allowed_company_ids', [env.user.company_id.id])[0]
company = env['res.company'].browse(company_id)

record['x_studio_company_id'] = company.id
```
  </details>
- **JIN - Company Id in Diagnosis Areas** (`sa_f5_x_diagnosis_areas_jin_company_id_in_diagnosis_areas`, type `code`)
  - Function: Sets the record's Company field to the user's currently selected company. Defined for Diagnosis Areas; not referenced by any automation or view.
  - Depends on: `model res.company` (base), `model x_diagnosis_areas`, `x_diagnosis_areas.x_studio_company_id`
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
| JIN - Company Id in Diagnosis Areas | `base_automation_300_jin_company_id_in_diagnosis_areas` |  | When a record is created or updated on Diagnosis Areas, runs _Execute Code_. | `model x_diagnosis_areas`<br>`server action Fix-repair.server_action_2664_jin_company_id_in_diagnosis_areas`<br>`x_diagnosis_areas.create_date` |  |

**Window actions (2):**

| Name | Record name | Function | Depends on | Used by |
|---|---|---|---|---|
| Diagnosis Areas | `action_x_diagnosis_areas` | Opens **Diagnosis Areas** records (tree,form). | `model x_diagnosis_areas` | `menu Fix-repair.menu_repair_diagnosis_diagnosis_areas` |
| Diagnosis Areas | `act_window_2212_diagnosis_areas` | Opens **Diagnosis Areas** records (tree,form). | `model x_diagnosis_areas` | `menu Fix-repair.menu_f6_diagnosis_areas` |

**Views (8):**

| Name | Record name | Type | What it changes | Function | Depends on | Used by |
|---|---|---|---|---|---|---|
| Default form view for x_diagnosis_areas | `view_4965_default_form_view_for_x_diagnosis_areas_e` | form | full form layout with 5 fields | Base form screen for the Diagnosis Areas configuration list (`x_diagnosis_areas`): Name as the title, an Archived ribbon when inactive, two empty groups that Studio extensions fill, and chatter. | `x_diagnosis_areas.activity_ids`<br>`x_diagnosis_areas.message_follower_ids`<br>`x_diagnosis_areas.message_ids`<br>`x_diagnosis_areas.x_active`<br>`x_diagnosis_areas.x_name` |  |
| Default list view for x_diagnosis_areas | `view_4964_default_list_view_for_x_diagnosis_areas_e` | tree | full tree layout with 2 fields | Base list screen for Diagnosis Areas (`x_diagnosis_areas`): shows the Name column with a drag handle on Sequence for manual reordering. | `x_diagnosis_areas.x_name`<br>`x_diagnosis_areas.x_studio_sequence` | `view Fix-repair.view_final_x_diagnosis_areas_odoo_studio_default_list_view_for_x_diagnosis_areas_customiz` |
| Default search view for x_diagnosis_areas | `view_4966_default_search_view_for_x_diagnosis_areas_e` | search | full search layout with 1 fields | Search screen for Diagnosis Areas (`x_diagnosis_areas`): search by Name plus an Archived filter to show inactive records. | `x_diagnosis_areas.x_active`<br>`x_diagnosis_areas.x_name` |  |
| Odoo Studio: Default list view for x_diagnosis_areas customization | `view_final_x_diagnosis_areas_odoo_studio_default_list_view_for_x_diagnosis_areas_customiz` | tree | set editable=bottom on `//tree[1]`; set column_invisible=1 on `//field[@name='x_studio_sequence']`; set string=Diagnosis Area on `//field[@name='x_name']`; after `//field[@name='x_name']`: add field x_studio_description, field x_studio_company_id | Makes the Diagnosis Areas list editable inline (new rows at bottom), hides the Sequence column, relabels Name as 'Diagnosis Area', and adds optional Description and Company columns. | `view Fix-repair.view_4964_default_list_view_for_x_diagnosis_areas_e`<br>`x_diagnosis_areas.x_studio_company_id`<br>`x_diagnosis_areas.x_studio_description` |  |
| x_diagnosis_areas.form | `view_x_diagnosis_areas_form` | form | full form layout with 5 fields | Form view for Diagnosis Areas: name (required), archived ribbon and chatter; the field groups are empty. | `x_diagnosis_areas.activity_ids`<br>`x_diagnosis_areas.message_follower_ids`<br>`x_diagnosis_areas.message_ids`<br>`x_diagnosis_areas.x_active`<br>`x_diagnosis_areas.x_name` |  |
| x_diagnosis_areas.search | `view_x_diagnosis_areas_search` | search | full search layout with 1 fields | Search view for Diagnosis Areas: search by name, plus an Archived filter. | `x_diagnosis_areas.x_active`<br>`x_diagnosis_areas.x_name` |  |
| x_diagnosis_areas.tree | `view_x_diagnosis_areas_tree` | tree | full tree layout with 2 fields | Base list view for Diagnosis Areas: drag handle for sequence and name. | `x_diagnosis_areas.x_name`<br>`x_diagnosis_areas.x_studio_sequence` | `view Fix-repair.view_x_diagnosis_areas_tree_inherit` |
| x_diagnosis_areas.tree.inherit | `view_x_diagnosis_areas_tree_inherit` | tree | set editable=bottom on `//tree[1]`; set column_invisible=1 on `//field[@name='x_studio_sequence']`; set string=Diagnosis Area on `//field[@name='x_name']`; after `//field[@name='x_name']`: add field x_studio_description, field x_studio_company_id | Makes the Diagnosis Areas list editable inline, hides the sequence column, labels the name 'Diagnosis Area', and adds Description and Company columns. | `view Fix-repair.view_x_diagnosis_areas_tree`<br>`x_diagnosis_areas.x_studio_company_id`<br>`x_diagnosis_areas.x_studio_description` |  |

**Access rights (4):**

| Name | Record name | Function | Depends on | Used by |
|---|---|---|---|---|
| Diagnosis Areas group_system | `access_1788_diagnosis_areas_group_system` | Gives **Administration / Settings** read/write/create/delete access to Diagnosis Areas records. | `group base.group_system` (base)<br>`model x_diagnosis_areas` |  |
| Diagnosis Areas group_user | `access_1789_diagnosis_areas_group_user` | Gives **User types / Internal User** read access to Diagnosis Areas records. | `group base.group_user` (base)<br>`model x_diagnosis_areas` |  |
| x_diagnosis_areas manager | `access_x_diagnosis_areas_manager` | Gives **Helpdesk / Administrator** read/write/create/delete access to Diagnosis Areas records. | `group helpdesk.group_helpdesk_manager` (helpdesk)<br>`model x_diagnosis_areas` |  |
| x_diagnosis_areas user | `access_x_diagnosis_areas_user` | Gives **Helpdesk / User** read/write/create/delete access to Diagnosis Areas records. | `group helpdesk.group_helpdesk_user` (helpdesk)<br>`model x_diagnosis_areas` |  |

**Record rules (2):**

| Name | Record name | Function | Depends on | Used by |
|---|---|---|---|---|
| JIN - Multi-Company - Diagnosis Areas | `rule_f7_x_diagnosis_areas_jin_multi_company_diagnosis_areas` | For everyone (global rule): read/write/create/delete on Diagnosis Areas only where `['|', ('x_studio_company_id', 'in', company_ids), ('x_studio_company_id', '=', False)]`. | `model x_diagnosis_areas`<br>`x_diagnosis_areas.x_studio_company_id` |  |
| JIN - Multi-Company - Diagnosis Areas | `rule_555_jin_multi_company_diagnosis_areas` | For everyone (global rule): read/write/create/delete on Diagnosis Areas only where `['|', ('x_studio_company_id', 'in', company_ids), ('x_studio_company_id', '=', False)]`. | `model x_diagnosis_areas`<br>`x_diagnosis_areas.x_studio_company_id` |  |
