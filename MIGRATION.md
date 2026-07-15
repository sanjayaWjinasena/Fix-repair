# Fix-repair — Migration & Development Log

**Module** `Fix-repair` — enhancements to the Customer Care – Repair helpdesk
workflow.
**Current version** `17.0.1.0.162`
**Odoo base** 17.0 (Enterprise)
**Active branch** `Fully-Convert-to-External-Model`

This document catalogues everything the module contributes to the running
Odoo install: the workflow features it adds, the fields / methods / hooks it
declares, and the multi-stage Studio → Python ownership migration that turned
a Studio-heavy environment into a fully code-owned one.

---

## Table of Contents

1. [Module purpose](#1-module-purpose)
2. [Runtime dependencies](#2-runtime-dependencies)
3. [File layout](#3-file-layout)
4. [Core concepts](#4-core-concepts)
5. [Feature development phases](#5-feature-development-phases)
   - 5.1 Repair movement lifecycle
   - 5.2 Sales-order workflow gates
   - 5.3 Reject-RUG / customer-pays branch
   - 5.4 Re-estimate flow
   - 5.5 Advance Payment plumbing
   - 5.6 Confirm-button validation stack
   - 5.7 Report ownership handover from BugFix-Sales
   - 5.8 NUW quotation type elimination
6. [Studio → Python migration](#6-studio--python-migration)
   - 6.1 Field clusters 1–8 (helpdesk.ticket)
   - 6.2 Satellite field migrations
   - 6.3 Custom Studio catalogue models
   - 6.4 Server action delegation (Tiers 1–7)
   - 6.5 Base-automation replacement (12 → Python hooks)
   - 6.6 View ownership repin (34 views)
   - 6.7 Report ownership repin (17 reports)
   - 6.8 Leftover field migration
7. [Version log](#7-version-log)
8. [Field catalogue (post-migration)](#8-field-catalogue-post-migration)
9. [Server action catalogue](#9-server-action-catalogue)
10. [Automation replacement catalogue](#10-automation-replacement-catalogue)
11. [Migration patterns & idempotence](#11-migration-patterns--idempotence)
12. [Gotchas encountered](#12-gotchas-encountered)

---

## 1. Module purpose

Fix-repair implements the end-to-end Customer Care – Repair workflow on top
of Odoo's Helpdesk, Field Service, and Sales modules. It covers:

- **Repair intake** (helpdesk.ticket → sale.order → project.task chain)
- **Stock movement lifecycle** (Send to Factory / Received at Factory / Send
  to Sales Centre / Received at Sales Centre / Plan Intervention / Mark as
  Done / Dispatch)
- **Repair vs sales quotation type** distinction (Sales / Project / Repair)
- **RUG (Reject-RUG) invoice / advance-payment / customer-pays branch**
- **Multi-company stage routing** (company 1 vs company 2 stage id maps)
- **Repair-specific reports** (C09–C19 series, Customer Letter, Repair
  Receipt, Repair Status, Final Notice variants)

Its guiding rule — *"same as Studio, just move to Python model"* — means
every field name, selection value, compute expression, and side effect
present in the original Studio customization was preserved verbatim when
ported.

---

## 2. Runtime dependencies

```python
'depends': [
    'base_setup', 'helpdesk', 'helpdesk_fsm', 'sale', 'sale_stock',
    'industry_fsm_sale', 'industry_fsm_stock', 'BugFix-Sales',
],
```

`BugFix-Sales` is a companion module carrying cross-cutting sale.order fixes
(Document Introduction/Conclusion feature, credit-limit gate). It was pulled
in as a dependency to keep the two modules functionally aligned.

---

## 3. File layout

```
Fix-repair/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── account_move.py               # RUG invoice logic + Change-to-RUG-Account
│   ├── account_payment_register.py   # RUG payment routing
│   ├── helpdesk_ticket.py            # Master file — 107+ x_studio_* fields
│   │                                 #   + all Studio migration methods
│   │                                 #   + all delegated server-action Python
│   │                                 #   + all replacing automation hooks
│   ├── helpdesk_type_stage.py        # helpdesk.ticket.type + helpdesk.stage
│   ├── ir_actions_report.py          # (module hooks — see reports section)
│   ├── project_task.py               # 22 x_studio_* fields + repair-workflow
│   │                                 #   view arch overrides via _get_view
│   ├── repair_master_data.py         # 5 catalogue models
│   │                                 #   (x_repair_accounts / _reason /
│   │                                 #    _reason_custom / _stages / _sub_reason)
│   ├── res_config_settings.py        # per-company Factory Repair Location dropdown
│   ├── res_users.py                  # 6 x_studio_* fields + _super_user_validate
│   ├── sale_order.py                 # SO workflow gates, Confirm predicates,
│   │                                 #   x_repair_customer_pays, tax_totals_json,
│   │                                 #   NUW elimination, delegated Studio computes
│   ├── stock_location.py             # 'Repair' usage on stock.location + seeding
│   ├── stock_lot.py                  # serial lot repair-workflow hooks
│   ├── stock_picking.py              # Return / Dispatch / Movement wiring
│   ├── stock_return_picking.py       # Return picking name / type wiring
│   └── stock_warehouse.py            # Intransit + Repair location seeding
├── data/
│   └── fix_repair_data.xml           # <function> calls for every migration step
├── views/
│   ├── helpdesk_ticket_views.xml     # native ticket form additions
│   ├── res_config_settings_views.xml # Settings dropdown host
│   └── sale_report_templates.xml     # QWeb report inheritance moved here
└── MIGRATION.md                      # this file
```

---

## 4. Core concepts

### 4.1 Studio ownership marker

Every Studio-created record (fields, views, reports, actions, models,
automations, templates) is owned by `module='studio_customization'` in
`ir.model.data`. Ownership drives:

- **Whether Studio's UI treats it as its own** and lets a user edit it in
  Studio.
- **Whether `web_studio.ir_ui_view` silently swallows arch errors** at
  render time. Studio-owned views bypass some validation raises; Fix-repair-
  owned views don't.

Migrating an artefact away from Studio ownership means rewriting its
`ir.model.data` pin to `module='Fix-repair'` with a stable slug. Data
columns (`arch_db`, `code`, DB values, etc.) are preserved verbatim.

### 4.2 `x_` field naming

- `x_studio_*` — created by Studio's UI. Original naming preserved through
  the migration so no data migration or view rename is needed.
- `x_repair_*` — Studio-created custom-model names (5 catalogue models).
- `x_x_studio_*` — Studio's own "count field" auto-naming for stat counters.

**Hard rule: `x_` fields have live data, never delete them.** Migration
always preserves the column and only changes ownership metadata.

### 4.3 `ir.model.fields.state`

- `state='manual'` — Studio-runtime field (created via UI, lives in
  `ir_model_fields` row, loaded into registry at boot).
- `state='base'` — Python-declared field (registry expects to resolve
  against a `fields.X(...)` line in a Python model class).

The migration flips these one direction only (`manual → base`), but only
*after* a matching Python declaration has been added in a Fix-repair model
file. Flipping without a declaration causes Odoo to drop the field from
the model at load time — every view that references it then fails
validation (see [gotchas](#12-gotchas-encountered)).

### 4.4 The delegation pattern (safe_eval → native Python)

Studio server actions run with `state='code'` and evaluate their Python
string through `safe_eval` on every call. `safe_eval` is orders of
magnitude slower than native CPython. The delegation pattern rewrites
each Studio action's code column to a one-line native call:

```python
# Server action id 2001 — before delegation
# (~40 lines of ported Studio logic run through safe_eval on every click)

# After delegation:
record._repair_studio_send_to_factory()
```

The one-line delegation still runs through `safe_eval`, but its cost is
negligible. All the actual work happens in the native Python method.

### 4.5 `arch_db` is jsonb, not text (Odoo 17)

`ir_ui_view.arch_db` is a `jsonb` column with per-language keys, e.g.
`{'en_US': '<data>...</data>'}`. Any raw SQL `UPDATE` must encode the
XML string as JSON before assignment; a bare string errors with
`invalid input syntax for type json`.

---

## 5. Feature development phases

The module's git history predates the Studio migration by hundreds of
commits. This section documents the feature waves that ship inside
Fix-repair *besides* the ownership migration.

### 5.1 Repair movement lifecycle

- **Send / Received at Factory** with source/dest computed from last
  movement's dest and warehouse routing (factory Intransit → factory Stock)
- **Send / Received at Sales Centre** mirrors the factory hop pattern
- **Plan Intervention** moves the item to the right Repair virtual location
- **Mark as Done** reverses the Plan Intervention hop back to prior source
- **Dispatch** creates the final outbound picking with the `<WH>/PHAN/xxxxx`
  or `<WH>/RET/xxxxx` naming convention
- **Repair Completed** is a one-way milestone — never regressed by any
  automation or hook (guarded at the `helpdesk.ticket.write()` boundary)

Location model additions:

- `stock.location.usage='repair'` value + child `<WH>/Repair` locations
  seeded on every warehouse
- `<WH>/Intransit` locations with `usage='transit'` seeded on every warehouse
  that lacks one

### 5.2 Sales-order workflow gates

Layered visibility / action gates on `sale.order`:

- `action_confirm` invisible unless every predicate holds (overdue debt,
  margin, commission, expired, valid lines, bank guarantee, project budget,
  credit limit for Credit-payment SOs, customer signature) — layered as a
  compound `invisible=` expression on the button
- Set-to-Quotation (`action_draft`) hidden at all times
- Send PRO-FORMA Invoice + Cancel hidden on sale.order form
- Register Payment hidden on RUG-confirmed invoices
- Cancel button appears once the first quotation email has been sent
- Create Advance Payment shown only on confirmed Sales quotations

### 5.3 Reject-RUG / customer-pays branch

RUG (Reject Under Guarantee) is the flow where the customer's warranty
claim is rejected and the customer pays. Behaviours added:

- SO route: identical to the NUW (Not Under Warranty) flow — same
  advance-payment prompt, same repair invoice generation, same delivery gating
- Ticket stage: advances to **Estimation Approval Received** on Confirm
- Payment: advances the ticket to **Advance Received** on `Register Payment`
- Invoice classification: Reject-RUG invoices treated as non-RUG (Change to
  RUG Account button hidden; Register Payment available)
- Email: uses the Not-Under-Warranty email body
- Confirm gate: portal auto-confirm suppressed; customer signature required
  before Confirm becomes clickable
- Rejection unblocks the delivery Validate flow once the first invoice exists

### 5.4 Re-estimate flow

- Re-estimate button on both `helpdesk.ticket` and the `sale.order` form
- Resets SO state to `draft`, clears customer signature, keeps existing
  pickings (new lines merge into them rather than creating fresh pickings)
- Hidden on cancelled SOs and cancelled tickets
- Injected via `_get_view` override so the button appears without a hard
  module upgrade

### 5.5 Advance Payment plumbing

- **Two Advance Payment journals** get inbound Manual payment method lines
  seeded automatically on upgrade (Odoo 17's `account.payment` validation
  requires `payment_method_line_id`; Studio's "Create Advance Payment"
  action creates payments on these journals)
- **`payment_account_id`** (Outstanding Receipts) also seeded on the method
  lines
- **Studio "Create Advance Payment" server action fix**: was passing
  `record.id` (a sale.order id) into `x_studio_project_no_1` (a
  Many2one → project.project) causing a FK violation. Rewritten to pass
  `record.x_studio_project_no.id`.

### 5.6 Confirm-button validation stack

Layered `invisible=` predicates on the Confirm button (all scoped to
Repair quotation_type by default; universal ones apply everywhere):

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

### 5.7 Report ownership handover from BugFix-Sales

- QWeb inheritance for Document Introduction / Conclusion **moved from
  BugFix-Sales to Fix-repair** (`views/sale_report_templates.xml`) so the
  helpdesk-repair reports maintain the same visual arrangement as sales
  reports.
- Anchor rewritten from `//p[@name='order_note']` (missing on this env) to
  `//div[hasclass('page')]` position="inside" to survive base-template
  reshuffles.

### 5.8 NUW quotation type elimination

- **Before**: `x_studio_quotation_type` had 3 values on sale.order —
  `Sales`, `Project`, `Repair`, and a legacy `Not Under Warranty`.
- **After**: NUW value dropped from the selection; existing NUW SOs
  migrated to `quotation_type='Repair'` **+** new Boolean
  `x_repair_customer_pays=True`.
- All downstream customer-pays logic (RUG buttons, invoice classification,
  hide/show rules) now reads `x_repair_customer_pays` directly.
- Migration is data-preserving and idempotent: subsequent runs find no NUW
  records and no NUW selection value.

Function: `sale.order._migrate_nuw_to_customer_pays_flag`

---

## 6. Studio → Python migration

This is the recent-session work. Every Studio artefact that touched the
helpdesk-repair scope was migrated to Python ownership across v143–v162.

### Scope models

The 10 models Fix-repair claims ownership of:

- `helpdesk.ticket`
- `helpdesk.ticket.type`
- `helpdesk.stage`
- `project.task`
- `res.users`
- `x_repair_accounts`
- `x_repair_reason`
- `x_repair_reason_custom`
- `x_repair_stages`
- `x_repair_sub_reason`

`sale.order` is deliberately partially migrated — many Studio fields on it
belong to workflows outside the helpdesk-repair scope and stay Studio-
managed.

### 6.1 Field clusters 1–8 (helpdesk.ticket)

107 `x_studio_*` fields on `helpdesk.ticket` were declared in Python and
flipped from `state='manual'` to `state='base'` in 8 thematic clusters.

| Cluster | Theme | Fields |
|---|---|---|
| 1 | RUG cycle | 7 |
| 2 | Repair location / stock | 9 |
| 3 | Cancel / Reopen lifecycle | 11 |
| 4 | Stage-transition markers | 10 |
| 5 | Stage-validation computes (with side effects) | 10 |
| 6 | Audit slots (`x_studio_created_by_N` / `_on_N` × 10 + factory + centre audit) | 29 |
| 7 | Serial number / product snapshot | 11 |
| 8 | Diagnostic / misc (branch, city, tracking, computed counts) | 20 |

Each cluster ships as a `_migrate_studio_<theme>_cluster_to_base` method
on `helpdesk.ticket`. Migration behaviour is identical across all 8:

1. Find `ir.model.fields` rows for the cluster names on the target model.
2. Filter to `state='manual'` rows.
3. Write `state='base'` (ORM write is fine because helpdesk_ticket.py already
   declares every field).
4. Delete the corresponding `studio_customization` pin on each row.

Compute strings from Studio were ported verbatim, including their side
effects (e.g. `x_studio_valid_delivered_so` also writes
`x_studio_valid_delivered_so2` inside its compute).

### 6.2 Satellite field migrations

Beyond helpdesk.ticket, the same field-migration pattern was applied to:

| Model | Field count | Purpose |
|---|---|---|
| `helpdesk.ticket.type` | 4 | RUG / RUG Confirmed / With serial / Without serial |
| `helpdesk.stage` | 1 | `x_studio_company_id` (multi-company stage routing) |
| `project.task` | 13 (Cluster 5) + 9 (leftover) | end_quick_repair, quick_repair_status_1, repair_image_01/02, repair_reason M2M, valid_* computes, cancelled/created_date/diagnosis_ids/incomplete_delivery_available/priority/quotation_type/related_information/valid_diagnosis/warranty_card |
| `res.users` | 4 (locations) + 2 (super-user) | Source Location, Virtual Location + `_1` duplicates, `x_studio_super_user`, `x_studio_super_user_melt_items` |

Location fields on `res.users` are the source of the `helpdesk.ticket.
x_studio_source_location`-style related chain, so their migration completes
the location field graph's Python ownership.

### 6.3 Custom Studio catalogue models

The 5 custom Studio models are now Python-owned via
`models/repair_master_data.py`:

```python
class XRepairAccounts(models.Model):
    _name = 'x_repair_accounts'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    x_studio_company_id = fields.Many2one('res.company')
    x_studio_sequence = fields.Integer()

    def _jin_set_company_id(self):
        for record in self:
            if not record.x_studio_company_id:
                company_id = self.env.context.get(
                    'allowed_company_ids', [self.env.user.company_id.id]
                )[0]
                record.x_studio_company_id = company_id

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._jin_set_company_id()
        return records
```

Same shape for `x_repair_reason`, `x_repair_reason_custom`,
`x_repair_stages`, `x_repair_sub_reason`.

The migration method
`_migrate_studio_repair_master_data_to_base` uses raw SQL to flip
`ir_model.state` and `ir_model_fields.state` (blocked by ORM
`@api.constrains`) and creates Fix-repair `ir.model.data` pins so the
registry treats the models as owned by Fix-repair.

### 6.4 Server action delegation (Tiers 1–7)

46 Studio server actions in scope. 37 of them delegated to native
Python; 9 already delegated but Studio-pinned had their pins repinned
to Fix-repair.

`_delegate_studio_server_actions_to_native` on `helpdesk.ticket` holds
the full delegation table. Each entry is a tuple:

```python
(action_id, guard_substring, delegation_code)
```

- `action_id` — the `ir.actions.server` PK.
- `guard_substring` — a marker text that must appear in the action's
  current code for the delegation to overwrite it. Skipped if absent
  (protects manual edits).
- `delegation_code` — the one-line native call (e.g.
  `"record._repair_studio_send_to_factory()"`).

Idempotence: every delegated action carries the marker
`# fix_repair:idempotent-v1` on the first line. If the marker is
present, the rewrite is skipped.

Tier breakdown:

| Tier | Trigger | Actions | Delegates to |
|---|---|---|---|
| 1 | automation-triggered | 4 (1976, 2000, 2222, 1989) | `helpdesk.ticket` seq/populate/validate/select |
| 2 | button-triggered repair-workflow | 6 (2001, 2002, 2007, 2006, 2220, 2221) | Send/Received × Factory + Sales Centre, Cancel, Reopen |
| 3 | heavy compute | 2 (1993, 1994) | route + serial-no auto-create |
| 4 | email actions | 5 (2269, 2308, 2309, 2310, 2311) | Customer Letter + 4 Final Notice variants |
| 5 | variants + object_write conversion | 8 (1990, 2450, 2451, 1992, 2343, 2159, 2558, 1998) | RUG variants, cancel repair 2, change type, user location, no-op |
| 6 | non-ticket models | 8 (2666, 2667, 2668, 2670, 2760, 2790, 2003, 2544) | 6 × `_jin_set_company_id` + project.task pipeline + super-user validate |
| 7 | project.task Studio | 4 (2316, 2224, 2242, 2219) | End Quick Repair + 3 validation guards |

### 6.5 Base-automation replacement

Every `base.automation` on the scope models was replaced by a native
Python create/write/unlink/onchange hook and deactivated
(`active=False`). Two deactivation methods handle the sweep:

- `_deactivate_migrated_ticket_automations` — 4 helpdesk.ticket
  automations (171, 172, 178, 201)
- `_deactivate_migrated_other_automations` — 8 automations on ancillary
  models (329, 331, 302, 303, 306, 304, 179, 250)

Replacement hooks:

| Automation | Replaced by |
|---|---|
| 171 Repair Seq | `helpdesk.ticket._repair_seq_no_on_create_or_write` (create + write hooks) |
| 172 Auto Populate Repair Location | `@api.onchange('x_studio_return_receipt_location')` |
| 178 Auto Select Product for RUG | `@api.onchange('ticket_type_id', 'x_studio_serial_number')` |
| 201 Validate Cancelled Tickets | `unlink()` hook |
| 250 Super User Validate | `res.users.create() + write()` |
| 179 RR Auto Update Helpdesk Pipeline Status - 1 | `project.task.create()` |
| 329 / 331 / 302 / 303 / 306 / 304 JIN Company Id | `create()` hooks on 6 catalogue models |

### 6.6 View ownership repin (34 views)

`_migrate_studio_views_to_native` on `helpdesk.ticket` walks every
`studio_customization` view pin whose target lives on a scope model and
rewrites the pin's module to `Fix-repair` with a stable slug pattern:

```
view_<model_with_underscores>_<type>_<view_id>
```

For example view id 4012 (`Odoo Studio: helpdesk.ticket.form
customization`) becomes `Fix-repair.view_helpdesk_ticket_form_4012`.

Arch bytes are untouched — only the ownership pin moves. 34 views
migrated in v152.

**Post-migration arch cleanup on view 3019.** Studio's silent-swallow
behaviour was hiding two classes of arch bug on
`project.task.form customization`:

- Cross-chain button xpaths (`action_fsm_create_quotation`,
  `action_fsm_view_material`) whose targets live in
  `industry_fsm_sale.view_task_form2_inherit` — a sibling inheritance
  chain unreachable when Odoo combines against `project.task.form`.
- Fragile positional xpaths (`//form[1]/sheet[1]/group[1]/group[2]/
  field[@name='sale_order_id']`) that break the moment a base module
  reshuffles the arch tree.

`_sanitize_broken_studio_task_form_xpath` (v157) rewrites view 3019's
arch entirely with name-based xpaths (`//field[@name='sale_order_id']`,
`//notebook`, etc.), dropping the two cross-chain button xpaths — both
of which are already replicated by `project_task.py._get_view`.

### 6.7 Report ownership repin (17 reports)

`_migrate_studio_reports_to_native` handles the three-step ownership
transfer per report:

1. Repin the `ir.actions.report` row (module `studio_customization` →
   `Fix-repair`, xml_id unchanged).
2. Follow `report_name` (`studio_customization.<tail>`) to the QWeb
   template `ir.ui.view` and repin the template pin the same way.
3. Rewrite `report_name` on the action from
   `studio_customization.<tail>` to `Fix-repair.<tail>` so `env.ref()`
   at render time resolves.

`_fix_studio_report_template_keys` (v154) is the follow-up hotfix that
also rewrites the template's `key` field (matched at render time by
`website.ir_ui_view._get_view_id`), creates missing
`ir.model.data` pins for templates that Studio never pinned (the
`_copy_N` clones), and rewrites `t-call="studio_customization.<X>"`
references inside `arch_db` for migrated tails so chained inheritance
resolves.

Reports covered: C09–C19 series (11), Customer Letter, Helpdesk Ticket
Report, Repair Status, Repair Receipt, and the two Repair Final Notice
variants — 17 total.

### 6.8 Leftover field migration (v162)

Cluster 1–8 didn't include 11 helpdesk-repair fields that are used by
view 3019's arch and by Fix-repair Python. v159 tried to flip their
state without Python declarations (broke view validation, rolled back in
v161). v162 added real Python declarations and re-flipped state via SQL.

The 11 fields:

| Model | Field | Type |
|---|---|---|
| `res.users` | `x_studio_super_user` | Boolean |
| `res.users` | `x_studio_super_user_melt_items` | Boolean |
| `project.task` | `x_studio_cancelled` | Boolean related |
| `project.task` | `x_studio_created_date` | Datetime |
| `project.task` | `x_studio_diagnosis_ids` | One2many('x_task_diagnosis','x_studio_task_id') |
| `project.task` | `x_studio_incomplete_delivery_available` | Boolean compute |
| `project.task` | `x_studio_priority` | Selection (5 levels) |
| `project.task` | `x_studio_quotation_type` | Selection related |
| `project.task` | `x_studio_related_information` | Binary related |
| `project.task` | `x_studio_valid_diagnosis` | Boolean compute |
| `project.task` | `x_studio_warranty_card` | Binary related |

Two computes ported to `@api.depends` methods on `project.task`:

```python
@api.depends('x_studio_diagnosis_ids')
def _compute_x_studio_valid_diagnosis(self):
    for rec in self:
        rec.x_studio_valid_diagnosis = bool(rec.x_studio_diagnosis_ids)

@api.depends('sale_order_id', 'sale_order_id.state')
def _compute_x_studio_incomplete_delivery_available(self):
    Picking = self.env['stock.picking']
    for rec in self:
        valid = False
        so = rec.sale_order_id
        if so and so.state != 'cancel':
            open_delivery = Picking.search(
                [('sale_id', '=', so.id), ('state', '!=', 'done')],
                limit=1,
            )
            if open_delivery:
                valid = open_delivery.state != 'cancel'
            else:
                any_delivery = Picking.search(
                    [('sale_id', '=', so.id)], limit=1,
                )
                valid = not any_delivery
        rec.x_studio_incomplete_delivery_available = valid
```

The `incomplete_delivery_available` compute dropped a no-op branch from
Studio (`if state == 'cancel' → if x_studio_repair_completed_stage_updated
→ valid = False` — but `valid` was already False, so the branch had no
observable effect).

Fields deliberately **not** migrated (out of helpdesk-repair scope):

- `res.users`: `x_studio_attendance_administrator`, `x_studio_company_id`,
  `x_studio_recr_stages`, 2 m2m helpers, 2 stock location counters
- `project.task`: `x_studio_payment_type`, `x_studio_starting_date`,
  `x_task_id_sale_order_count`

---

## 7. Version log

| Version | Commit | Summary |
|---|---|---|
| 17.0.1.0.144 | 7d63a40 | Tier 1 — 4 automation-triggered actions delegated |
| 17.0.1.0.145 | 98c5326 | Tier 2 — 6 button-triggered repair actions delegated |
| 17.0.1.0.146 | 87f85a4 | Tier 3 — 2 heavy compute actions delegated |
| 17.0.1.0.147 | c6b59d9 | Tier 4 — 5 email actions delegated |
| 17.0.1.0.148 | 54903c7 | Tier 5 — 8 variant / object_write actions delegated |
| 17.0.1.0.149 | 7bf6322 | 4 ticket automations replaced by Python hooks |
| 17.0.1.0.150 | 05e5e88 | Tier 6 — 8 non-ticket actions + 8 remaining automations |
| 17.0.1.0.151 | 3c44b60 | Tier 7 — 4 remaining project.task Studio actions |
| 17.0.1.0.152 | d7c271b | 34 views repinned Studio → Fix-repair |
| 17.0.1.0.153 | e2f1f94 | 17 reports repinned Studio → Fix-repair |
| 17.0.1.0.154 | ef3adfd | Hotfix — realign QWeb template `key` field with new module prefix |
| 17.0.1.0.155 | 5ba32eb | Hotfix — strip broken `action_fsm_create_quotation` xpath from view 3019 |
| 17.0.1.0.156 | 988e2b3 | Extend sanitize to strip both broken button xpaths in one pass |
| 17.0.1.0.157 | 56ad102 | Rewrite view 3019 arch with robust name-based xpaths via SQL |
| 17.0.1.0.158 | 64c0cc5 | Fix v157 SQL — `arch_db` is jsonb, encode with JSON wrapper |
| 17.0.1.0.159 | 2b6babf | Close last two Studio pockets — 11 fields + 9 action repins |
| 17.0.1.0.160 | 748216c | Switch v159 state flip from ORM write to raw SQL |
| 17.0.1.0.161 | 13db4bb | Rollback — 11-field state flip missed Python declarations, killed views |
| 17.0.1.0.162 | 07980ce | Add real Python declarations for the 11 leftover fields, re-flip state |

Earlier version history (pre-migration) is in `git log`; representative
commits include:

| Range | Theme |
|---|---|
| ~v100–v130 | Repair movement lifecycle (Send/Receive Factory + Centre, Plan Intervention, Mark as Done, Dispatch, Intransit + Repair location seeding) |
| v130–v140 | Sales-order gates (Confirm predicates layered, Cancel visibility, Send by Email, Advance Payment plumbing) |
| v140–v143 | Reject-RUG customer-pays flow, NUW elimination, tax_totals_json alias, credit-limit gate |

---

## 8. Field catalogue (post-migration)

All fields below are Python-owned (`state='base'`) with declarations in
the noted file.

### 8.1 `helpdesk.ticket` (via `models/helpdesk_ticket.py`)

107 `x_studio_*` fields spread across the 8 clusters. Highlights:

**Cluster 1 — RUG cycle:** `x_studio_rug_confirmed`, `x_studio_rug_approved`,
`x_studio_rug_rejected`, `x_studio_rug_approval_status`, plus audit slots.

**Cluster 2 — Repair location / stock:** `x_studio_repair_location`,
`x_studio_return_receipt_location`, source / virtual location variants,
plus pick / picking id fields.

**Cluster 3 — Cancel / Reopen:** `x_studio_cancelled`,
`x_studio_cancel_reason`, `x_studio_cancel_status`, `x_studio_cancel_by`,
`x_studio_cancel_date`, `x_studio_cancel_stage`, `x_studio_reopen`,
`x_studio_reopen_status`, `x_studio_reopen_by`, `x_studio_reopen_date`,
`x_studio_cancelled_2`.

**Cluster 4 — Stage-transition markers:** `x_studio_send_to_factory`,
`x_studio_received_from_factory`, `x_studio_send_to_sales_centre`,
`x_studio_received_from_sales_centre`, plus estimation / invoice /
`x_studio_repair_complete_stage_updated` flags and the older
`x_studio_handed_over`.

**Cluster 5 — Stage-validation computes (with side effects):**
`x_studio_valid_confirmed_so`, `_valid_confirmed2_so`, `_valid_invoiced_so`,
`_valid_delivered_so`, `_task_status`, plus 5 simpler predicates. Each
carries the Studio-verbatim compute including its stage writes and
audit-slot writes.

**Cluster 6 — Audit slots:** `x_studio_stage_date` + 10
`x_studio_created_by_N` / `_created_on_N` pairs + 4 factory + 4
sales-centre shipment audit fields.

**Cluster 7 — Serial / product:** `x_studio_serial_no`, `_serial_number`,
`_sn_updated`, `_repair_serial_created`, `_repair_reason` M2M,
`_materials_used`, `_quantity`, `_unit_price`, `_items` M2M, `_qty`,
`_sales_price`.

**Cluster 8 — Diagnostic / misc:** `x_studio_branch`, `_city`, `_driver_name`,
`_warranty_card`, `_stage_name`, `_tracking`, `_cccc`, `_cccc3`,
`_sale_order`, `_material_availability`, `_re_estimate_count`,
`_re_estimate_status`, `_x_x_studio_created_from_help_ticket_stock_picking_count`,
plus siblings.

### 8.2 `helpdesk.ticket.type` (via `models/helpdesk_type_stage.py`)

- `x_studio_rug` — Boolean
- `x_studio_rug_confirmed` — Boolean
- `x_studio_with_serial_no` — Boolean
- `x_studio_without_serial_no` — Boolean

### 8.3 `helpdesk.stage` (via `models/helpdesk_type_stage.py`)

- `x_studio_company_id` — Many2one to `res.company` (multi-company routing)

Method: `_jin_set_company_id` + `@api.model_create_multi create()` hook.

### 8.4 `project.task` (via `models/project_task.py`)

Cluster 5 (13):

- `x_studio_end_quick_repair`, `x_studio_repair_image_01/02`,
  `x_studio_repair_reason` (M2M), `x_studio_quick_repair_status_1`,
  `x_studio_repair_completed_stage_updated` (related),
  `x_studio_valid_delivered_so2`, `x_studio_fully_invoiced_so`,
  `x_studio_material_availability`, `x_studio_valid_confirm_so`,
  `x_studio_valid_confirm2_so`, `x_studio_valid_delivered_so`,
  `x_studio_valid_invoiced_so`.

Leftover v162 (9):

- `x_studio_cancelled` (related), `x_studio_created_date`,
  `x_studio_diagnosis_ids` (O2m), `x_studio_incomplete_delivery_available`
  (compute), `x_studio_priority`, `x_studio_quotation_type` (related),
  `x_studio_related_information` (related), `x_studio_valid_diagnosis`
  (compute), `x_studio_warranty_card` (related).

Native additions (not Studio-migrated):

- `ticket_repair_stage_state` — Char compute
- `so_cancelled` — Boolean compute

### 8.5 `res.users` (via `models/res_users.py`)

- `x_studio_source_location`, `x_studio_source_location_1` — Many2one to
  `stock.location`
- `x_studio_virtual_location`, `x_studio_virtual_location_1` — same
- `x_studio_super_user`, `x_studio_super_user_melt_items` — Boolean

Method: `_super_user_validate` + create/write hooks.

### 8.6 `sale.order` (via `models/sale_order.py`)

Fix-repair-native:

- `x_repair_customer_pays` — Boolean (NUW replacement)
- `tax_totals_json` — Char alias computed from `tax_totals` via `json.dumps`
  (Studio-migrated arch expects the Odoo 16 attribute name)

Plus delegated compute rewrites via `_delegate_studio_computes_to_native`
and `_optimize_slow_write_automations` / `_optimize_slow_studio_computes` —
none of them touch the field graph, only rewrite Studio compute strings to
one-line native calls.

### 8.7 Catalogue models (via `models/repair_master_data.py`)

Each of the 5 models (`x_repair_accounts`, `x_repair_reason`,
`x_repair_reason_custom`, `x_repair_stages`, `x_repair_sub_reason`)
inherits `['mail.thread', 'mail.activity.mixin']` and declares:

- `x_studio_company_id` — Many2one to `res.company`
- `x_studio_sequence` — Integer

Method: `_jin_set_company_id` + `@api.model_create_multi create()` hook.

---

## 9. Server action catalogue

Every entry is a `(server_action_id, delegation_target)` pair from
`_delegate_studio_server_actions_to_native`.

### Tier 1 — automation-triggered (4)

| ID | Delegates to |
|---|---|
| 1976 | `helpdesk.ticket._repair_seq_no_on_create_or_write` |
| 2000 | `helpdesk.ticket._repair_populate_repair_location` |
| 2222 | `helpdesk.ticket._repair_validate_cancelled_on_unlink` |
| 1989 | `helpdesk.ticket._repair_auto_select_product_for_rug` |

### Tier 2 — repair-workflow buttons (6)

| ID | Delegates to |
|---|---|
| 2001 | `helpdesk.ticket._repair_studio_send_to_factory` |
| 2002 | `helpdesk.ticket._repair_studio_receive_at_factory` |
| 2007 | `helpdesk.ticket._repair_studio_send_to_sales_centre` |
| 2006 | `helpdesk.ticket._repair_studio_receive_at_sales_centre` |
| 2220 | `helpdesk.ticket._repair_studio_cancel_repair` |
| 2221 | `helpdesk.ticket._repair_studio_reopen_repair` |

### Tier 3 — heavy compute (2)

| ID | Delegates to |
|---|---|
| 1993 | `helpdesk.ticket._repair_studio_auto_create_repair_route` |
| 1994 | `helpdesk.ticket._repair_studio_auto_create_repair_serial_nos` |

### Tier 4 — email actions (5)

| ID | Delegates to |
|---|---|
| 2269 | `helpdesk.ticket._repair_send_customer_letter` |
| 2308 | `helpdesk.ticket._repair_send_final_notice` |
| 2309 | `helpdesk.ticket._repair_send_final_notice_estimated` |
| 2310 | `helpdesk.ticket._repair_send_final_notice_scrappage` |
| 2311 | `helpdesk.ticket._repair_send_reminding_letter` |

### Tier 5 — variants + object_write conversion (8)

| ID | Delegates to |
|---|---|
| 1990 | `helpdesk.ticket._repair_auto_select_product_for_rug_2` |
| 2450 | `helpdesk.ticket._repair_auto_select_product_for_rug_22` |
| 2451 | `helpdesk.ticket._repair_auto_select_product_for_rug_33` |
| 1992 | `helpdesk.ticket._repair_auto_select_product_for_rug_4` |
| 2343 | `helpdesk.ticket._repair_studio_cancel_repair_2` |
| 2159 | `helpdesk.ticket._repair_studio_change_repair_type_to_rug` |
| 2558 | `helpdesk.ticket._repair_studio_user_location_validation` |
| 1998 | `helpdesk.ticket._repair_studio_update_rug_approval_in_pipeline` (object_write → code) |

### Tier 6 — non-ticket models (8)

| ID | Model | Delegates to |
|---|---|---|
| 2666 | `x_repair_reason` | `_jin_set_company_id` |
| 2667 | `x_repair_reason_custom` | `_jin_set_company_id` |
| 2668 | `x_repair_sub_reason` | `_jin_set_company_id` |
| 2670 | `x_repair_stages` | `_jin_set_company_id` |
| 2760 | `helpdesk.stage` | `_jin_set_company_id` |
| 2790 | `x_repair_accounts` | `_jin_set_company_id` |
| 2003 | `project.task` | `_repair_auto_update_helpdesk_pipeline_status_1` |
| 2544 | `res.users` | `_super_user_validate` |

### Tier 7 — project.task Studio actions (4)

| ID | Delegates to |
|---|---|
| 2316 | `project.task._repair_studio_end_quick_repair` |
| 2224 | `project.task._repair_studio_diagnosis_validation` |
| 2242 | `project.task._repair_studio_image_validation` |
| 2219 | `project.task._repair_studio_validate_diagnosis_lines` |

### Ownership repin only (9)

Actions whose Python delegation code was in place before v159 but whose
`ir.model.data` pin was still under `studio_customization`:

| ID | Name | New xml_id |
|---|---|---|
| 1976 | RR Repair Seq No | `Fix-repair.action_1976` |
| 2544 | Super User Validate | `Fix-repair.action_2544` |
| 2558 | User Location Validation | `Fix-repair.action_2558` |
| 2666 | JIN Company Id in Repair Reason | `Fix-repair.action_2666` |
| 2667 | JIN Company Id in Repair Reason - Customer | `Fix-repair.action_2667` |
| 2668 | JIN Company Id in Repair Sub Reason | `Fix-repair.action_2668` |
| 2670 | JIN Company Id in Repair Stages | `Fix-repair.action_2670` |
| 2760 | JIN Company Id in Helpdesk Stage | `Fix-repair.action_2760` |
| 2790 | JIN Company Id in Repair Accounts | `Fix-repair.action_2790` |

---

## 10. Automation replacement catalogue

Every entry: `(automation_id, replaced_by_python_hook)`.

| ID | Automation name | Replacement |
|---|---|---|
| 171 | RR - Auto Seq. No | `helpdesk.ticket._repair_seq_no_on_create_or_write` (create + write) |
| 172 | RR - Auto Populate Repair Location | `@api.onchange('x_studio_return_receipt_location')` |
| 178 | RR - Auto Select Product for RUG | `@api.onchange('ticket_type_id', 'x_studio_serial_number')` |
| 201 | RR - Validate Cancelled Tickets | `helpdesk.ticket.unlink()` hook |
| 179 | RR - Auto Update Helpdesk Pipeline Status - 1 | `project.task.create()` |
| 250 | Super User Validate | `res.users.create() + write()` |
| 302 | JIN Company Id in Repair Reason | `x_repair_reason.create()` |
| 303 | JIN Company Id in Repair Reason - Customer | `x_repair_reason_custom.create()` |
| 304 | JIN Company Id in Repair Sub Reason | `x_repair_sub_reason.create()` |
| 306 | JIN Company Id in Repair Stages | `x_repair_stages.create()` |
| 329 | JIN Company Id in Helpdesk Stage | `helpdesk.stage.create()` |
| 331 | JIN Company Id in Repair Accounts | `x_repair_accounts.create()` |

Plus a separate deactivation for `RR - Auto Select Product for RUG
Repairs-33` (unconditionally cleared `product_id` when `x_studio_serial_no`
changed; superseded by `_onchange_serial_no_product`).

---

## 11. Migration patterns & idempotence

### Wire everything through `data/fix_repair_data.xml`

Every migration step is a `<function>` call in the data XML:

```xml
<function model="helpdesk.ticket"
          name="_migrate_studio_rug_cluster_to_base"/>
```

Odoo re-runs the whole data file on every upgrade. Every method is
idempotent — subsequent runs find no manual rows / no studio pins in scope
and no-op.

### Marker string for delegated code

```python
_FIX_REPAIR_IDEMPOTENCE_MARKER = "# fix_repair:idempotent-v1"
```

Delegated server actions carry this marker on the first line of their
`code` column. The delegation table checks for the marker before
overwriting and skips if present, so a subsequent upgrade won't clobber a
manually-edited action.

### Stable slug xml_ids

Repinned records get deterministic xml_ids derived from the record id:

- Views: `view_<model_underscored>_<type>_<id>`
- Server actions: `action_<id>`
- Report templates: original tail preserved verbatim (Studio's UUID-based
  name kept for cross-reference safety)

### Raw SQL where ORM validation gets in the way

Two classes of state transition are blocked by Odoo's ORM:

- `ir.model.state`: `manual → base` is protected by
  `@api.constrains('state')`. Solved with:
  ```python
  self.env.cr.execute("UPDATE ir_model SET state = 'base' WHERE id IN %s",
                      (tuple(rows.ids),))
  rows.invalidate_recordset(['state'])
  ```

- `ir.model.fields.state`: same constraint on some field configurations
  (One2many with a still-manual comodel, computed fields, etc.). Same
  raw-SQL fix applied for these too.

### `arch_db` writes bypass `_check_xml` via SQL

When the view arch we're replacing contains xpaths that will fail
validation during the same transaction (partial-strip case), we use SQL:

```python
self.env.cr.execute(
    "UPDATE ir_ui_view SET arch_db = %s::jsonb WHERE id = %s",
    (json.dumps({lang: clean_arch for lang in existing_langs}), view.id),
)
view.invalidate_recordset(['arch_db'])
```

`arch_db` is jsonb — the payload must be a JSON string with per-language
keys, not a bare XML string.

---

## 12. Gotchas encountered

Documented for future migrators.

### 12.1 Studio silently swallows arch failures

`web_studio.ir_ui_view` overrides `_get_view` and `apply_inheritance_specs`
with lenient error handling for views owned by `studio_customization`.
Under that ownership, broken xpaths raise but the error is caught and
skipped. Once a view is repinned to a different module, Odoo's normal
raise path kicks in and the latent bug becomes user-visible.

Manifested in this migration as:

- `action_fsm_create_quotation` xpath (v155)
- `action_fsm_view_material` xpath (v156)
- Positional `//form[1]/sheet[1]/...` xpaths on view 3019 (v157)

### 12.2 Report template resolution has two paths, both must line up

QWeb reports resolve their template via `report_name` (a string like
`Fix-repair.<tail>`). Two resolution paths exist:

- **`ir.model.data` lookup** — matches `(module, name)` against
  `ir_model_data`.
- **`website.ir_ui_view._get_view_id` fallback** — matches
  `ir.ui.view.key` verbatim against the full `<module>.<name>` string.

The report migration originally only updated `report_name` + the
`ir.model.data` pin (v153). It missed the `key` field. Result: all 17
reports 500'd at render time with:

```
ValueError: View 'Fix-repair.studio_report_docume_...' in website 1 not found
```

v154 was the follow-up hotfix — it walks the templates and updates
`key` + creates missing pins + rewrites `t-call="studio_customization.
<migrated_tail>"` references inside `arch_db`.

### 12.3 State flip without Python declaration drops the field

`ir.model.fields.state='base'` means Odoo's registry loader expects to
resolve the field against a `fields.X(...)` line in a Python model.
If that line doesn't exist, the field is dropped from the model at load
time. Every view / expression / computed field that references it then
fails validation.

Manifested in v159/v160 — 11 fields were flipped to `base` without
adding declarations. Result:

```
Field "x_studio_super_user_melt_items" does not exist in model "res.users"
```

v161 rolled state back to `manual` as a hotfix. v162 did the proper
migration: added declarations first, flipped state second.

### 12.4 `arch_db` is jsonb, not text

Discovered in v157/v158. Any raw SQL `UPDATE ir_ui_view SET arch_db = ...`
must pass a JSON-encoded string with per-language keys. Passing a bare
XML string errors with:

```
psycopg2.errors.InvalidTextRepresentation: invalid input syntax for type json
```

Solution: `json.dumps({'en_US': arch})` + `::jsonb` cast in the
`UPDATE`.

### 12.5 Studio compute strings can reference non-existent fields

The Studio compute for `x_studio_incomplete_delivery_available` referenced
`x_studio_repair_completed_stage_updated` on `helpdesk.ticket` — a field
that doesn't exist there (only on `project.task` as a related). Studio's
runtime evaluated the `AttributeError` as `False` silently. The branch
guarded by that check was a no-op (assigned `valid = False` when it was
already `False`).

Discovered when porting to `@api.depends`; the branch was omitted from
the Python port with no observable behaviour change.

### 12.6 `ir.model.data` unique constraint is `(module, name)`

Not `res_id`. So the same view / action record can carry multiple pins
under different `(module, name)` tuples. When repinning, only touch the
`studio_customization` pin — don't unlink other module's pins on the
same record.

### 12.7 QWeb report templates without pins

Studio's report-cloning flow copies the template's `ir.ui.view` row but
often doesn't create a matching `ir.model.data` pin. The cloned template
is findable only via its `key` field. Our template repin walks templates
by `key` first (rather than only via existing pins) and creates missing
`Fix-repair` pins so both resolution paths converge on the same record.

---

## Final scoreboard (post-v162)

| Layer | Studio-owned | Python-owned |
|---|---|---|
| Fields (helpdesk-repair scope) | **0** | 145+ |
| Custom models (`x_repair_*`) | 0 | 5 |
| Server actions | 0 | 46 (37 delegated + 9 repinned) |
| Base automations | 0 | 12 replaced by Python hooks |
| Views | 0 | 34 repinned |
| Reports | 0 | 17 repinned + templates |
| QWeb templates for Fix-repair reports | 0 | all pinned |

The helpdesk-repair scope is 100 % Python-owned. Studio no longer treats
any of it as its own; every future change lives under source control.
