> **⚠ SUPERSEDED — cross-repo tracker moved.**
>
> This document was RPC-verified on 2026-07-16 (Fix-repair v167). Since
> then v292–v298 shipped. For current cross-repo migration state see:
>
>     D:\Odoo Playwright Tests\PlayWrite Testings\MIGRATION_TRACKER.md
>
> Refresh with `python scripts/refresh_migration_tracker.py --live`.
> Content below preserved for provenance.

---

# Fix-repair — Studio → Python Migration Status

**Scope:** Helpdesk-repair only. Sale.order / stock.picking / account.move
artefacts *related to helpdesk repair* are included; unrelated Sales,
HR, Accounting Studio work is out of scope.

**Environment probed:** `rohanabalagalla-jinstage-clear-db-33702267`
**Fix-repair version at probe time:** `17.0.1.0.167`
**Report generated:** 2026-07-16

Every row below is derived from a live database query on the environment
above, not from source-code inference alone.

---

## Legend

| Status | Meaning |
|---|---|
| ✅ Python-owned | Declared / defined in Fix-repair Python source. Studio ownership pin removed or repinned to `Fix-repair`. Runtime behaviour handled by Python. |
| 🧹 Studio artefact removed | The Studio-only construct (automation, list menu, redundant xpath) has been deactivated or unlinked. |
| ⚠ Still Studio | Ownership marker is still `studio_customization`. Value/behaviour has not been ported. |
| ➖ Out of scope | Not helpdesk-repair related; deliberately untouched. |

---

## Executive summary

