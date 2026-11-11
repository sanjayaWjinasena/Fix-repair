# Fix-repair — `repair_accounts`

[← back to Functional_Documentation.md](../Functional_Documentation.md)

### `repair_accounts` — Repair Accounts

*Created by this repo.* Python: `models/repair_master_data.py`. Record name field: `name`.

Other repos that use this model: `server action BugFix-Accounting.action_rr_rug_account_update_in_si` (BugFix-Accounting)<br>`server action BugFix-Accounting.srv_rug_account_update_in_si` (BugFix-Accounting)

**Summary:**

<!-- SUMMARY:model:repair_accounts -->
A Repair Account maps a company to its RUG Account (`rug_account`). The invoice's "Change to RUG Account" button and the automatic RUG settlement read this account (see account.move). There is typically one row per company, edited from the Repair Accounts list/form. The `create` override fills Company with the user's current company. It replaces the archived Studio automation "JIN - Company Id in Repair Accounts". A multi-company record rule limits visibility to the user's companies (or rows without a company).
<!-- /SUMMARY -->

**Fields (35):**

| Field | Label | Type | Function | How it gets its value | Depends on | Used by |
|---|---|---|---|---|---|---|
| `activity_calendar_event_id` | Next Activity Calendar Event | many2one → `calendar.event` | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored | `model calendar.event` (calendar) |  |
| `activity_date_deadline` | Next Activity Deadline | date | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored |  |  |
| `activity_exception_decoration` | Activity Exception Decoration | selection: warning=Alert; danger=Error | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored |  |  |
| `activity_exception_icon` | Icon | char | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored |  |  |
| `activity_ids` | Activities | one2many → `mail.activity` | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | stored | `model mail.activity` (mail) | `view Fix-repair.view_repair_accounts_form`<br>`repair_accounts.activity_summary`<br>`repair_accounts.activity_type_icon`<br>`repair_accounts.activity_type_id` |
| `activity_state` | Activity State | selection: overdue=Overdue; today=Today; planned=Planned | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored |  |  |
| `activity_summary` | Next Activity Summary | char | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | related `activity_ids.summary`; not stored | `mail.activity.summary` (mail)<br>`repair_accounts.activity_ids` |  |
| `activity_type_icon` | Activity Type Icon | char | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | related `activity_ids.icon`; not stored | `mail.activity.icon` (mail)<br>`repair_accounts.activity_ids` |  |
| `activity_type_id` | Next Activity Type | many2one → `mail.activity.type` | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | related `activity_ids.activity_type_id`; not stored | `mail.activity.activity_type_id` (mail)<br>`model mail.activity.type` (mail)<br>`repair_accounts.activity_ids` |  |
| `activity_user_id` | Responsible User | many2one → `res.users` | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored | `model res.users` (base) |  |
| `create_date` | Created on | datetime | Date and time the record was created (automatic). | stored |  |  |
| `create_uid` | Created by | many2one → `res.users` | User who created the record (automatic). | stored | `model res.users` (base) |  |
| `display_name` | Display Name | char | Name shown for the record in lists, dropdowns and links (computed automatically by Odoo). | not stored |  |  |
| `has_message` | Has Message | boolean | Standard chatter field: tells whether the record has messages. | not stored |  |  |
| `id` | ID | integer | Unique database ID of the record (automatic). | stored |  |  |
| `message_attachment_count` | Attachment Count | integer | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_follower_ids` | Followers | one2many → `mail.followers` | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | stored | `model mail.followers` (mail) | `view Fix-repair.view_repair_accounts_form` |
| `message_has_error` | Message Delivery error | boolean | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_has_error_counter` | Number of errors | integer | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_has_sms_error` | SMS Delivery error | boolean | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_ids` | Messages | one2many → `mail.message` | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | stored | `model mail.message` (mail) | `view Fix-repair.view_repair_accounts_form` |
| `message_is_follower` | Is Follower | boolean | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_needaction` | Action Needed | boolean | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_needaction_counter` | Number of Actions | integer | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_partner_ids` | Followers (Partners) | many2many → `res.partner` | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored | `model res.partner` (base) |  |
| `my_activity_date_deadline` | My Activity Deadline | date | Standard activity field: deadline of the current user’s next activity on the record. | not stored |  |  |
| `rating_ids` | Ratings | one2many → `rating.rating` | Standard customer-rating field provided by Odoo’s rating mixin. | stored | `model rating.rating` (rating) |  |
| `website_message_ids` | Website Messages | one2many → `mail.message` | Standard chatter field: messages shown on the website/portal for this record. | stored | `model mail.message` (mail) |  |
| `write_date` | Last Updated on | datetime | Date and time the record was last changed (automatic). | stored |  |  |
| `write_uid` | Last Updated by | many2one → `res.users` | User who last changed the record (automatic). | stored | `model res.users` (base) |  |
| `active` | Active | boolean | Active flag of a Repair Accounts record; unticking it archives the entry so it no longer appears in selection lists (it can still be found with the Archived filter). | default `True`; stored |  | `default Fix-repair.default_repair_accounts_active`<br>`view Fix-repair.view_repair_accounts_form`<br>`view Fix-repair.view_repair_accounts_search` |
| `name` | Name | char | Name (Name) of the Repair Accounts entry; it is the record's display name and is shown in the list, form and search views. | stored |  | `view Fix-repair.view_repair_accounts_list`<br>`view Fix-repair.view_repair_accounts_form`<br>`view Fix-repair.view_repair_accounts_search` |
| `accounting_company_id` | Company | many2one → `res.company` | Company that owns the Repair Accounts entry, filled automatically on create by `_jin_set_company_id`; multi-company record rules use it to show users only their companies' entries. | stored | `model res.company` (base) | `record rule Fix-repair.rule_jin_multi_company_repair_accounts`<br>`record rule Fix-repair.rule_f7_repair_accounts_jin_multi_company_repair_accounts`<br>`view Fix-repair.view_default_form_view_for_repair_accounts_inherit`<br>`repair_accounts._jin_set_company_id()` |
| `rug_account` | RUG Account | many2one → `account.account` | Accounting account used for Repair-Under-Guarantee invoices in this company; the 'Change to RUG Account' button moves invoice lines to it and the RUG auto-settlement posts against it. | stored | `model account.account` (account) | `view Fix-repair.view_default_form_view_for_repair_accounts_inherit` |
| `sequence` | Sequence | integer | Ordering number that sorts Repair Accounts entries in the list view. | stored |  | `default Fix-repair.default_repair_accounts_sequence`<br>`view Fix-repair.view_repair_accounts_list` |

**Python methods (2):**

| Method | Function | Decorators | Extends standard | Depends on | Used by | Where |
|---|---|---|---|---|---|---|
| `_jin_set_company_id` | Sets the repair account's Company field to the user's currently selected company. |  |  | `repair_accounts.accounting_company_id` | `repair_accounts.create()` | `models/repair_master_data.py:23` |
| `create` | Override of repair account creation: stamps the current company after creating (replaces Studio automation 'JIN Company Id in Repair Accounts'). | api.model_create_multi | yes | `repair_accounts._jin_set_company_id()` |  | `models/repair_master_data.py:32` |

**Server actions (1):**

- **JIN - Company Id in Repair Accounts** (`action_jin_company_id_in_repair_accounts`, type `code`)
  - Function: Sets the record's Company field to the user's currently selected company. Delegates to the native company setter for repair accounts (record creation now does this automatically).
  - Depends on: `model repair_accounts`
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
| JIN - Company Id in Repair Accounts | `automation_jin_company_id_in_repair_accounts` | archived | When a record is created or updated on Repair Accounts, runs nothing (no action linked). **Archived — does not run.** | `model repair_accounts` |  |

**Window actions (1):**

| Name | Record name | Function | Depends on | Used by |
|---|---|---|---|---|
| Repair Accounts | `action_repair_accounts` | Opens **Repair Accounts** records (tree,form). | `model repair_accounts` | `menu Fix-repair.menu_repair_accounts_2`<br>`menu Fix-repair.menu_repair_accounts` |

**Views (5):**

| Name | Record name | Type | What it changes | Function | Depends on | Used by |
|---|---|---|---|---|---|---|
| Default form view for repair_accounts | `view_repair_accounts_form` | form | full form layout with 5 fields | Base form screen for the Repair Accounts configuration list (`repair_accounts`): Name as the title, an Archived ribbon when inactive, two empty groups that Studio extensions fill, and chatter. | `repair_accounts.activity_ids`<br>`repair_accounts.message_follower_ids`<br>`repair_accounts.message_ids`<br>`repair_accounts.active`<br>`repair_accounts.name` | `view Fix-repair.view_default_form_view_for_repair_accounts_inherit` |
| Default list view for repair_accounts | `view_repair_accounts_list` | tree | full tree layout with 2 fields | Base list screen for Repair Accounts (`repair_accounts`): shows the Name column with a drag handle on Sequence for manual reordering. | `repair_accounts.name`<br>`repair_accounts.sequence` | `view Fix-repair.view_default_list_view_for_repair_accounts_inherit` |
| Default search view for repair_accounts | `view_repair_accounts_search` | search | full search layout with 1 fields | Search screen for Repair Accounts (`repair_accounts`): search by Name plus an Archived filter to show inactive records. | `repair_accounts.active`<br>`repair_accounts.name` |  |
| Odoo Studio: Default form view for repair_accounts customization | `view_default_form_view_for_repair_accounts_inherit` | form | set create=true on `//form[1]`; set string=RUG Repair Accounts in Invoicing on `//group[@name='studio_group_bf46f3_left']`; inside `//group[@name='studio_group_bf46f3_left']`: add field rug_account; inside `//group[@name='studio_group_bf46f3_right']`: add field accounting_company_id | Extends the Repair Accounts form: allows creating records, titles the left group 'RUG Repair Accounts in Invoicing' with a required RUG Account field, and shows Company read-only (force-saved) on the right. | `view Fix-repair.view_repair_accounts_form`<br>`repair_accounts.accounting_company_id`<br>`repair_accounts.rug_account` |  |
| Odoo Studio: Default list view for repair_accounts customization | `view_default_list_view_for_repair_accounts_inherit` | tree | set create=true, delete=true, edit=true on `//tree[1]`; after `//field[@name='name']`: add field id | Explicitly enables create, edit and delete on the Repair Accounts list and adds an optional ID column after Name. | `view Fix-repair.view_repair_accounts_list` |  |

