# Fix-repair — `helpdesk.team`

[← back to Functional_Documentation.md](../Functional_Documentation.md)

### `helpdesk.team` — Helpdesk Team

*Extends a model created by `helpdesk`.*

Other repos that use this model: `report BugFix-Studio-Misc.action_report_3491_helpdesk_team_report` (BugFix-Studio-Misc)<br>`window action BugFix-Studio-Misc.act_window_2239_customer_letter_report_d7` (BugFix-Studio-Misc)<br>`window action BugFix-Studio-Misc.act_window_2876_helpdesk_team_helpdesk_team_d7` (BugFix-Studio-Misc)

**Summary:**

<!-- SUMMARY:model:helpdesk.team -->
Adds no fields or Python code. The team kanban dashboard gets quick-create enabled, and its kanban menu template is replaced (`helpdesk_team_kanban_no_menu`). The repo also ships two window actions (Customer Letter Report, Helpdesk Team) and the helpdesk team record rules: administrator, user privacy visibility, multi-company, and public access to published teams.
<!-- /SUMMARY -->

**Window actions (2):**

| Name | Record name | Function | Depends on | Used by |
|---|---|---|---|---|
| Customer Letter Report | `act_window_2239_customer_letter_report` | Opens **Helpdesk Team** records (kanban,tree,form). | `model helpdesk.team` (helpdesk) | `menu BugFix-Studio-Misc.menu_f6_customer_letter_report` (BugFix-Studio-Misc) |
| Helpdesk Team (helpdesk.team) | `act_window_2876_helpdesk_team_helpdesk_team` | Opens **Helpdesk Team** records (kanban,tree,form). | `model helpdesk.team` (helpdesk) | `menu BugFix-Studio-Misc.menu_f6_helpdesk_team_helpdesk_team` (BugFix-Studio-Misc)<br>`menu BugFix-Studio-Misc.menu_f6r2_test_app_05_projects_helpdesk_team_helpdesk_team` (BugFix-Studio-Misc) |

**Views (2):**

| Name | Record name | Type | What it changes | Function | Depends on | Used by |
|---|---|---|---|---|---|---|
| Odoo Studio: helpdesk.team.dashboard customization | `ported_odoo_studio_helpdesk_28046b65_e20c_4a5e_8a99_12fc2676bd8f` | kanban | set quick_create=true on `//kanban[1]` | Helpdesk team dashboard kanban: enables quick create. | `view helpdesk.helpdesk_team_view_kanban` (helpdesk) |  |
| helpdesk.team.kanban.no.menu | `helpdesk_team_kanban_no_menu` | kanban | replace `//templates/t[@t-name='kanban-menu']`: add t | Helpdesk team kanban: removes the card dropdown menu. | `view helpdesk.helpdesk_team_view_kanban` (helpdesk) |  |

**Record rules (4):**

| Name | Record name | Function | Depends on | Used by |
|---|---|---|---|---|
| Helpdesk Administrator | `rule_360_helpdesk_administrator` | For Helpdesk / Administrator: read/write/create/delete on Helpdesk Team with no record filter (empty domain = all records). | `group helpdesk.group_helpdesk_manager` (helpdesk)<br>`model helpdesk.team` (helpdesk) |  |
| Helpdesk User | `rule_362_helpdesk_user` | For Helpdesk / User: read/write/create/delete on Helpdesk Team only where `['|',
                                            ('privacy_visibility', '!=', 'invited_internal'),
                                            ('message_partner_ids', 'in', [user.partner_id.id])
                                        ]`. | `group helpdesk.group_helpdesk_user` (helpdesk)<br>`helpdesk.team.message_partner_ids` (helpdesk)<br>`helpdesk.team.privacy_visibility` (helpdesk)<br>`model helpdesk.team` (helpdesk) |  |
| Public User: Published Helpdesk Team | `rule_695_public_user_published_helpdesk_team` | For User types / Public: read/write/create/delete on Helpdesk Team only where `[('website_published', '=', True)]`. | `group base.group_public` (base)<br>`helpdesk.team.website_published` (website_helpdesk)<br>`model helpdesk.team` (helpdesk) |  |
| Team: multi-company | `rule_365_team_multi_company` | For everyone (global rule): read/write/create/delete on Helpdesk Team only where `[('company_id', 'in', company_ids)]`. | `helpdesk.team.company_id` (helpdesk)<br>`model helpdesk.team` (helpdesk) |  |
