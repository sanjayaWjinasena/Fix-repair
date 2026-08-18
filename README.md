# Fix Repair

**Version:** 17.0.1.0.167
**Odoo base:** 17.0 (Enterprise)
**Category:** Helpdesk
**Author:** Jinasena Agricultural Machinery (Pvt) Ltd.
**License:** LGPL-3

Fix-repair is the primary Odoo module for the Customer Care – Repair
workflow. It layers on top of Odoo Helpdesk + Field Service + Sales +
Sale-Stock and drives the end-to-end repair lifecycle: intake, stock
movements, quotation, RUG / non-RUG customer-pays branches, repair
completion, invoicing, and dispatch.

The module also owns the long-running Studio → Python migration for
this environment (see [`MIGRATION.md`](MIGRATION.md) and
[`STUDIO_MIGRATION_STATUS.md`](STUDIO_MIGRATION_STATUS.md)) — every
Studio-authored helpdesk-repair artefact in the DB has been claimed by
this module's Python source.

---

## Table of contents

1. [Scope](#1-scope)
2. [Runtime dependencies](#2-runtime-dependencies)
3. [Module layout](#3-module-layout)
4. [Feature areas](#4-feature-areas)
   - 4.1 Repair movement lifecycle
   - 4.2 Sale-order workflow gates
   - 4.3 RUG / non-RUG customer-pays branch
   - 4.4 Re-estimate flow
   - 4.5 Advance-payment plumbing
   - 4.6 Confirm-button validation stack
   - 4.7 Invoice creation (single full invoice for non-RUG)
   - 4.8 Delivery Validate + Dispatch payment gates
   - 4.9 Reports
5. [Models & fields](#5-models--fields)
6. [Python methods per model](#6-python-methods-per-model)
7. [Automation replacements (Python hooks)](#7-automation-replacements-python-hooks)
8. [Server-action delegation](#8-server-action-delegation)
9. [View overrides](#9-view-overrides)
10. [Settings](#10-settings)
11. [Development notes](#11-development-notes)
12. [Related documents](#12-related-documents)

---

## 1. Scope

**In scope — everything helpdesk-repair related:**

- `helpdesk.ticket` — every field, view, and workflow button on the
  ticket form
- `helpdesk.ticket.type` and `helpdesk.stage` — repair-workflow
  type/stage helpers
- `project.task` — the FSM task that fills the repair job
- `res.users` — repair-specific location fields + super-user gate
- `sale.order` — repair quotations (Repair type: warranty / RUG /
  Reject-RUG / customer-pays); non-repair SOs are only touched
  where they share a code path
- `account.move` + `account.payment.register` — RUG invoice logic,
  advance-payment threshold on the payment wizard
- `stock.picking`, `stock.return.picking`, `stock.location`,
  `stock.warehouse`, `stock.lot` — repair movement lifecycle
- Five custom Studio catalogue models (`x_repair_accounts`,
  `x_repair_reason`, `x_repair_reason_custom`, `x_repair_stages`,
  `x_repair_sub_reason`)

**Out of scope (not touched):**

- Plain Sales / Project / non-repair workflows (those live in
  BugFix-Sales)
- HR, recruitment, accounting-only, purchase Studio work
- Non-Repair Studio fields even on the models Fix-repair inherits (10
  such fields on `res.users` and `project.task` are deliberately left
  as `state='manual'` — see [`STUDIO_MIGRATION_STATUS.md`](STUDIO_MIGRATION_STATUS.md)
  section 4)

## 2. Runtime dependencies

```python
'depends': [
    'base_setup',
    'helpdesk',
    'helpdesk_fsm',
    'sale',
    'sale_stock',
    'industry_fsm_sale',
    'industry_fsm_stock',
    'BugFix-Sales',   # sale.order sub-fixes + minimum-sales-margin config
],
```

`BugFix-Sales` is a companion module for cross-cutting Sales workflow
fixes. Fix-repair depends on it explicitly so upgrade order is
enforced.

## 3. Module layout

```
Fix-repair/
├── __manifest__.py
├── __init__.py
├── MIGRATION.md                    # Chronological Studio→Python migration log
├── STUDIO_MIGRATION_STATUS.md      # Inventory of every migrated artefact
├── CHANGES.txt                     # Legacy changelog (kept for history)
│
├── models/
│   ├── __init__.py
│   ├── account_move.py             # RUG invoice + Change-to-RUG-Account button
│   ├── account_payment_register.py # Advance-payment threshold guard on wizard
│   ├── helpdesk_ticket.py          # Master file — 107+ x_studio_* fields, 25
│   │                                 native Python methods, 12 automation hooks,
│   │                                 all Studio migration methods
│   ├── helpdesk_type_stage.py      # helpdesk.ticket.type + helpdesk.stage
│   ├── ir_actions_report.py        # Report helpers
│   ├── project_task.py             # 22 x_studio_* fields + repair-workflow
│   │                                 view arch injection via _get_view
│   ├── repair_master_data.py       # 5 catalogue models
│   │                                 (x_repair_accounts, _reason,
│   │                                  _reason_custom, _stages, _sub_reason)
│   ├── res_config_settings.py      # Settings dropdown: Factory Repair Location
│   ├── res_users.py                # 6 x_studio_* fields + super-user validator
│   ├── sale_order.py               # SO workflow gates, Confirm predicates,
│   │                                 x_repair_customer_pays, Studio compute
│   │                                 delegation, RUG approve/reject buttons,
│   │                                 single-full-invoice flow, tax_totals_json
│   ├── stock_location.py           # 'repair' usage on stock.location
│   ├── stock_lot.py                # Serial-lot repair-workflow hooks
│   ├── stock_picking.py            # Delivery Validate gate (nuw_block_validate)
│   │                                 + repair-lifecycle _action_done Paths A/B/C
│   ├── stock_return_picking.py     # Return picking name/type wiring; phantom
│   │                                 reuse for the Return wizard
│   └── stock_warehouse.py          # Intransit + Repair location seeding
│
├── data/
│   └── fix_repair_data.xml         # <function> calls for every migration and
│                                     seed on install/upgrade
│
├── views/
│   ├── helpdesk_ticket_views.xml   # Native ticket form additions
│   ├── res_config_settings_views.xml # Settings block host
│   └── sale_report_templates.xml   # QWeb report inheritance
```

## 4. Feature areas

### 4.1 Repair movement lifecycle

Every physical hop of the item is a stock movement stamped with
`x_studio_helpdesk_ticket_id` so the ticket's Movements smart button
surfaces them.

- **Receipt at branch:** the customer drop-off. `stock.return.picking`
  reversed from a synthesised `PHAN` phantom picking. Wizard reuse
  logic prevents orphan phantoms building up.
- **Send to Factory:** current location → factory warehouse Intransit
- **Received at Factory:** factory Intransit → factory Stock (via
  `_ensure_intransit_location`)
- **Plan Intervention:** current location → warehouse `Repair`
  virtual location (via `_ensure_repair_location`)
- **Mark as Done:** reverses the Plan Intervention hop back to prior
  source (Centre Repair keeps at centre virtual; Factory Repair returns
  the item to factory Intransit anchor)
- **Send to Sales Centre:** current location → centre Intransit
- **Received at Sales Centre:** centre Intransit → centre virtual
  repair location
- **Dispatch:** stock.return.picking off the customer-receipt to
  reverse it back to the customer. Names use `<WH>/RET/xxxxx` sequence.

Location model additions:

- `stock.location.usage='repair'` value (custom)
- `<WH>/Repair` child locations seeded on every warehouse
- `<WH>/Intransit` locations seeded where missing (`usage='transit'`)

### 4.2 Sale-order workflow gates

- **Set to Quotation** button hidden at all times (`action_draft`)
- **Send PRO-FORMA Invoice + Cancel** hidden on the SO form
- **Register Payment** hidden on RUG-confirmed invoices
- **Cancel** appears after the first quotation email is sent
- **Create Advance Payment** shown only on confirmed Sales quotations

### 4.3 RUG / non-RUG customer-pays branch

RUG = Reject Under Guarantee — the customer's warranty claim is
rejected and the customer pays. Two flags:

| Flag | Meaning |
|---|---|
| `x_repair_customer_pays` | True from the start (NUW — Not Under Warranty). Set by `project_task._sync_repair_flags` from `ticket.x_studio_rug_confirmed`. |
| `x_studio_rug_rejected` | Set later after the RUG cycle rejects a warranty repair. |

Every "customer pays" check in the codebase reads the union:
`order.x_repair_customer_pays or order.x_studio_rug_rejected`.

The NUW → `x_repair_customer_pays` migration is one-way and
data-preserving. `_migrate_nuw_to_customer_pays_flag` runs on every
install/upgrade, no-ops when nothing to migrate.

### 4.4 Re-estimate flow

- Button visible on both `helpdesk.ticket` and `sale.order` form
- Injected via `_get_view` so no hard module upgrade is needed to
  see the button
- Resets SO to `draft`, clears customer signature, keeps existing
  pickings (new lines merge into them rather than creating fresh
  pickings)
- Hidden on cancelled SOs and cancelled tickets

### 4.5 Advance-payment plumbing

- **Two Advance Payment journals** auto-seeded with inbound Manual
  payment method lines (Odoo 17's `account.payment` validation
  requires `payment_method_line_id`; Studio's "Create Advance
  Payment" action creates payments on these journals)
- `payment_account_id` (Outstanding Receipts) also seeded on the
  method lines
- Studio's "Create Advance Payment" action was passing `record.id`
  into `x_studio_project_no_1` (a Many2one → project.project), causing
  FK violations. Rewritten to pass `record.x_studio_project_no.id`.

### 4.6 Confirm-button validation stack

`sale.order.action_confirm` is layered with a compound `invisible=`
expression on the Confirm button (all scoped to Repair
quotation_type by default; universal ones apply everywhere):

| Gate | Scope | What it checks |
|---|---|---|
| Overdue debt | universal | `partner_id.total_overdue == 0` |
| Valid Order Lines | universal | at least one non-service order line |
| Expired quotation | universal | `date_order` still within validity window |
| Over-commission | Sales + Project | commission % not exceeded |
| Margin-exceed | Sales + Project | negative-margin lines require override |
| Bank Guarantee | Credit-payment | `x_studio_bank_guarantee_approved` |
| Project Budget | Project | project inventory / budget headroom |
| Credit Limit | Credit-payment | `partner_id.credit_limit` respected |
| Customer signature | Reject-RUG + NUW | `x_customer_signed` set from portal |
| Stock availability | Repair | resupply-pool availability check |

### 4.7 Invoice creation (single full invoice for non-RUG)

**Before v163**, non-RUG repair SOs went through Odoo's standard
two-invoice down-payment flow. **v163 replaced that with a single
full-invoice flow.**

- Purple **Create Invoice** button repointed to
  `action_repair_create_invoice` (`type='object'`, no wizard)
- Non-RUG branch: `_create_repair_full_invoice()` builds ONE
  `account.move` for the entire SO using `product_uom_qty`
  (ordered qty) on every line, ignoring `invoice_policy='delivery'`
- RUG-approved branch: falls through to standard `_create_invoices()`
- Percentage advance button hidden on every Repair SO
- Button auto-hides once any non-cancelled invoice exists on the SO;
  reappears if the invoice is cancelled

### 4.8 Delivery Validate + Dispatch payment gates

**Delivery Validate (`stock.picking.button_validate`):**

For customer-pays repair pickings, `nuw_block_validate` is True until
at least one non-cancelled invoice on the linked SO has
`payment_state in ('partial', 'in_payment', 'paid')`. The button is
hidden AND the server-side override in `button_validate` raises a
matching UserError, so URL / API bypasses are also blocked.

**Dispatch button (`helpdesk.ticket` action 195 wrapper):**

`so_fully_paid` is True only when every non-cancelled invoice on the
task SO is `state='posted' AND payment_state in ('in_payment',
'paid')`. Draft invoices don't count. Bypasses: `is_tested_ok` and
`is_so_cancelled` tickets never invoice, so the payment gate is
skipped for them.

### 4.9 Reports

`views/sale_report_templates.xml` inherits `sale.report_saleorder_document`
to add the Document Introduction / Conclusion blocks (feature owned
by BugFix-Sales; the inherit target lives here for repair-scope
reports).

The 17 Studio-authored helpdesk-repair reports (C09–C19, Customer
Letter, Repair Receipt, Repair Status, etc.) are all under
`Fix-repair` ownership via runtime repin — see
[`STUDIO_MIGRATION_STATUS.md`](STUDIO_MIGRATION_STATUS.md) section 7.

## 5. Models & fields

Model-by-model summary. Every field listed is Python-declared
(`state='base'`); computed fields have their compute string ported
verbatim from Studio into a Python method.

### 5.1 `helpdesk.ticket` (`models/helpdesk_ticket.py`)

**107 x_studio_* fields** across 8 clusters:

| Cluster | Theme | # |
|---|---|---|
| 1 | RUG cycle | 7 |
| 2 | Repair location / stock | 9 |
| 3 | Cancel / Reopen lifecycle | 11 |
| 4 | Stage-transition markers | 10 |
| 5 | Stage-validation computes (with side effects) | 10 |
| 6 | Audit slots (`created_by_N` / `_on_N` × 10 + factory + centre) | 29 |
| 7 | Serial number / product snapshot | 11 |
| 8 | Diagnostic / misc | 20 |

**Native (non-Studio) fields:**

- `ticket_repair_stage_state` — Char compute
- `so_fully_paid` — Boolean compute (Dispatch gate)
- `is_tested_ok`, `is_so_cancelled` — Boolean computes
- `so_invoice_status` — Char related
- `has_return_picking`, `has_ready_dispatch_picking` — Boolean computes
- `repair_picking_ids` — One2many to `stock.picking`
- `repair_picking_count` — Integer compute

### 5.2 `helpdesk.ticket.type` (`models/helpdesk_type_stage.py`)

- `x_studio_rug` — Boolean
- `x_studio_rug_confirmed` — Boolean
- `x_studio_with_serial_no` — Boolean
- `x_studio_without_serial_no` — Boolean

### 5.3 `helpdesk.stage` (`models/helpdesk_type_stage.py`)

- `x_studio_company_id` — Many2one → `res.company` (multi-company routing)

### 5.4 `project.task` (`models/project_task.py`)

**Cluster 5 (13 fields):** end_quick_repair, repair_image_01/02,
repair_reason (M2M), quick_repair_status_1,
repair_completed_stage_updated (related), valid_delivered_so2,
fully_invoiced_so (compute), material_availability (compute),
valid_confirm_so / valid_confirm2_so / valid_delivered_so /
valid_invoiced_so (all computes).

**Leftover v162 (9 fields):** cancelled (related), created_date,
diagnosis_ids (One2many to x_task_diagnosis), incomplete_delivery_available
(compute), priority, quotation_type (related), related_information
(related), valid_diagnosis (compute), warranty_card (related).

**Native additions:** ticket_repair_stage_state (compute), so_cancelled
(compute).

### 5.5 `res.users` (`models/res_users.py`)

- 4 location fields: `x_studio_source_location`, `_source_location_1`,
  `_virtual_location`, `_virtual_location_1` (all Many2one → stock.location)
- 2 super-user booleans: `x_studio_super_user`, `x_studio_super_user_melt_items`

### 5.6 `sale.order` (`models/sale_order.py`)

**Native additions:**

- `x_repair_customer_pays` — Boolean, replaces NUW quotation type
- `tax_totals_json` — Char alias, computed from `tax_totals` via
  `json.dumps` (Studio's arch expects the Odoo-16 attribute name)
- `x_repair_stock_ok` — Boolean compute (repair-scope stock availability)
- `ticket_repair_stage_state` — Char compute
- Numerous native compute methods that back Studio compute strings
  after `_delegate_studio_computes_to_native` runs

### 5.7 Custom catalogue models (`models/repair_master_data.py`)

Each declared as its own Python class with `mail.thread` + `mail.activity.mixin`
inherited:

| Model | Fields | Purpose |
|---|---|---|
| `x_repair_accounts` | `x_studio_company_id`, `x_studio_sequence` | Repair account catalogue |
| `x_repair_reason` | Same | Repair reason master |
| `x_repair_reason_custom` | Same | Customer-facing reason list |
| `x_repair_stages` | Same | Repair sub-stages |
| `x_repair_sub_reason` | Same | Sub-reason under each reason |

## 6. Python methods per model

### 6.1 `helpdesk.ticket` (`models/helpdesk_ticket.py`)

**Studio-migrated method names** (delegated to by rewritten server
actions):

- `_repair_seq_no_on_create_or_write`, `_repair_populate_repair_location`,
  `_repair_validate_cancelled_on_unlink`, `_repair_auto_select_product_for_rug`
- `_repair_studio_send_to_factory`, `_repair_studio_receive_at_factory`,
  `_repair_studio_send_to_sales_centre`, `_repair_studio_receive_at_sales_centre`
- `_repair_studio_cancel_repair`, `_repair_studio_reopen_repair`
- `_repair_studio_auto_create_repair_route`,
  `_repair_studio_auto_create_repair_serial_nos`
- `_repair_send_customer_letter`, `_repair_send_final_notice`,
  `_repair_send_final_notice_estimated`, `_repair_send_final_notice_scrappage`,
  `_repair_send_reminding_letter`
- `_repair_auto_select_product_for_rug_2/_22/_33/_4`
- `_repair_studio_cancel_repair_2`,
  `_repair_studio_change_repair_type_to_rug`,
  `_repair_studio_user_location_validation`,
  `_repair_studio_update_rug_approval_in_pipeline`

**Native operational methods:**

- `action_send_to_factory`, `action_received_at_factory`,
  `action_send_to_sales_centre`, `action_received_at_sales_centre`
- `action_generate_fsm_task` (Plan Intervention wrapper)
- `_create_send_to_factory_picking`, `_create_received_at_factory_picking`,
  `_create_send_to_sales_centre_picking`,
  `_create_received_at_sales_centre_picking`,
  `_create_plan_intervention_picking`, `_create_mark_as_done_picking`
- `_create_repair_transfer` — core state='done' picking builder
- `_current_item_location`, `_get_factory_repair_location`
- `_move_to_stage`
- Migration methods (see [`MIGRATION.md`](MIGRATION.md))

**Automation-replacement hooks:**

- `@api.model_create_multi create(vals_list)` — replaces automation 171 (seq)
- `write(vals)` — repair-stage guards, serial → product/SO re-assert
- `unlink()` — replaces automation 201 (Validate Cancelled Tickets)
- `@api.onchange('ticket_type_id', 'x_studio_serial_number')` — replaces automation 178
- `@api.onchange('x_studio_return_receipt_location')` — replaces automation 172

### 6.2 `sale.order` (`models/sale_order.py`)

- `action_confirm` — portal-signature gate + stage transition
- `action_repair_create_invoice` — v163 router for the purple button
- `_create_repair_full_invoice` — single-full-invoice non-RUG flow
- `action_approve_rug_direct`, `action_reject_rug_direct`
- `action_re_estimate`, `_re_estimate_reset`
- `_migrate_nuw_to_customer_pays_flag`, `_fix_advance_payment_project_field`,
  `_seed_advance_payment_method_lines`, `_optimize_slow_write_automations`,
  `_optimize_slow_studio_computes`, `_delegate_studio_computes_to_native`,
  `_restrict_notify_transfer_completion_automation`
- Fifteen `_fix_repair_compute_*` methods backing Studio compute strings
- `_get_view` — layers on ~15 button visibility rules on top of the
  merged core-Odoo arch

### 6.3 `project.task` (`models/project_task.py`)

- `_repair_auto_update_helpdesk_pipeline_status_1` — replaces
  automation 179 via `create()` hook
- `_sync_repair_flags` — writes SO's Repair type + customer_pays from
  ticket state when task is linked
- `action_fsm_validate` — after Mark as Done, fires
  `ticket._create_mark_as_done_picking()` + advance to Repair Completed
- `_repair_studio_end_quick_repair`, `_repair_studio_diagnosis_validation`,
  `_repair_studio_image_validation`,
  `_repair_studio_validate_diagnosis_lines`
- 5 `_compute_x_studio_valid_*` methods (Cluster 5 ports)
- `_get_view` — Plan Intervention arch overrides, sale_order_id column
  visibility, button gating

### 6.4 `res.users` (`models/res_users.py`)

- `_super_user_validate` — replaces automation 250 (raises when both
  super-user flags set)
- `create()` + `write()` hooks — invoke the validator

### 6.5 `stock.picking` (`models/stock_picking.py`)

- `_compute_nuw_block_validate` — the delivery-Validate gate
- `button_validate` override — server-side guard against URL/API bypass
- `_action_done` — three paths:
  - **Path A** Repair SO pickings (warranty) → ticket stage transitions
  - **Path B** Return-to-customer handover pickings → advance to
    Handed Over
  - **Path C** Customer-pays SO pickings (NUW / Reject-RUG)
- Eight `_fix_repair_compute_*` methods backing Studio computes

### 6.6 `account.payment.register` (`models/account_payment_register.py`)

- `_validate_repair_advance_threshold` — raises UserError when the
  first payment on a non-RUG invoice is below the configured
  Advance Payment %
- `action_create_payments` override — advances ticket to "Advance
  Received" after payment posts

### 6.7 `account.move` (`models/account_move.py`)

- `_compute_is_rug_invoice`, `_compute_is_rug_account_set`
- `action_change_to_rug_account` — button to reclassify invoice
- `action_post` override — auto-settles RUG invoices
- `_rug_auto_settle` — the settlement logic
- `_delegate_studio_computes_to_native` — same delegation pattern as
  `sale.order`

### 6.8 Repair master-data models (`models/repair_master_data.py`)

Each of the 5 catalogue classes has:

- `_jin_set_company_id` — from context's `allowed_company_ids[0]`
- `@api.model_create_multi create(vals_list)` — calls the above

Plus an `AbstractModel _migrate_studio_repair_master_data_to_base`
that runs on install/upgrade to flip `ir.model.state` from `manual`
to `base` for the 5 models (uses raw SQL to bypass Odoo's
`@api.constrains` on that column).

## 7. Automation replacements (Python hooks)

Every `base.automation` on scope models has been replaced. All 18 in
scope now have `active=False` on the DB (audit trail preserved):

| Automation | Replacement |
|---|---|
| 171 RR - Auto Seq. No | `helpdesk.ticket._repair_seq_no_on_create_or_write` |
| 172 RR - Auto Populate Repair Location | `@api.onchange('x_studio_return_receipt_location')` |
| 178 RR - Auto Select Product for RUG | `@api.onchange('ticket_type_id', 'x_studio_serial_number')` |
| 201 RR - Validate Cancelled Tickets | `helpdesk.ticket.unlink()` hook |
| 179 RR Auto Update Helpdesk Pipeline Status - 1 | `project.task.create()` |
| 250 Super User Validate | `res.users.create() + write()` |
| 302 / 303 / 304 / 306 / 329 / 331 JIN Company Id | `create()` hooks on 6 catalogue models |

## 8. Server-action delegation

All 37 in-scope Studio server actions have had their `code` column
rewritten to a one-line native call with the marker
`# fix_repair:idempotent-v1`. Same behaviour, orders of magnitude
faster (no `safe_eval` overhead on the actual work).

Full tier-by-tier table: see
[`STUDIO_MIGRATION_STATUS.md`](STUDIO_MIGRATION_STATUS.md) section 3.

## 9. View overrides

### `helpdesk.ticket.py._get_view`

Injects onto the base helpdesk.ticket form:

- Return button (action 195) — visibility rules, context defaults
- Dispatch sibling button — payment-gated + stage-gated
- Send to Factory / Received at Factory / Plan Intervention / Send to
  Sales Centre / Received at Sales Centre — one visibility expression
  per button
- Serial Number field — domain + options
- Approve/Reject RUG rewiring to native Python methods

### `sale.order.py._get_view`

Injects onto the base sale.order form:

- Confirm button — layered validation stack (see 4.6)
- Create Invoice (purple) — rewired to `action_repair_create_invoice`
- Create Invoice (percentage) — hidden on every Repair SO
- Cancel / Set-to-Quotation / Send PRO-FORMA — hidden or gated
- x_studio_order_payment_method / x_studio_quotation_type readonly rules
- RUG buttons (Request / Approve / Reject) — visibility + rewire
- Re-estimate button injection
- Ghost `x_studio_current_tot_amount` field stripping

### `project.task.py._get_view`

Injects onto the base project.task form:

- Studio's original view 3019 arch was rewritten to name-based xpaths
  via SQL (v157). Two cross-chain button xpaths that Studio was
  silently swallowing are now handled in `_get_view` at combine time:
  - `action_fsm_create_quotation` → unconditional hide
  - `action_fsm_view_material` → same `invisible` expression Studio had
- Helper fields (ticket_repair_stage_state, so_cancelled) injected as
  invisible so button expressions can read them
- Mark as Done gating on Repair Completed
- Studio's Return-Return-Wizard hidden group

## 10. Settings

`Settings → Fix Repair` block (`views/res_config_settings_views.xml`):

- **Factory Repair Location** — per-company Many2one → stock.location.
  Stored in `ir.config_parameter` under
  `fix_repair.factory_repair_location.<company_id>`.

See BugFix-Sales for the Sales Configurations block (Advance Payment %,
Minimum Sales Margin %, SO Validity, Purchase Price Validity — same
company-scoping pattern).

## 11. Development notes

- Fix-repair inherits many models but declares **no new persistent
  models** other than the 5 catalogue models it took over from Studio.
- Every seed/patch/migration function is registered as a
  `<function model="..." name="..."/>` call in
  `data/fix_repair_data.xml` so it runs on every install and upgrade.
- Every one of those functions is **idempotent** — reruns find no
  work to do and no-op.
- Studio-fights are handled with a marker string
  `# fix_repair:idempotent-v1` embedded in server-action `code` fields
  and (for redundant computes) in `ir.model.fields.compute` strings, so
  successive upgrades don't clobber manual edits that were made after
  a delegation.
- Raw SQL is used deliberately in a handful of places where Odoo's
  ORM `@api.constrains` on `ir.model.state` /
  `ir.model.fields.state` blocks otherwise-safe operations. Every use
  is called out with a comment explaining why the ORM was bypassed.

## 12. Related documents

- [`MIGRATION.md`](MIGRATION.md) — the chronological Studio → Python
  migration log (Clusters 1–8, Tiers 1–7, per-version narrative
  through v163+)
- [`STUDIO_MIGRATION_STATUS.md`](STUDIO_MIGRATION_STATUS.md) — the
  live-audited inventory of every migrated artefact with current
  Python-owned / Studio-owned status
- [`CHANGES.txt`](CHANGES.txt) — the older changelog kept for
  historical reference

For a runtime verification of every migration claim in this document,
run the audit test in the companion Playwright repo:

```bash
cd "D:\Odoo Playwright Tests\PlayWrite Testings"
npm run audit
```

It produces a management-ready HTML report at
`studio-migration-audit-output/report.html`.