**Access rights (4):**

| Name | Record name | Function | Depends on | Used by |
|---|---|---|---|---|
| Repair Accounts group_system | `access_repair_accounts_group_system` | Gives **Administration / Settings** read/write/create/delete access to Repair Accounts records. | `group base.group_system` (base)<br>`model repair_accounts` |  |
| Repair Accounts group_user | `access_repair_accounts_group_user` | Gives **User types / Internal User** read access to Repair Accounts records. | `group base.group_user` (base)<br>`model repair_accounts` |  |
| repair_accounts manager | `access_repair_accounts_manager` | Gives **Helpdesk / Administrator** read/write/create/delete access to Repair Accounts records. | `group helpdesk.group_helpdesk_manager` (helpdesk)<br>`model repair_accounts` |  |
| repair_accounts user | `access_repair_accounts_user` | Gives **Helpdesk / User** read/write/create/delete access to Repair Accounts records. | `group helpdesk.group_helpdesk_user` (helpdesk)<br>`model repair_accounts` |  |

**Record rules (2):**

| Name | Record name | Function | Depends on | Used by |
|---|---|---|---|---|
| JIN - Multi-Company - Repair Accounts | `rule_f7_repair_accounts_jin_multi_company_repair_accounts` | For everyone (global rule): read/write/create/delete on Repair Accounts only where `['|', ('accounting_company_id', 'in', company_ids), ('accounting_company_id', '=', False)]`. | `model repair_accounts`<br>`repair_accounts.accounting_company_id` |  |
| JIN - Multi-Company - Repair Accounts | `rule_jin_multi_company_repair_accounts` | For everyone (global rule): read/write/create/delete on Repair Accounts only where `['|', ('accounting_company_id', 'in', company_ids), ('accounting_company_id', '=', False)]`. | `model repair_accounts`<br>`repair_accounts.accounting_company_id` |  |
