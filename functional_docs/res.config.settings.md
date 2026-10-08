# Fix-repair — `res.config.settings`

[← back to Functional_Documentation.md](../Functional_Documentation.md)

### `res.config.settings` — Config Settings

*Extends a model created by `base`.* Python: `models/res_config_settings.py`.

Other repos that use this model: `access right BugFix-Sales.access_1531_res_config_settings_group_system` (BugFix-Sales)<br>`access right BugFix-Sales.access_1532_res_config_settings_group_user` (BugFix-Sales)<br>`access right BugFix-Studio-Misc.access_res_config_settings_group_system` (BugFix-Studio-Misc)<br>`server action BugFix-Accounting.server_action_1370_imp_update_consignment_pi` (BugFix-Accounting)<br>`server action BugFix-Accounting.srv_imp_update_consignment_pi` (BugFix-Accounting)<br>`server action BugFix-Stock.server_action_1318_imp_allocate_consignment_header_charges` (BugFix-Stock)

**Summary:**

<!-- SUMMARY:model:res.config.settings -->
Adds the setting Factory Repair Location (`factory_repair_location_id`), an internal stock location. A repair item arrives there when its ticket reaches Received at Factory. The value is saved per company in the system parameter `fix_repair.factory_repair_location.<company_id>` through `get_values`/`set_values`. It is shown in a Fix-repair block on the Settings page.
<!-- /SUMMARY -->

**Fields (1):**

| Field | Label | Type | Function | How it gets its value | Depends on | Used by |
|---|---|---|---|---|---|---|
| `factory_repair_location_id` | Factory Repair Location | many2one → `stock.location` | Settings option: internal stock location where items land when a repair ticket reaches 'Received at Factory'; saved per company as a system parameter. | stored | `model stock.location` (stock) | `res.config.settings.set_values()`<br>`view Fix-repair.res_config_settings_view_form_fix_repair` |

**Python methods (2):**

| Method | Function | Decorators | Extends standard | Depends on | Used by | Where |
|---|---|---|---|---|---|---|
| `get_values` | Settings loader: reads the per-company Factory Repair Location from system parameters and shows it in Settings if the location still exists. | api.model | yes | `model ir.config_parameter` (base)<br>`model stock.location` (stock) |  | `models/res_config_settings.py:22` |
| `set_values` | Settings saver: stores the chosen Factory Repair Location in a per-company system parameter (`fix_repair.factory_repair_location.<company>`). |  | yes | `model ir.config_parameter` (base)<br>`res.config.settings.factory_repair_location_id`<br>`stock.location.id` (stock) |  | `models/res_config_settings.py:35` |

**Views (1):**

| Name | Record name | Type | What it changes | Function | Depends on | Used by |
|---|---|---|---|---|---|---|
| res.config.settings.form.fix.repair | `res_config_settings_view_form_fix_repair` | form | inside `//form`: add app | Settings: adds a 'Fix Repair' section (administrators only) with the per-company Factory Repair Location setting. | `group base.group_system` (base)<br>`res.config.settings.factory_repair_location_id`<br>`view base_setup.res_config_settings_view_form` (base_setup) |  |
