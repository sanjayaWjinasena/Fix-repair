# Fix-repair — `x_task_diagnosis`

[← back to Functional_Documentation.md](../Functional_Documentation.md)

### `x_task_diagnosis` — Task Diagnosis

*Created by this repo.* Python: `models/x_task_diagnosis.py`, `models/x_task_diagnosis_gap.py`. Record name field: `x_name`.

Other repos that use this model: `server action BugFix-Studio-Misc.server_action_2799_mst_odoo_data_clean_up` (BugFix-Studio-Misc)

**Summary:**

<!-- SUMMARY:model:x_task_diagnosis -->
A Task Diagnosis is one line in the Repair Diagnosis tab of an FSM repair task (`x_studio_task_id`, the inverse of `project.task.x_studio_diagnosis_ids`). Each line has a sequence, a description, and dropdowns for Condition, Symptom Area/Code, Diagnosis Area/Code, Reason, Sub Reason, Resolution and Repair Stage. The task checks these lines (Valid Diagnosis) before the repair can continue. The repo ships list, form and search views and a Task Diagnosis window action. There are no automations.
<!-- /SUMMARY -->

**Fields (44):**

| Field | Label | Type | Function | How it gets its value | Depends on | Used by |
|---|---|---|---|---|---|---|
| `activity_calendar_event_id` | Next Activity Calendar Event | many2one → `calendar.event` | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored | `model calendar.event` (calendar) |  |
| `activity_date_deadline` | Next Activity Deadline | date | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored |  |  |
| `activity_exception_decoration` | Activity Exception Decoration | selection: warning=Alert; danger=Error | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored |  |  |
| `activity_exception_icon` | Icon | char | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored |  |  |
| `activity_ids` | Activities | one2many → `mail.activity` | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | stored | `model mail.activity` (mail) | `view Fix-repair.view_4986_default_form_view_for_x_task_diagnosis_e`<br>`view Fix-repair.view_x_task_diagnosis_form`<br>`x_task_diagnosis.activity_summary`<br>`x_task_diagnosis.activity_type_icon`<br>`x_task_diagnosis.activity_type_id` |
| `activity_state` | Activity State | selection: overdue=Overdue; today=Today; planned=Planned | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored |  |  |
| `activity_summary` | Next Activity Summary | char | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | related `activity_ids.summary`; not stored | `mail.activity.summary` (mail)<br>`x_task_diagnosis.activity_ids` |  |
| `activity_type_icon` | Activity Type Icon | char | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | related `activity_ids.icon`; not stored | `mail.activity.icon` (mail)<br>`x_task_diagnosis.activity_ids` |  |
| `activity_type_id` | Next Activity Type | many2one → `mail.activity.type` | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | related `activity_ids.activity_type_id`; not stored | `mail.activity.activity_type_id` (mail)<br>`model mail.activity.type` (mail)<br>`x_task_diagnosis.activity_ids` |  |
| `activity_user_id` | Responsible User | many2one → `res.users` | Standard activity field (scheduled to-dos, calls, meetings on the record) provided by Odoo’s activity mixin. | not stored | `model res.users` (base) |  |
| `create_date` | Created on | datetime | Date and time the record was created (automatic). | stored |  |  |
| `create_uid` | Created by | many2one → `res.users` | User who created the record (automatic). | stored | `model res.users` (base) |  |
| `display_name` | Display Name | char | Name shown for the record in lists, dropdowns and links (computed automatically by Odoo). | not stored |  |  |
| `has_message` | Has Message | boolean | Standard chatter field: tells whether the record has messages. | not stored |  |  |
| `id` | ID | integer | Unique database ID of the record (automatic). | stored |  |  |
| `message_attachment_count` | Attachment Count | integer | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_follower_ids` | Followers | one2many → `mail.followers` | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | stored | `model mail.followers` (mail) | `view Fix-repair.view_4986_default_form_view_for_x_task_diagnosis_e`<br>`view Fix-repair.view_x_task_diagnosis_form` |
| `message_has_error` | Message Delivery error | boolean | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_has_error_counter` | Number of errors | integer | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_has_sms_error` | SMS Delivery error | boolean | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_ids` | Messages | one2many → `mail.message` | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | stored | `model mail.message` (mail) | `view Fix-repair.view_4986_default_form_view_for_x_task_diagnosis_e`<br>`view Fix-repair.view_x_task_diagnosis_form` |
| `message_is_follower` | Is Follower | boolean | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_needaction` | Action Needed | boolean | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_needaction_counter` | Number of Actions | integer | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored |  |  |
| `message_partner_ids` | Followers (Partners) | many2many → `res.partner` | Standard chatter field (messages, followers, attachments) provided by Odoo’s mail thread mixin. | not stored | `model res.partner` (base) |  |
| `my_activity_date_deadline` | My Activity Deadline | date | Standard activity field: deadline of the current user’s next activity on the record. | not stored |  |  |
| `rating_ids` | Ratings | one2many → `rating.rating` | Standard customer-rating field provided by Odoo’s rating mixin. | stored | `model rating.rating` (rating) |  |
| `website_message_ids` | Website Messages | one2many → `mail.message` | Standard chatter field: messages shown on the website/portal for this record. | stored | `model mail.message` (mail) |  |
| `write_date` | Last Updated on | datetime | Date and time the record was last changed (automatic). | stored |  |  |
| `write_uid` | Last Updated by | many2one → `res.users` | User who last changed the record (automatic). | stored | `model res.users` (base) |  |
| `x_active` | Active | boolean | Active flag of a Task Diagnosis record; unticking it archives the entry so it no longer appears in selection lists (it can still be found with the Archived filter). | stored |  | `default Fix-repair.default_355_x_task_diagnosis_x_active`<br>`view Fix-repair.view_4986_default_form_view_for_x_task_diagnosis_e`<br>`view Fix-repair.view_4987_default_search_view_for_x_task_diagnosis_e`<br>`view Fix-repair.view_x_task_diagnosis_form`<br>`view Fix-repair.view_x_task_diagnosis_search` |
| `x_name` | Name | char | Name (Name) of the Task Diagnosis entry; it is the record's display name and is shown in the list, form and search views. | stored |  | `view Fix-repair.view_4985_default_list_view_for_x_task_diagnosis_e`<br>`view Fix-repair.view_4986_default_form_view_for_x_task_diagnosis_e`<br>`view Fix-repair.view_4987_default_search_view_for_x_task_diagnosis_e`<br>`view Fix-repair.view_project_task_repair_diagnosis`<br>`view Fix-repair.view_x_task_diagnosis_form`<details><summary>+2 more</summary>`view Fix-repair.view_x_task_diagnosis_search`<br>`view Fix-repair.view_x_task_diagnosis_tree`</details> |
| `x_studio_condition` | Condition | many2one → `x_conditions` | Condition of the item, chosen from the Conditions list, on the diagnosis line. | stored | `model x_conditions` | `view Fix-repair.view_project_task_repair_diagnosis` |
| `x_studio_description` | Description | char | Free-text description of the diagnosis line; not used by any view or logic listed for this repo. | stored |  | `view Fix-repair.view_project_task_repair_diagnosis` |
| `x_studio_diagnosis_area` | Diagnosis Area | many2one → `x_diagnosis_areas` | Diagnosis area chosen from the Diagnosis Areas list on the diagnosis line. | stored | `model x_diagnosis_areas` | `view Fix-repair.view_project_task_repair_diagnosis` |
| `x_studio_diagnosis_code` | Diagnosis Code | many2one → `x_diagnosis_codes` | Diagnosis code chosen from the Diagnosis Codes list on the diagnosis line. | stored | `model x_diagnosis_codes` | `view Fix-repair.view_project_task_repair_diagnosis` |
| `x_studio_reason` | Reason | many2one → `x_repair_reason` | Repair reason chosen from the Repair Reason list on the diagnosis line. | stored | `model x_repair_reason` | `view Fix-repair.view_project_task_repair_diagnosis` |
| `x_studio_repair_stage` | Repair Stage | many2one → `x_repair_stages` | Repair stage, chosen from the Repair Stages list, that the diagnosis line refers to. | stored | `model x_repair_stages` | `view Fix-repair.view_project_task_repair_diagnosis` |
| `x_studio_resolution` | Resolution | many2one → `x_resolutions` | Resolution applied, chosen from the Resolutions list, on the diagnosis line. | stored | `model x_resolutions` | `view Fix-repair.view_project_task_repair_diagnosis` |
| `x_studio_sequence` | Sequence | integer | Ordering number that sorts Task Diagnosis entries in the list view (default 10). | default `10`; stored |  | `default Fix-repair.default_356_x_task_diagnosis_x_studio_sequence`<br>`view Fix-repair.view_4985_default_list_view_for_x_task_diagnosis_e`<br>`view Fix-repair.view_project_task_repair_diagnosis`<br>`view Fix-repair.view_x_task_diagnosis_tree` |
| `x_studio_sub_reason` | Sub Reason | many2one → `x_repair_sub_reason` | Repair sub-reason chosen from the Repair Sub Reason list on the diagnosis line. | stored | `model x_repair_sub_reason` | `view Fix-repair.view_project_task_repair_diagnosis` |
| `x_studio_symptom_area` | Symptom Area | many2one → `x_symptom_areas` | Symptom area chosen from the Symptom Areas list on the diagnosis line. | stored | `model x_symptom_areas` | `view Fix-repair.view_project_task_repair_diagnosis` |
| `x_studio_symptom_code` | Symptom Code | many2one → `x_symptom_codes` | Symptom code chosen from the Symptom Codes list on the diagnosis line. | stored | `model x_symptom_codes` | `view Fix-repair.view_project_task_repair_diagnosis` |
| `x_studio_task_id` | Task | many2one → `project.task` | Repair task this diagnosis line belongs to; shown in the diagnosis list. | stored | `model project.task` (project) | `view Fix-repair.view_final_x_task_diagnosis_odoo_studio_default_list_view_for_x_task_diagnosis_customiza`<br>`view Fix-repair.view_project_task_repair_diagnosis`<br>`view Fix-repair.view_x_task_diagnosis_tree_inherit` |

