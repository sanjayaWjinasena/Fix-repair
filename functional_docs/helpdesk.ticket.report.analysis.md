# Fix-repair — `helpdesk.ticket.report.analysis`

[← back to Functional_Documentation.md](../Functional_Documentation.md)

### `helpdesk.ticket.report.analysis` — Ticket Analysis

*Extends a model created by `helpdesk`.*

**Summary:**

<!-- SUMMARY:model:helpdesk.ticket.report.analysis -->
Purpose not evident from code. No fields or methods are added. The repo ships the "Success Rate Analysis" window action (pivot/graph, filtered to tickets closed on or after 2025-03-11) and three record rules on the ticket analysis report: multi-company, helpdesk user and helpdesk administrator.
<!-- /SUMMARY -->

**Window actions (1):**

| Name | Record name | Function | Depends on | Used by |
|---|---|---|---|---|
| Success Rate Analysis | `act_window_1802_success_rate_analysis` | Opens **Ticket Analysis** records (pivot,graph), filtered to `[('close_date', '>=', '2025-03-11 10:18:26')]`. | `helpdesk.ticket.report.analysis.close_date` (helpdesk)<br>`model helpdesk.ticket.report.analysis` (helpdesk) |  |

**Record rules (3):**

| Name | Record name | Function | Depends on | Used by |
|---|---|---|---|---|
| Helpdesk Ticket Report: Helpdesk Ticket Administrator | `rule_679_helpdesk_ticket_report_helpdesk_ticket_administrator` | For Helpdesk / Administrator: read/write/create/delete on Ticket Analysis with no record filter (empty domain = all records). | `group helpdesk.group_helpdesk_manager` (helpdesk)<br>`model helpdesk.ticket.report.analysis` (helpdesk) |  |
| Helpdesk Ticket Report: Helpdesk Ticket User | `rule_396_helpdesk_ticket_report_helpdesk_ticket_user` | For Helpdesk / User: read/write/create/delete on Ticket Analysis only where `[
                '|', 
                    ('team_id.privacy_visibility', '!=', 'invited_internal'),
                    '|',
                        ('team_id.message_partner_ids', 'in', [user.partner_id.id]),
                        ('ticket_id.message_partner_ids', 'in', [user.partner_id.id]),
            ]`. | `group helpdesk.group_helpdesk_user` (helpdesk)<br>`helpdesk.team.message_partner_ids` (helpdesk)<br>`helpdesk.team.privacy_visibility` (helpdesk)<br>`helpdesk.ticket.message_partner_ids` (helpdesk)<br>`helpdesk.ticket.report.analysis.team_id` (helpdesk)<details><summary>+2 more</summary>`helpdesk.ticket.report.analysis.ticket_id` (helpdesk)<br>`model helpdesk.ticket.report.analysis` (helpdesk)</details> |  |
| Helpdesk Ticket Report: multi-company | `rule_395_helpdesk_ticket_report_multi_company` | For everyone (global rule): read/write/create/delete on Ticket Analysis only where `[('company_id', 'in', company_ids + [False])]`. | `helpdesk.ticket.report.analysis.company_id` (helpdesk)<br>`model helpdesk.ticket.report.analysis` (helpdesk) |  |
