# Fix-repair — `x_repair_master_data.migration`

[← back to Functional_Documentation.md](../Functional_Documentation.md)

### `x_repair_master_data.migration` — Repair Master Data — Studio→Python migration helper

*Created by this repo.* Python: `models/repair_master_data.py`.

**Summary:**

<!-- SUMMARY:model:x_repair_master_data.migration -->
A technical abstract model with no records. Its single method, `_migrate_studio_repair_master_data_to_base`, moves the repair catalogue models and their fields from Studio to this module: it changes the model and field rows from state 'manual' to 'base' and removes the `studio_customization` XML IDs. The method can be run more than once safely, and the existing tables and data are kept.
<!-- /SUMMARY -->

**Python methods (1):**

| Method | Function | Decorators | Extends standard | Depends on | Used by | Where |
|---|---|---|---|---|---|---|
| `_migrate_studio_repair_master_data_to_base` | One-off migration helper: switches the Studio repair master-data models (accounts, reasons, stages, sub reasons, conditions, diagnosis/symptom areas and codes, resolutions) and their fields to code-owned via SQL and removes Studio external ids. Data kept. | api.model |  | `model ir.model.data` (base)<br>`model ir.model.fields` (base)<br>`model ir.model` (base) |  | `models/repair_master_data.py:307` |