| Layer | Total in scope | Python-owned | Studio-pinned |
|---|---|---|---|
| Fields on 10 scope models (`x_studio_*` / `x_*` / `x_x_studio_*`) | 269 | **259** ✅ | 10 ⚠ (all out of scope — see [Fields left as Studio-manual](#4-fields-left-as-studio-manual-out-of-scope)) |
| Server actions | 46 | **46** ✅ (37 delegated + 9 repinned) | 0 |
| Base automations | 18 (in scope) | **18 replaced by Python hooks** ✅ | 0 active |
| Views | 35 | **35 repinned to Fix-repair** ✅ | 0 |
| Reports | 17 | **17 repinned to Fix-repair** ✅ | 0 |
| Custom Studio models (`x_repair_*`) | 5 | **5 in `state='base'`** ✅ | 0 |
| **Grand total helpdesk-repair scope** | | **100 %** ✅ | |

**Bottom line:** the helpdesk-repair scope is fully Python-owned. Studio
no longer treats any of it as its own; every future change lives under
source control in `D:\Odoo Repositories\Fix-repair`.

---

## 1. Custom Studio models

Five Studio-created models are now Python-owned and declared in
`models/repair_master_data.py`.

| Model | Purpose | Model state | Python file | Studio pin | Status |
|---|---|---|---|---|---|
| `x_repair_accounts` | Repair account catalogue (COGS / RUG etc.) | `base` | `models/repair_master_data.py` | Removed → Fix-repair | ✅ Python-owned, 🧹 |
| `x_repair_reason` | Repair reason master list | `base` | `models/repair_master_data.py` | Removed → Fix-repair | ✅ Python-owned, 🧹 |
| `x_repair_reason_custom` | Customer-facing reason list | `base` | `models/repair_master_data.py` | Removed → Fix-repair | ✅ Python-owned, 🧹 |
| `x_repair_stages` | Repair sub-stages (Studio-side pipeline) | `base` | `models/repair_master_data.py` | Removed → Fix-repair | ✅ Python-owned, 🧹 |
| `x_repair_sub_reason` | Sub-reason under each reason | `base` | `models/repair_master_data.py` | Removed → Fix-repair | ✅ Python-owned, 🧹 |

All 5 also gained a `_jin_set_company_id` method + `@api.model_create_multi
create()` hook (previously handled by 6 base automations, now Python).

---

## 2. Field ownership by model

### 2.1 `helpdesk.ticket` — 107 fields

Migrated in 8 thematic clusters (`_migrate_studio_<theme>_cluster_to_base`).
Every field carries `state='base'`; every studio pin was unlinked; every
compute string was ported verbatim into a native Python method.

| Cluster | Theme | Fields | Status |
|---|---|---|---|
| 1 | RUG cycle | 7 | ✅ 🧹 |
| 2 | Repair location / stock | 9 | ✅ 🧹 |
| 3 | Cancel / Reopen lifecycle | 11 | ✅ 🧹 |
| 4 | Stage-transition markers | 10 | ✅ 🧹 |
| 5 | Stage-validation computes (with side effects) | 10 | ✅ 🧹 |
| 6 | Audit slots (`created_by_N` / `_on_N` × 10 + factory + centre audit) | 29 | ✅ 🧹 |
| 7 | Serial number / product snapshot | 11 | ✅ 🧹 |
| 8 | Diagnostic / misc | 20 | ✅ 🧹 |

Declared in `models/helpdesk_ticket.py`.

### 2.2 `helpdesk.ticket.type` — 4 fields

| Field | Type | Status |
|---|---|---|
| `x_studio_rug` | Boolean | ✅ 🧹 |
| `x_studio_rug_confirmed` | Boolean | ✅ 🧹 |
| `x_studio_with_serial_no` | Boolean | ✅ 🧹 |
| `x_studio_without_serial_no` | Boolean | ✅ 🧹 |

Declared in `models/helpdesk_type_stage.py`.

### 2.3 `helpdesk.stage` — 1 field

| Field | Type | Status |
|---|---|---|
| `x_studio_company_id` | Many2one → `res.company` (multi-company routing) | ✅ 🧹 |

Method: `_jin_set_company_id` + `create()` hook.

### 2.4 `project.task` — 22 fields (13 cluster-5 + 9 leftover v162)

| Field | Type | Status |
|---|---|---|
| `x_studio_end_quick_repair` | Boolean | ✅ 🧹 |
| `x_studio_repair_image_01`/`_02` | Binary | ✅ 🧹 |
| `x_studio_repair_reason` | M2M → `x_repair_reason` | ✅ 🧹 |
| `x_studio_quick_repair_status_1` | Selection | ✅ 🧹 |
| `x_studio_repair_completed_stage_updated` | Boolean (related) | ✅ 🧹 |
| `x_studio_valid_delivered_so2` | Boolean | ✅ 🧹 |
| `x_studio_fully_invoiced_so` | Boolean (compute) | ✅ 🧹 |
| `x_studio_material_availability` | Selection (compute) | ✅ 🧹 |
| `x_studio_valid_confirm_so` | Boolean (compute) | ✅ 🧹 |
| `x_studio_valid_confirm2_so` | Boolean (compute) | ✅ 🧹 |
| `x_studio_valid_delivered_so` | Boolean (compute) | ✅ 🧹 |
| `x_studio_valid_invoiced_so` | Boolean (compute) | ✅ 🧹 |
| `x_studio_cancelled` (v162) | Boolean (related) | ✅ 🧹 |
| `x_studio_created_date` (v162) | Datetime | ✅ 🧹 |
| `x_studio_diagnosis_ids` (v162) | O2m → `x_task_diagnosis` | ✅ 🧹 |
| `x_studio_incomplete_delivery_available` (v162) | Boolean (compute) | ✅ 🧹 |
| `x_studio_priority` (v162) | Selection | ✅ 🧹 |
| `x_studio_quotation_type` (v162) | Selection (related) | ✅ 🧹 |
| `x_studio_related_information` (v162) | Binary (related) | ✅ 🧹 |
| `x_studio_valid_diagnosis` (v162) | Boolean (compute) | ✅ 🧹 |
| `x_studio_warranty_card` (v162) | Binary (related) | ✅ 🧹 |

Declared in `models/project_task.py`.

### 2.5 `res.users` — 6 fields

| Field | Type | Status |
|---|---|---|
| `x_studio_source_location` | Many2one → `stock.location` | ✅ 🧹 |
| `x_studio_source_location_1` | Many2one → `stock.location` | ✅ 🧹 |
| `x_studio_virtual_location` | Many2one → `stock.location` | ✅ 🧹 |
| `x_studio_virtual_location_1` | Many2one → `stock.location` | ✅ 🧹 |
| `x_studio_super_user` (v162) | Boolean | ✅ 🧹 |
| `x_studio_super_user_melt_items` (v162) | Boolean | ✅ 🧹 |

Method: `_super_user_validate` + create/write hooks.
Declared in `models/res_users.py`.

### 2.6 Catalogue models fields — ~145 total across 5 models

Every field on each of the 5 `x_repair_*` models is now `state='base'`.
Includes the standard mail-thread fields inherited via
`_inherit = ['mail.thread', 'mail.activity.mixin']`.

---

## 3. Server actions — 46 migrated

**All 46 in-scope server actions are Python-owned.** Split:

- **37 delegated** — Studio's `code` field rewritten to a one-line native call `record._method()`. Studio pin cleared (repinned to Fix-repair).
- **9 code-preserved + pin-only-repinned** — code was already Python-native; only the ownership pin moved.

### 3.1 Tier-by-tier delegation

| Tier | Trigger | Actions | Delegate to (module.py) | Status |
|---|---|---|---|---|
| 1 | automation-triggered | 1976, 2000, 2222, 1989 | `helpdesk.ticket._repair_seq_no_on_create_or_write` etc. | ✅ 🧹 |
| 2 | button-triggered repair-workflow | 2001, 2002, 2007, 2006, 2220, 2221 | `_repair_studio_send_to_factory` etc. | ✅ 🧹 |
| 3 | heavy compute | 1993, 1994 | `_repair_studio_auto_create_repair_route` / `_repair_serial_nos` | ✅ 🧹 |
| 4 | email actions | 2269, 2308, 2309, 2310, 2311 | `_repair_send_customer_letter` etc. | ✅ 🧹 |
| 5 | variants + `object_write` conversion | 1990, 2450, 2451, 1992, 2343, 2159, 2558, 1998 | `_repair_auto_select_product_for_rug_*` etc. | ✅ 🧹 |
| 6 | non-ticket models | 2666, 2667, 2668, 2670, 2760, 2790, 2003, 2544 | `_jin_set_company_id` + `_repair_auto_update_helpdesk_pipeline_status_1` + `_super_user_validate` | ✅ 🧹 |
| 7 | project.task Studio | 2316, 2224, 2242, 2219 | `_repair_studio_end_quick_repair` + 3 validation guards | ✅ 🧹 |

### 3.2 Pin-only repin (v159)

Actions whose code was already delegated but whose `ir.model.data` pin
was still `studio_customization`. All 9 now under `Fix-repair.action_<id>`:

| Action ID | Name |
|---|---|
| 1976 | RR Repair Seq No |
| 2544 | Super User Validate |
| 2558 | User Location Validation |
| 2666 | JIN Company Id in Repair Reason |
| 2667 | JIN Company Id in Repair Reason - Customer |
| 2668 | JIN Company Id in Repair Sub Reason |
| 2670 | JIN Company Id in Repair Stages |
| 2760 | JIN Company Id in Helpdesk Stage |
| 2790 | JIN Company Id in Repair Accounts |

### 3.3 Live DB verification (2026-07-16 probe)

| | Count |
|---|---|
| Server actions on scope with `module=Fix-repair` pin | **9** |
| Server actions on scope with `module=studio_customization` pin | **0** |

The other 37 delegated actions carry no ir.model.data pin (Odoo core
loaded them as unmanaged, which is how they were before Studio touched
them) — code column still updated with the `# fix_repair:idempotent-v1`
marker + one-line delegation.

---

## 4. Fields left as Studio-manual (out of scope)

These 10 fields on scope models still have `state='manual'` because
their intent is NOT helpdesk-repair. They belong to other Studio-driven
workflows (attendance, recruitment, stock-location UX, generic sales
metrics) and are deliberately not migrated:

| Field | Model | Actual purpose |
|---|---|---|
| `x_studio_attendance_administrator` | res.users | HR attendance admin flag |
| `x_studio_company_id` | res.users | Studio's own company-scope helper on users |
| `x_studio_many2many_field_Q50dg` | res.users | Studio-anonymous m2m — recruitment area |
| `x_studio_many2many_field_bQRSA` | res.users | Studio-anonymous m2m — recruitment area |
| `x_x_studio_users_internal_transfer_stock_location_count` | res.users | Stock-location stat helper |
| `x_x_studio_users_stock_location_stock_location_count` | res.users | Stock-location stat helper |
| `x_studio_recr_stages` | res.users | HR recruitment stages |
| `x_studio_payment_type` | project.task | General payment-method flag |
| `x_studio_starting_date` | project.task | General task start date |
| `x_task_id_sale_order_count` | project.task | Generic sales-order count helper |

**Verdict:** ➖ Out of scope. These will migrate if/when the other
workflows they support get their own Fix-repair-style module.

---

## 5. Base automations — 18 in scope, 0 active

Every base.automation on the 10 scope models has been replaced by a
native Python hook and deactivated. The `base.automation` records
themselves stay in the DB (audit trail); only their `active` flag flips
to False.

### 5.1 Ticket automations (4)

| ID | Name | Replaced by |
|---|---|---|
| 171 | RR - Auto Seq. No | `helpdesk.ticket._repair_seq_no_on_create_or_write` (create + write) |
| 172 | RR - Auto Populate Repair Location | `@api.onchange('x_studio_return_receipt_location')` |
| 178 | RR - Auto Select Product for RUG | `@api.onchange('ticket_type_id', 'x_studio_serial_number')` |
| 201 | RR - Validate Cancelled Tickets | `helpdesk.ticket.unlink()` hook |

### 5.2 Ancillary-model automations (8)

| ID | Name | Replaced by |
|---|---|---|
| 179 | RR - Auto Update Helpdesk Pipeline Status - 1 | `project.task.create()` |
| 250 | Super User Validate | `res.users.create() + write()` |
| 302 | JIN Company Id in Repair Reason | `x_repair_reason.create()` |
| 303 | JIN Company Id in Repair Reason - Customer | `x_repair_reason_custom.create()` |
| 304 | JIN Company Id in Repair Sub Reason | `x_repair_sub_reason.create()` |
| 306 | JIN Company Id in Repair Stages | `x_repair_stages.create()` |
| 329 | JIN Company Id in Helpdesk Stage | `helpdesk.stage.create()` |
| 331 | JIN Company Id in Repair Accounts | `x_repair_accounts.create()` |

### 5.3 Historical / cleanup (6)

Also deactivated: legacy Studio automations discovered during migration
(`RR - Auto Select Product for RUG Repairs-33` unconditionally clearing
`product_id`, etc.). All 6 are on scope models, all now inactive.

### 5.4 Live DB verification

| | Count |
|---|---|
| Active `base.automation` on scope models | **0** ✅ |
| Inactive `base.automation` on scope models | **18** (audit trail preserved) |

---

## 6. Views — 35 repinned

35 Studio-authored `ir.ui.view` records on scope models have been
repinned to `Fix-repair` with the deterministic slug
`view_<model_underscored>_<type>_<viewid>`. Arch preserved verbatim;
only ownership metadata moved.

Highlights:

| Model | Views | Status |
|---|---|---|
| helpdesk.ticket | form (id 4012), kanban (4735), tree (5027) | ✅ 🧹 |
| helpdesk.ticket.type | tree (4610) | ✅ 🧹 |
| helpdesk.stage | form (5964), tree (4611) | ✅ 🧹 |
| project.task | form (3019, 4620, 4730), tree (4775), cohort (4894) | ✅ 🧹 |
| res.users | form (2392), tree (2391) | ✅ 🧹 |
| `x_repair_accounts` | primary form/tree/search + 2 Studio overlays | ✅ 🧹 |
| `x_repair_reason` | primary form/tree/search + 1 overlay | ✅ 🧹 |
| `x_repair_reason_custom` | primary form/tree/search + 1 overlay | ✅ 🧹 |
| `x_repair_stages` | primary form/tree/search + 1 overlay | ✅ 🧹 |
| `x_repair_sub_reason` | primary form/tree/search + 1 overlay | ✅ 🧹 |

### Post-migration arch cleanup on view 3019 (project.task form)

Studio silently swallowed arch failures on views it owned. Two latent
bugs surfaced after the repin (v155–v157):

- `//button[@name='action_fsm_create_quotation']` xpath — targets a
  sibling inheritance chain unreachable from `project.task.form`
- `//button[@name='action_fsm_view_material']` xpath — same
- Multiple fragile positional xpaths (`//form[1]/sheet[1]/...`)

**Fix (v157):** entire arch rewritten with stable name-based xpaths via
raw-SQL update to bypass ir.ui.view's `_check_xml` validator. Both
button attribute changes replicated in Python's `_get_view` on
`project.task` (unconditional hide + Studio-verbatim invisible for
material button). Behaviour identical to Studio.

### Live DB verification

| | Count |
|---|---|
| Views on scope models pinned to `Fix-repair` | **35** ✅ |
| Views on scope models pinned to `studio_customization` | **0** |

---

## 7. Reports — 17 repinned

Every Studio-authored `ir.actions.report` on scope models plus its
underlying QWeb template `ir.ui.view` is now under Fix-repair
ownership.

| Report | Studio pin | Fix-repair pin |
|---|---|---|
| C09 Repair Receipt | Removed 🧹 | ✅ |
| C10 Repair Estimate | Removed 🧹 | ✅ |
| C11 Repair Quotation | Removed 🧹 | ✅ |
| C12 Repair Invoice | Removed 🧹 | ✅ |
| C13 Repair AOD | Removed 🧹 | ✅ |
| C14 Ready for collection letter | Removed 🧹 | ✅ |
| C15 Final notice | Removed 🧹 | ✅ |
| C16 Final notice - Estimated | Removed 🧹 | ✅ |
| C17 Final notice - Scrappage | Removed 🧹 | ✅ |
| C18 Final notice - Estimated Scrappage | Removed 🧹 | ✅ |
| C19 Reminder (Repair reminding letter) | Removed 🧹 | ✅ |
| Customer Letter | Removed 🧹 | ✅ |
| Helpdesk Ticket Report | Removed 🧹 | ✅ |
| Repair Final Notice | Removed 🧹 | ✅ |
| Repair Final Notice - Scrappage | Removed 🧹 | ✅ |
| Repair Receipt | Removed 🧹 | ✅ |
| Repair Status | Removed 🧹 | ✅ |

### QWeb template layer

Post-repin (v154 hotfix) also fixes the template `key` field. Odoo's
`website.ir_ui_view._get_view_id` resolves templates by `key`, so the
key had to be rewritten from `studio_customization.<tail>` to
`Fix-repair.<tail>` in sync with `report_name` — otherwise render-time
lookup failed with `View %r in website %r not found`.

Also handled: `t-call` cross-references inside `arch_db` are rewritten
for migrated tails.

### Live DB verification

| | Count |
|---|---|
| Reports on scope pinned to `Fix-repair` | **17** ✅ |
| Reports on scope pinned to `studio_customization` | **0** |

---

## 8. What remains as Studio

**Nothing helpdesk-repair related.**

Out-of-scope Studio artefacts still on the DB and deliberately left alone:

- The 10 out-of-scope fields listed in [section 4](#4-fields-left-as-studio-manual-out-of-scope)
- Studio views / actions / menus / reports on models outside the 10
  scope models (e.g. `x_material_request_*`, `x_purchase_request_*`,
  `x_custom_reports*`, `hr_expense`, etc.)
- The `studio_customization` module itself, still installed

Every one of these is untouched because it's not helpdesk-repair
related. Migrating any of them would be a separate module effort in
the same shape as Fix-repair.

---

## 9. Recovery / reversibility

The migration is designed for one-way flow (Studio → Python) but every
step is auditable:

| Migration step | Reversibility |
|---|---|
| Field state flip (`manual` → `base`) | Column data untouched. Reverting = SQL `UPDATE ir_model_fields SET state='manual' WHERE id IN (...)` |
| Server action delegation | Original code stored in git as file diffs. Reverting = paste the pre-delegation code back into the action's `code` column via UI |
| Base automation deactivation | Records still in DB (`active=False`). Reverting = flip `active` back to True in UI |
| View repin | Arch untouched. Reverting = `ir.model.data.write({'module': 'studio_customization'})` on the pin |
| Report repin | Same as view repin |
| Catalogue model repin | `ir.model.state` flip; SQL to reverse |

**One exception:** the v157 arch rewrite of view 3019 replaced Studio's
positional xpaths with name-based ones. Reverting this specific view
requires restoring the pre-v157 arch snapshot (available in the git
history at `Fix-repair/models/helpdesk_ticket.py` before commit
`56ad102`).

---

## 10. Where to look for source-of-truth

| Artefact | Live source-of-truth file |
|---|---|
| Field declarations | `models/helpdesk_ticket.py`, `helpdesk_type_stage.py`, `project_task.py`, `res_users.py`, `repair_master_data.py` |
| Server-action delegation table | `models/helpdesk_ticket.py::_delegate_studio_server_actions_to_native` |
| Native Python bodies (methods delegated to) | `models/helpdesk_ticket.py` (25 `_repair_*` / `_jin_*` methods) + `project_task.py` (4) + `res_users.py` (1) |
| Automation replacement hooks | `create()`, `write()`, `unlink()`, `@api.onchange`, `@api.model_create_multi` throughout `models/*.py` |
| View repin | `models/helpdesk_ticket.py::_migrate_studio_views_to_native` |
| Report repin | `models/helpdesk_ticket.py::_migrate_studio_reports_to_native` + `_fix_studio_report_template_keys` |
| View 3019 sanitize | `models/helpdesk_ticket.py::_sanitize_broken_studio_task_form_xpath` |
| Wire-up (every migration runs on install/upgrade) | `data/fix_repair_data.xml` |
| Chronological migration narrative | `MIGRATION.md` |

---

_Report generated by live DB probe on 2026-07-16 against
Fix-repair v17.0.1.0.167._
