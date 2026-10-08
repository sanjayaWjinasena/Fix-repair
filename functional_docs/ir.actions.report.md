# Fix-repair — `ir.actions.report`

[← back to Functional_Documentation.md](../Functional_Documentation.md)

### `ir.actions.report` — Report Action

*Extends a model created by `base`.* Python: `models/ir_actions_report.py`.

Other repos that use this model: `bugfix_sales.minimum_sales_margin.seed._attach_c01_intro_conclusion_view()` (BugFix-Sales)

**Summary:**

<!-- SUMMARY:model:ir.actions.report -->
Overrides `_get_report` for the standard quotation report `sale.action_report_saleorder`. If that XML ID is missing (for example after Studio replaced the report), it falls back to the first PDF report on sale.order, so the customer portal accept flow still works.
<!-- /SUMMARY -->

**Python methods (1):**

| Method | Function | Decorators | Extends standard | Depends on | Used by | Where |
|---|---|---|---|---|---|---|
| `_get_report` | Report lookup override: if the standard sale order report (`sale.action_report_saleorder`) is missing, falls back to the first PDF report for sale orders so the portal quotation-accept flow still works. |  | yes |  |  | `models/ir_actions_report.py:8` |
