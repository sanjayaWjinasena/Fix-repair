# Fix-repair — `helpdesk.stage`

[← back to Functional_Documentation.md](../Functional_Documentation.md)

### `helpdesk.stage` — Helpdesk Stage

*Extends a model created by `helpdesk`.* Python: `models/helpdesk_type_stage.py`.

**Summary:**

<!-- SUMMARY:model:helpdesk.stage -->
Adds Company (`x_studio_company_id`) to helpdesk stages, shown on the stage form. The `create` override fills it with the user's current company. This replaces Studio automation 329 "JIN - Company Id in Helpdesk Stage", which is shipped archived. The record rule "JIN - Multi-Company - Helpdesk Stage" shows stages of the user's companies plus stages without a company. A Studio tree customization adds the ID column to the stage list.
<!-- /SUMMARY -->

**Fields (1):**

| Field | Label | Type | Function | How it gets its value | Depends on | Used by |
|---|---|---|---|---|---|---|
| `x_studio_company_id` | Company | many2one → `res.company` | Company that owns the helpdesk stage, filled on create by `_jin_set_company_id`; a multi-company record rule limits stages to the user's companies. | stored | `model res.company` (base) | `helpdesk.stage._jin_set_company_id()`<br>`record rule Fix-repair.rule_616_jin_multi_company_helpdesk_stage`<br>`view Fix-repair.view_5964_odoo_studio_helpdesk_stage_form_customization_e` |

**Python methods (3):**

| Method | Function | Decorators | Extends standard | Depends on | Used by | Where |
|---|---|---|---|---|---|---|
| `_jin_set_company_id` | Sets the helpdesk stage's Company field to the user's currently selected company; used by the stage create override and the old delegated Studio action. |  |  | `helpdesk.stage.x_studio_company_id` | `helpdesk.stage.create()` | `models/helpdesk_type_stage.py:67` |
| `create` | Override of helpdesk stage creation: after creating, stamps the current company on the new stages (replaces Studio automation 'JIN Company Id in Helpdesk Stage'). | api.model_create_multi | yes | `helpdesk.stage._jin_set_company_id()` |  | `models/helpdesk_type_stage.py:79` |
| `_migrate_studio_stage_cluster_to_base` | One-off migration helper: makes the Studio Company field on helpdesk stages code-owned and removes its Studio external id. Data kept. | api.model |  | `model ir.model.data` (base)<br>`model ir.model.fields` (base) |  | `models/helpdesk_type_stage.py:88` |

**Server actions (1):**

- **JIN - Company Id in Helpdesk Stage** (`server_action_2760_jin_company_id_in_helpdesk_stage`, type `code`)
  - Function: Sets the record's Company field to the user's currently selected company. Linked to the helpdesk stage company automation.
  - Depends on: `model helpdesk.stage` (helpdesk)
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
| JIN - Company Id in Helpdesk Stage | `base_automation_329_jin_company_id_in_helpdesk_stage` | archived | When a record is created or updated on Helpdesk Stage, runs nothing (no action linked). **Archived — does not run.** | `model helpdesk.stage` (helpdesk) |  |

**Views (2):**

| Name | Record name | Type | What it changes | Function | Depends on | Used by |
|---|---|---|---|---|---|---|
| Odoo Studio: helpdesk.stage.form customization | `view_5964_odoo_studio_helpdesk_stage_form_customization_e` | form | after `//field[@name='sequence']`: add field x_studio_company_id | Helpdesk stage form: adds the Company field after Sequence. | `helpdesk.stage.x_studio_company_id`<br>`view helpdesk.helpdesk_stage_view_form` (helpdesk) |  |
| Odoo Studio: helpdesk.stages.tree customization | `view_4611_odoo_studio_helpdesk_stages_tree_customization_e` | tree | after `//field[@name='fold']`: add field id | Helpdesk stage list: adds an ID column after Folded. | `view helpdesk.helpdesk_stage_view_tree` (helpdesk) |  |

**Record rules (1):**

| Name | Record name | Function | Depends on | Used by |
|---|---|---|---|---|
| JIN - Multi-Company - Helpdesk Stage | `rule_616_jin_multi_company_helpdesk_stage` | For everyone (global rule): read/write/create/delete on Helpdesk Stage only where `['|', ('x_studio_company_id', 'in', company_ids), ('x_studio_company_id', '=', False)]`. | `helpdesk.stage.x_studio_company_id`<br>`model helpdesk.stage` (helpdesk) |  |