**Window actions (1):**

| Name | Record name | Function | Depends on | Used by |
|---|---|---|---|---|
| Task Diagnosis | `act_window_2217_task_diagnosis` | Opens **Task Diagnosis** records (tree,form). | `model x_task_diagnosis` | `menu BugFix-Studio-Misc.menu_f6r2_test_app_05_task_diagnosis` (BugFix-Studio-Misc) |

**Views (8):**

| Name | Record name | Type | What it changes | Function | Depends on | Used by |
|---|---|---|---|---|---|---|
| Default form view for x_task_diagnosis | `view_4986_default_form_view_for_x_task_diagnosis_e` | form | full form layout with 5 fields | Base form screen for the Task Diagnosis configuration list (`x_task_diagnosis`): Name as the title, an Archived ribbon when inactive, two empty groups that Studio extensions fill, and chatter. | `x_task_diagnosis.activity_ids`<br>`x_task_diagnosis.message_follower_ids`<br>`x_task_diagnosis.message_ids`<br>`x_task_diagnosis.x_active`<br>`x_task_diagnosis.x_name` |  |
| Default list view for x_task_diagnosis | `view_4985_default_list_view_for_x_task_diagnosis_e` | tree | full tree layout with 2 fields | Base list screen for Task Diagnosis (`x_task_diagnosis`): shows the Name column with a drag handle on Sequence for manual reordering. | `x_task_diagnosis.x_name`<br>`x_task_diagnosis.x_studio_sequence` | `view Fix-repair.view_final_x_task_diagnosis_odoo_studio_default_list_view_for_x_task_diagnosis_customiza` |
| Default search view for x_task_diagnosis | `view_4987_default_search_view_for_x_task_diagnosis_e` | search | full search layout with 1 fields | Search screen for Task Diagnosis (`x_task_diagnosis`): search by Name plus an Archived filter to show inactive records. | `x_task_diagnosis.x_active`<br>`x_task_diagnosis.x_name` |  |
| Odoo Studio: Default list view for x_task_diagnosis customization | `view_final_x_task_diagnosis_odoo_studio_default_list_view_for_x_task_diagnosis_customiza` | tree | set editable=bottom on `//tree[1]`; after `//field[@name='x_name']`: add field x_studio_task_id | Makes the Task Diagnosis list editable inline (new rows at bottom) and adds a hidden Task Id column after Name. | `view Fix-repair.view_4985_default_list_view_for_x_task_diagnosis_e`<br>`x_task_diagnosis.x_studio_task_id` |  |
| x_task_diagnosis.form | `view_x_task_diagnosis_form` | form | full form layout with 5 fields | Form view for Task Diagnosis: name (required), archived ribbon and chatter; the field groups are empty. | `x_task_diagnosis.activity_ids`<br>`x_task_diagnosis.message_follower_ids`<br>`x_task_diagnosis.message_ids`<br>`x_task_diagnosis.x_active`<br>`x_task_diagnosis.x_name` |  |
| x_task_diagnosis.search | `view_x_task_diagnosis_search` | search | full search layout with 1 fields | Search view for Task Diagnosis: search by name, plus an Archived filter. | `x_task_diagnosis.x_active`<br>`x_task_diagnosis.x_name` |  |
| x_task_diagnosis.tree | `view_x_task_diagnosis_tree` | tree | full tree layout with 2 fields | Base list view for Task Diagnosis: drag handle for sequence and name. | `x_task_diagnosis.x_name`<br>`x_task_diagnosis.x_studio_sequence` | `view Fix-repair.view_x_task_diagnosis_tree_inherit` |
| x_task_diagnosis.tree.inherit | `view_x_task_diagnosis_tree_inherit` | tree | set editable=bottom on `//tree[1]`; after `//field[@name='x_name']`: add field x_studio_task_id | Makes the Task Diagnosis list editable inline and adds a hidden Task Id column. | `view Fix-repair.view_x_task_diagnosis_tree`<br>`x_task_diagnosis.x_studio_task_id` |  |

**Access rights (4):**

| Name | Record name | Function | Depends on | Used by |
|---|---|---|---|---|
| Task Diagnosis group_system | `access_1798_task_diagnosis_group_system` | Gives **Administration / Settings** read/write/create/delete access to Task Diagnosis records. | `group base.group_system` (base)<br>`model x_task_diagnosis` |  |
| Task Diagnosis group_user | `access_1799_task_diagnosis_group_user` | Gives **User types / Internal User** read access to Task Diagnosis records. | `group base.group_user` (base)<br>`model x_task_diagnosis` |  |
| x_task_diagnosis helpdesk manager | `access_x_task_diagnosis_helpdesk_manager` | Gives **Helpdesk / Administrator** read/write/create/delete access to Task Diagnosis records. | `group helpdesk.group_helpdesk_manager` (helpdesk)<br>`model x_task_diagnosis` |  |
| x_task_diagnosis helpdesk user | `access_x_task_diagnosis_helpdesk_user` | Gives **Helpdesk / User** read/write/create/delete access to Task Diagnosis records. | `group helpdesk.group_helpdesk_user` (helpdesk)<br>`model x_task_diagnosis` |  |
