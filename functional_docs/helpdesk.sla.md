# Fix-repair — `helpdesk.sla`

[← back to Functional_Documentation.md](../Functional_Documentation.md)

### `helpdesk.sla` — Helpdesk SLA Policies

*Extends a model created by `helpdesk`.*

**Summary:**

<!-- SUMMARY:model:helpdesk.sla -->
Purpose not evident from code. No fields, methods or views are added. The repo only ships the record rule "SLA: multi-company" (`rule_366_sla_multi_company`), which limits SLA policies to the user's allowed companies.
<!-- /SUMMARY -->

**Record rules (1):**

| Name | Record name | Function | Depends on | Used by |
|---|---|---|---|---|
| SLA: multi-company | `rule_366_sla_multi_company` | For everyone (global rule): read/write/create/delete on Helpdesk SLA Policies only where `[('company_id', 'in', company_ids)]`. | `helpdesk.sla.company_id` (helpdesk)<br>`model helpdesk.sla` (helpdesk) |  |
