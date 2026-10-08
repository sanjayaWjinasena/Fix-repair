# Fix-repair — `helpdesk.ticket`

[← back to Functional_Documentation.md](../Functional_Documentation.md)

### `helpdesk.ticket` — Helpdesk Ticket

*Extends a model created by `helpdesk`.* Python: `models/helpdesk_ticket.py`.

Other repos that use this model: `report BugFix-Studio-Misc.action_report_2093_repair_status` (BugFix-Studio-Misc)<br>`report BugFix-Studio-Misc.action_report_2094_repair_receipt` (BugFix-Studio-Misc)<br>`report BugFix-Studio-Misc.action_report_2237_customer_letter` (BugFix-Studio-Misc)<br>`report BugFix-Studio-Misc.action_report_2240_repair_final_notice` (BugFix-Studio-Misc)<br>`report BugFix-Studio-Misc.action_report_2241_repair_final_notice_scrappage` (BugFix-Studio-Misc)<br>`report BugFix-Studio-Misc.action_report_2420_helpdesk_ticket_report` (BugFix-Studio-Misc)<br>`report BugFix-Studio-Misc.action_report_3492_c09_repair_receipt` (BugFix-Studio-Misc)<br>`report BugFix-Studio-Misc.action_report_3494_c10_repair_estimate` (BugFix-Studio-Misc)<details><summary>+15 more</summary>`report BugFix-Studio-Misc.action_report_3495_c11_repair_quotation` (BugFix-Studio-Misc)<br>`report BugFix-Studio-Misc.action_report_3496_c12_repair_invoice` (BugFix-Studio-Misc)<br>`report BugFix-Studio-Misc.action_report_3510_c19_reminder_repair_reminding_letter` (BugFix-Studio-Misc)<br>`report BugFix-Studio-Misc.action_report_3511_c18_final_notice_estimated_scrappage` (BugFix-Studio-Misc)<br>`report BugFix-Studio-Misc.action_report_3512_c17_final_notice_scrappage` (BugFix-Studio-Misc)<br>`report BugFix-Studio-Misc.action_report_3513_c16_final_notice_estimated` (BugFix-Studio-Misc)<br>`report BugFix-Studio-Misc.action_report_3514_c15_final_notice` (BugFix-Studio-Misc)<br>`report BugFix-Studio-Misc.action_report_3515_c14_ready_for_collection_letter` (BugFix-Studio-Misc)<br>`report BugFix-Studio-Misc.action_report_3516_c13_repair_aod` (BugFix-Studio-Misc)<br>`server action BugFix-Stock.sa_f5_stock_return_picking_rr_auto_select_product_for_rug_repairs_3` (BugFix-Stock)<br>`server action BugFix-Stock.server_action_1991_rr_auto_select_product_for_rug_repairs_3` (BugFix-Stock)<br>`server action BugFix-Stock.server_action_1997_rr_rug_return_from_help_desk` (BugFix-Stock)<br>`server action BugFix-Studio-Misc.server_action_2799_mst_odoo_data_clean_up` (BugFix-Studio-Misc)<br>`stock.picking.x_studio_created_from_help_ticket` (BugFix-Stock)<br>`stock.picking.x_studio_helpdesk_ticket_id` (BugFix-Stock)</details>

**Summary:**

<!-- SUMMARY:model:helpdesk.ticket -->
This is the core of the module: a helpdesk ticket represents one repair job. About 120 fields are added. They cover repair type and RUG status (Repair Under Warranty, RUG Confirmed/Approved, RUG Approval Status), serial number and product, repair and return-receipt locations, cancel/reopen data, stage-transition markers, and numbered audit fields (Created By/On 1-10, factory and sales-centre shipped/received by/date). Movement buttons create completed stock transfers and move the ticket stage: Send to Factory, Received at Factory, Plan Intervention (`action_generate_fsm_task`), Send to Sales Centre and Received at Sales Centre. The Movements smart button (`action_view_repair_pickings`) lists those transfers. The form also has Assign to Me, Create Serial No, Change to RUG, and one-click Return and Dispatch, which skip the return wizard. Dispatch requires all invoices on the repair sales order to be posted and paid (`so_fully_paid`). The ticket becomes read-only after its first validated movement (`x_ticket_locked`). The Repair Completed stage cannot be reached a second time, and cancelled tickets cannot be deleted. Former Studio automations and server actions are now native methods: sequence numbering, auto-selecting product and sales order from the serial, user location validation, cancel/reopen, and the customer letter / final notice emails (10 mail templates).
<!-- /SUMMARY -->

**Fields (120):**

| Field | Label | Type | Function | How it gets its value | Depends on | Used by |
|---|---|---|---|---|---|---|
| `can_re_estimate` | Can Re Estimate | boolean | Computed but always False; currently has no effect. | computed by `_compute_can_re_estimate`; not stored | `helpdesk.ticket._compute_can_re_estimate()` |  |
| `has_ready_dispatch_picking` | Has Ready Dispatch Picking | boolean | Computed: true when a repair transfer to a customer location is Ready; controls the dispatch button on the ticket form. | computed by `_compute_has_ready_dispatch_picking`; not stored | `helpdesk.ticket._compute_has_ready_dispatch_picking()` | `view Fix-repair.helpdesk_ticket_form_assign_to_me` |
| `has_return_picking` | Has Return Picking | boolean | Computed: true when the ticket has any transfer, or, for Without-Serial-No repairs, when the item's serial was already collected from a customer location. | computed by `_compute_has_return_picking`; not stored | `helpdesk.ticket._compute_has_return_picking()` |  |
| `is_so_cancelled` | Is So Cancelled | boolean | Computed: true when the ticket's repair tasks have sales orders and at least one of them is cancelled. | computed by `_compute_is_so_cancelled`; not stored | `helpdesk.ticket._compute_is_so_cancelled()` |  |
| `is_tested_ok` | Is Tested Ok | boolean | Computed: true when any linked repair task is marked 'Tested OK' (Quick Repair status) or has End Quick Repair ticked. | computed by `_compute_is_tested_ok`; not stored | `helpdesk.ticket._compute_is_tested_ok()` |  |
| `name` | Subject | char | Ticket subject, defaulting to 'New'; Fix-repair replaces it with the repair sequence number when a repair ticket is created or written, and uses it when creating repair serial numbers. | default `New`; stored; required |  | `default Fix-repair.default_301_helpdesk_ticket_name`<br>`helpdesk.ticket._repair_seq_no_on_create_or_write()`<br>`helpdesk.ticket.action_create_repair_serial()` |
| `repair_picking_count` | Repair Picking Count | integer | Computed number of repair movements (transfers) linked to the ticket; shown on the ticket form's smart button. | computed by `_compute_repair_picking_count`; not stored | `helpdesk.ticket._compute_repair_picking_count()` | `view Fix-repair.helpdesk_ticket_form_assign_to_me` |
| `repair_picking_ids` | Movements | one2many → `stock.picking` | Stock transfers (movements) created for this repair ticket; used to count movements, detect a ready dispatch transfer and lock the ticket once a movement is done. | stored | `model stock.picking` (stock) | `helpdesk.ticket._compute_has_ready_dispatch_picking()`<br>`helpdesk.ticket._compute_repair_picking_count()`<br>`helpdesk.ticket._compute_x_ticket_locked()` |
| `repair_stage_state` | Repair Stage State | selection: new=New; sent_to_factory=Sent to Factory; received_at_factory=Received at Factory; estimation_sent_to_customer=Estimation Sent to Customer; repair_completed=Repair Completed; sent_to_sales_centre=Sent to Sales Centre; received_at_sales_centre=Received at Sales Centre; other=Other | Computed key of the ticket's current repair stage (New, Sent to Factory, ..., Received at Sales Centre, or Other) mapped from the stage name; used by the Direct Return action and form button visibility. | computed by `_compute_repair_stage_state`; stored | `helpdesk.ticket._compute_repair_stage_state()` | `helpdesk.ticket.fix_repair_action_direct_return()`<br>`view Fix-repair.helpdesk_ticket_form_assign_to_me` |
| `so_fully_paid` | So Fully Paid | boolean | Computed: true when every sales order of the ticket's repair tasks has at least one non-cancelled invoice and all such invoices are posted and In Payment or Paid. Gates the Dispatch button so the item is not handed back before the customer pays. | computed by `_compute_so_fully_paid`; not stored | `helpdesk.ticket._compute_so_fully_paid()` |  |
| `so_invoice_status` | Invoice Status | selection | Invoice status of the ticket's sales order (related); read-only information. | related `sale_order_id.invoice_status`; not stored | `helpdesk.ticket.sale_order_id` (helpdesk_sale)<br>`sale.order.invoice_status` (sale) |  |
| `task_done` | Task Done | boolean | Computed: true when the ticket has at least one field-service task marked done; controls buttons on the ticket form. | computed by `_compute_task_done`; not stored | `helpdesk.ticket._compute_task_done()` | `view Fix-repair.helpdesk_ticket_form_assign_to_me` |
| `x_studio_balance_due` | Balance Due | float | Amount still owed by the customer; printed in the repair collection and final-reminder email templates. | stored |  |  |
| `x_studio_branch` | Branch | selection: Colombo=Colombo; Gampah=Gampah | Branch of the ticket (Colombo or Gampah), entered manually; not used by any view or logic in this repo. | stored |  |  |
| `x_studio_cancel_reason` | Cancel Reason | text | Reason entered when the repair ticket is cancelled; written by the Cancel Repair handlers and shown on the ticket form. | stored |  | `helpdesk.ticket._repair_studio_cancel_repair()`<br>`helpdesk.ticket._repair_studio_cancel_repair_2()`<br>`view Fix-repair.ported_view_helpdesk_ticket_form_4012` |
| `x_studio_cancel_status` | Cancel Status | selection: None=None; Cancelled=Cancelled | Cancel status of the ticket ('None' or 'Cancelled'), with a default of None; shown on the ticket kanban. | stored |  | `default Fix-repair.default_360_helpdesk_ticket_x_studio_cancel_status`<br>`view Fix-repair.view_4735_odoo_studio_helpdesk_ticket_kanban_customization_e` |
| `x_studio_cancelled` | Cancelled | boolean | Marks the repair ticket as cancelled; checked by the cancelled-ticket validation automation and on delete, mirrored on tasks and used in form button conditions. | stored |  | `automation Fix-repair.base_automation_201_rr_validate_cancelled_tickets`<br>`helpdesk.ticket._repair_validate_cancelled_on_unlink()`<br>`project.task.x_studio_cancelled` (BugFix-Project)<br>`view Fix-repair.view_4013_odoo_studio_helpdesk_ticket_form_button_e` |
| `x_studio_cancelled_2` | Cancelled-2 | boolean | Second cancelled flag on the ticket; not used by any view or logic in this repo. | stored |  |  |
| `x_studio_cancelled_by` | Cancelled By | many2one → `res.users` | User who cancelled the repair ticket; shown on the ticket form. | stored | `model res.users` (base) | `view Fix-repair.ported_view_helpdesk_ticket_form_4012` |
| `x_studio_cancelled_date` | Cancelled Date | datetime | Date and time the repair ticket was cancelled; shown on the ticket form and kanban. | stored |  | `view Fix-repair.ported_view_helpdesk_ticket_form_4012`<br>`view Fix-repair.view_4735_odoo_studio_helpdesk_ticket_kanban_customization_e` |
| `x_studio_cancelled_stage_id` | Cancelled Stage Id | many2one → `helpdesk.stage` | Stage the ticket was in when it was cancelled; the Reopen Repair handler moves the ticket back to it. | stored | `model helpdesk.stage` (helpdesk) | `helpdesk.ticket._repair_studio_reopen_repair()` |
| `x_studio_cccc` | CCCC | char | Ticket type name (related); a leftover Studio test field not used by any view or logic in this repo. | related `ticket_type_id.name`; stored | `helpdesk.ticket.ticket_type_id` (helpdesk)<br>`helpdesk.ticket.type.name` (helpdesk) |  |
| `x_studio_cccc3` | CCCC3 | many2one → `helpdesk.stage` | Copy of the ticket's stage (related); a leftover Studio test field not used by any view or logic in this repo. | related `stage_id`; stored | `helpdesk.ticket.stage_id` (helpdesk)<br>`model helpdesk.stage` (helpdesk) |  |
| `x_studio_city` | City | selection: Gampaha=Gampaha; Colombo=Colombo; Yakkala=Yakkala | City of the ticket (Gampaha, Colombo or Yakkala), entered manually; not used by any view or logic in this repo. | stored |  |  |
| `x_studio_created_by_1` | Created By 1 | many2one → `res.users` | User who sent the item to the factory (stamped by the Send to Factory handler); audit field. | stored | `model res.users` (base) |  |
| `x_studio_created_by_10` | Created By 10 | many2one → `res.users` | User who received the item back at the sales centre (stamped by the Receive at Sales Centre handler); audit field. | stored | `model res.users` (base) |  |
| `x_studio_created_by_2` | Created By 2 | many2one → `res.users` | User who received the item at the factory (stamped by the Receive at Factory handler); audit field. | stored | `model res.users` (base) |  |
| `x_studio_created_by_3` | Created By 3 | many2one → `res.users` | User whose task creation moved the ticket to the next pipeline stage (stamped by the task's helpdesk pipeline-status update); audit field. | stored | `model res.users` (base) |  |
| `x_studio_created_by_4` | Created By 4 | many2one → `res.users` | User at the time the ticket was auto-moved to Estimation Sent (stamped by the Valid Confirmed SO compute); audit field. | stored | `model res.users` (base) |  |
| `x_studio_created_by_5` | Created By 5 | many2one → `res.users` | User at the time the ticket was auto-moved to Estimation Approved (stamped by the Valid Confirmed2 SO compute); audit field. | stored | `model res.users` (base) |  |
| `x_studio_created_by_6` | Created By 6 | many2one → `res.users` | User at the time the ticket was auto-moved to the Invoice stage (stamped by the Valid Invoiced SO compute); audit field. | stored | `model res.users` (base) |  |
| `x_studio_created_by_7` | Created By 7 | many2one → `res.users` | User at the time the ticket was auto-moved to Repair Started (stamped by the Valid Delivered SO compute); audit field. | stored | `model res.users` (base) |  |
| `x_studio_created_by_8` | Created By 8 | many2one → `res.users` | User at the time the ticket was auto-moved to Repair Completed (stamped by the Valid Delivered SO and Task Status computes); audit field. | stored | `model res.users` (base) |  |
| `x_studio_created_by_9` | Created By 9 | many2one → `res.users` | User who sent the item from the factory to the sales centre (stamped by the Send to Sales Centre handler); audit field. | stored | `model res.users` (base) |  |
| `x_studio_created_on_1` | Created On 1 | datetime | Date and time the item was sent to the factory (stamped by the Send to Factory handler); also printed in a customer collection-reminder email template as the hand-over date. | stored |  |  |
| `x_studio_created_on_10` | Created On 10 | datetime | Date and time the item was received back at the sales centre (stamped by the Receive at Sales Centre handler); audit field. | stored |  |  |
| `x_studio_created_on_2` | Created On 2 | datetime | Date and time the item was received at the factory (stamped by the Receive at Factory handler); audit field. | stored |  |  |
| `x_studio_created_on_3` | Created On 3 | datetime | Date and time a field-service task moved the ticket to the next pipeline stage (stamped by the task's pipeline-status update); audit field. | stored |  |  |
| `x_studio_created_on_4` | Created On 4 | datetime | Date and time the ticket was auto-moved to Estimation Sent (stamped by the Valid Confirmed SO compute); audit field. | stored |  |  |
| `x_studio_created_on_5` | Created On 5 | datetime | Date and time the ticket was auto-moved to Estimation Approved (stamped by the Valid Confirmed2 SO compute); audit field. | stored |  |  |
| `x_studio_created_on_6` | Created On 6 | datetime | Date and time the ticket was auto-moved to the Invoice stage (stamped by the Valid Invoiced SO compute); audit field. | stored |  |  |
| `x_studio_created_on_7` | Created On 7 | datetime | Date and time the ticket was auto-moved to Repair Started (stamped by the Valid Delivered SO compute); audit field. | stored |  |  |
| `x_studio_created_on_8` | Created On 8 | datetime | Date and time the ticket reached Repair Completed (stamped by the Valid Delivered SO and Task Status computes); used in the collection-reminder email as the notice date. | stored |  |  |
| `x_studio_created_on_9` | Created On 9 | datetime | Date and time the item was sent to the sales centre (stamped by the Send to Sales Centre handler); audit field. | stored |  |  |
| `x_studio_driver_name` | Driver Name | char | Name of the driver delivering the item; shown read-only under Delivery Details on the factory repair page. | stored |  |  |
| `x_studio_estimation_approved_stage_updated` | Estimation Approved Stage Updated | boolean | Marks that the ticket has passed the Estimation Approved stage; used by the Valid Confirmed2 SO compute. | stored |  | `helpdesk.ticket._compute_x_studio_valid_confirmed2_so()` |
| `x_studio_estimation_sent_stage_updated` | Estimation Sent Stage Updated | boolean | Marks that the ticket has passed the Estimation Sent stage; used by the Valid Confirmed SO compute. | stored |  | `helpdesk.ticket._compute_x_studio_valid_confirmed_so()` |
| `x_studio_f_received_by` | Received By | many2one → `res.users` | User who received the item at the factory (set by Received at Factory); shown read-only under Repair Transfer Details (Factory). | stored | `model res.users` (base) |  |
| `x_studio_f_received_date` | Received Date | datetime | Date and time the item was received at the factory (set by Received at Factory); shown read-only under Repair Transfer Details (Factory). | stored |  |  |
| `x_studio_f_shipped_by` | Shipped By | many2one → `res.users` | User who shipped the item from the factory back to the sales centre (set by Send to Sales Centre); shown read-only under Repair Transfer Details (Factory). | stored | `model res.users` (base) |  |
| `x_studio_f_shipped_date` | Shipped Date | datetime | Date and time the factory shipped the item back to the sales centre (set by Send to Sales Centre); shown read-only under Repair Transfer Details (Factory). | stored |  |  |
| `x_studio_fsm_task_done` | FSM Task Done | boolean | Computed: true when any linked field-service task is marked done or has End Quick Repair set. | computed by `_compute_x_studio_fsm_task_done`; not stored | `helpdesk.ticket._compute_x_studio_fsm_task_done()` |  |
| `x_studio_fully_paid_so` | Fully Paid SO | boolean | Computed: true when any linked field-service task has a fully invoiced sales order or ended as a quick repair. | computed by `_compute_x_studio_fully_paid_so`; not stored | `helpdesk.ticket._compute_x_studio_fully_paid_so()` |  |
| `x_studio_handed_over` | X Studio Handed Over | boolean | Computed: true when more than one of the ticket's transfers is done, meaning the item has been handed over. | computed by `_compute_x_studio_handed_over`; not stored | `helpdesk.ticket._compute_x_studio_handed_over()` | `helpdesk.ticket._compute_x_studio_handed_over()` |
| `x_studio_invoice_stage_updated` | Invoice Stage Updated | boolean | Marks that the ticket has passed the Invoice stage; used by the Valid Invoiced SO compute. | stored |  | `helpdesk.ticket._compute_x_studio_valid_invoiced_so()` |
| `x_studio_items` | Items | many2many → `product.product` | Products used in the repair, copied from the sales order lines when the ticket reaches Repair Completed; shown on the ticket form and list. | stored | `model product.product` (product) | `view Fix-repair.ported_view_helpdesk_ticket_form_4012`<br>`view Fix-repair.view_5027_odoo_studio_helpdesk_ticket_tree_customization_e` |
| `x_studio_job_location` | Job Location | selection: Centre Repair=Centre Repair; Factory Repair=Factory Repair | Where the repair is done: Centre Repair or Factory Repair; decides which transfers are created on Plan Intervention and Mark as Done and controls form buttons and the factory page. | stored |  | `helpdesk.ticket._create_mark_as_done_picking()`<br>`helpdesk.ticket._create_plan_intervention_picking()`<br>`view Fix-repair.view_4013_odoo_studio_helpdesk_ticket_form_button_e` |
| `x_studio_material_availability` | Material Availability | selection: Material Not Ready=Material Not Ready; Material Ready=Material Ready | Computed from the linked field-service tasks: takes the last task's Material Availability (default 'Material Not Ready'); shown on the ticket kanban. | computed by `_compute_x_studio_material_availability`; not stored | `helpdesk.ticket._compute_x_studio_material_availability()` | `view Fix-repair.view_4735_odoo_studio_helpdesk_ticket_kanban_customization_e` |
| `x_studio_materials_used` | Materials Used | many2one → `product.product` | Product of the ticket's sales order lines (related through Sales Order), shown in the ticket list as materials used. | related `x_studio_sale_order.order_line.product_id`; stored | `helpdesk.ticket.x_studio_sale_order`<br>`model product.product` (product)<br>`sale.order.line.product_id` (sale)<br>`sale.order.order_line` (sale) | `view Fix-repair.view_5027_odoo_studio_helpdesk_ticket_tree_customization_e` |
| `x_studio_normal_repair_with_serial_no` | Normal Repair (With Serial No) | boolean | Copied from the ticket type: marks a normal repair for an item with a serial number; controls ticket form elements. | related `ticket_type_id.x_studio_with_serial_no`; stored | `helpdesk.ticket.ticket_type_id` (helpdesk)<br>`helpdesk.ticket.type.x_studio_with_serial_no` | `view Fix-repair.ported_view_helpdesk_ticket_form_4012`<br>`view Fix-repair.view_4013_odoo_studio_helpdesk_ticket_form_button_e` |
| `x_studio_normal_repair_without_serial_no` | Normal Repair (Without Serial No) | boolean | Copied from the ticket type: marks a normal repair for an item without a serial number; used by the RUG product auto-select helpers and ticket form buttons. | related `ticket_type_id.x_studio_without_serial_no`; stored | `helpdesk.ticket.ticket_type_id` (helpdesk)<br>`helpdesk.ticket.type.x_studio_without_serial_no` | `helpdesk.ticket._repair_auto_select_product_for_rug()`<br>`helpdesk.ticket._repair_auto_select_product_for_rug_no_company()`<br>`view Fix-repair.ported_view_helpdesk_ticket_form_4012`<br>`view Fix-repair.view_4013_odoo_studio_helpdesk_ticket_form_button_e` |
| `x_studio_pick_id` | Pick Id | integer | Integer id of the transfer created for the repair, with a default; set and read by the route, serial-number and RUG product helpers and the Direct Dispatch action. | stored |  | `default Fix-repair.default_298_helpdesk_ticket_x_studio_pick_id`<br>`helpdesk.ticket._repair_auto_select_product_for_rug()`<br>`helpdesk.ticket._repair_auto_select_product_for_rug_no_company()`<br>`helpdesk.ticket._repair_studio_auto_create_repair_route()`<br>`helpdesk.ticket._repair_studio_auto_create_repair_serial_nos()`<details><summary>+3 more</summary>`helpdesk.ticket.fix_repair_action_direct_dispatch()`<br>`helpdesk.ticket.fix_repair_action_direct_return()`<br>`view Fix-repair.view_4013_odoo_studio_helpdesk_ticket_form_button_e`</details> |
| `x_studio_picking_id` | Picking Id | many2one → `stock.picking` | Transfer linked to the repair ticket; set and read by the repair route, serial-number and RUG auto-select product helpers. | stored | `model stock.picking` (stock) | `helpdesk.ticket._repair_auto_select_product_for_rug()`<br>`helpdesk.ticket._repair_auto_select_product_for_rug_no_company()`<br>`helpdesk.ticket._repair_studio_auto_create_repair_route()`<br>`helpdesk.ticket._repair_studio_auto_create_repair_serial_nos()` |
| `x_studio_qty` | Qty | char | Text list of the order line quantities copied when the ticket reaches Repair Completed; shown in the ticket list. | stored |  | `view Fix-repair.view_5027_odoo_studio_helpdesk_ticket_tree_customization_e` |
| `x_studio_quantity` | Quantity | float | Quantity of the ticket's sales order line (related through Sales Order); shown in the ticket list. | related `x_studio_sale_order.order_line.product_uom_qty`; stored | `helpdesk.ticket.x_studio_sale_order`<br>`sale.order.line.product_uom_qty` (sale)<br>`sale.order.order_line` (sale) | `view Fix-repair.view_5027_odoo_studio_helpdesk_ticket_tree_customization_e` |
| `x_studio_quick_repair_status` | Tested OK | selection: None=None; Quick Repair=Tested OK | Tested OK status of the ticket ('None' or 'Tested OK'), defaulting to None; read by the transfer cash-payment compute and shown on the ticket form and kanban. | stored |  | `default Fix-repair.default_372_helpdesk_ticket_x_studio_quick_repair_status`<br>`stock.picking._fix_repair_compute_cash_full_payment_made()`<br>`view Fix-repair.ported_view_helpdesk_ticket_form_4012`<br>`view Fix-repair.view_4735_odoo_studio_helpdesk_ticket_kanban_customization_e` |
| `x_studio_re_estimate_count` | Re-estimate Count | integer | Computed: number of re-estimates on the last linked task's sales order. | computed by `_compute_x_studio_re_estimate_count`; not stored | `helpdesk.ticket._compute_x_studio_re_estimate_count()` | `default Fix-repair.default_369_helpdesk_ticket_x_studio_re_estimate_count` |
| `x_studio_re_estimate_status` | Re-estimate Status | selection: None=None; Re-estimated=Re-estimated | Computed: 'Re-estimated' when any linked task's sales order has a re-estimate count above zero, else 'None'. | computed by `_compute_x_studio_re_estimate_status`; not stored | `helpdesk.ticket._compute_x_studio_re_estimate_status()` | `default Fix-repair.default_368_helpdesk_ticket_x_studio_re_estimate_status` |
| `x_studio_receive_at_centre` | Receive at Centre | boolean | Stores a Receive at Centre flag; not used by any view or logic in this repo. | stored |  |  |
| `x_studio_receive_at_factory` | Receive at Factory | boolean | Receive at Factory flag on the ticket; used in ticket form button conditions. | stored |  | `view Fix-repair.view_4013_odoo_studio_helpdesk_ticket_form_button_e` |
| `x_studio_related_field_FNjnC` | New Related Field | one2many → `project.task` | All tasks of the ticket's project (related); leftover Studio field not used by any view or logic in this repo. | related `project_id.task_ids`; not stored | `helpdesk.ticket.project_id` (helpdesk_timesheet)<br>`model project.task` (project)<br>`project.project.task_ids` (project) |  |
| `x_studio_related_field_QuqN1` | New Related Field | integer | Ticket id taken from the project's tasks (related); leftover Studio field not used by any view or logic in this repo. | related `project_id.task_ids.helpdesk_ticket_id.id`; stored | `helpdesk.ticket.id` (helpdesk)<br>`helpdesk.ticket.project_id` (helpdesk_timesheet)<br>`project.project.task_ids` (project)<br>`project.task.helpdesk_ticket_id` (helpdesk_fsm) |  |
| `x_studio_related_information` | Related Information | binary | Attachment with related information uploaded on the ticket; shown on the ticket form and copied to its tasks. | stored |  | `project.task.x_studio_related_information` (BugFix-Project)<br>`view Fix-repair.ported_view_helpdesk_ticket_form_4012` |
| `x_studio_reopen_status` | Reopen Status | selection: None=None; Reopened=Reopened | Reopen status of the ticket ('None' or 'Reopened'), defaulting to None; shown on the ticket kanban. | stored |  | `default Fix-repair.default_361_helpdesk_ticket_x_studio_reopen_status`<br>`view Fix-repair.view_4735_odoo_studio_helpdesk_ticket_kanban_customization_e` |
| `x_studio_reopened` | Reopened | boolean | Stores whether the ticket was reopened; not used by any view or logic in this repo. | stored |  |  |
| `x_studio_reopened_by` | Reopened By | many2one → `res.users` | User who reopened the cancelled ticket; shown on the ticket form. | stored | `model res.users` (base) | `view Fix-repair.ported_view_helpdesk_ticket_form_4012` |
| `x_studio_reopened_date` | Reopened Date | datetime | Date and time the ticket was reopened; shown on the ticket form and kanban. | stored |  | `view Fix-repair.ported_view_helpdesk_ticket_form_4012`<br>`view Fix-repair.view_4735_odoo_studio_helpdesk_ticket_kanban_customization_e` |
| `x_studio_repair_complete_stage_updated` | Repair Complete Stage Updated | boolean | Marks that the ticket has passed the Repair Completed stage; used by task-status, delivered/invoiced validity computes, mirrored on tasks and read by the transfer cash-payment compute. | stored |  | `helpdesk.ticket._compute_x_studio_task_status()`<br>`helpdesk.ticket._compute_x_studio_valid_delivered_so()`<br>`helpdesk.ticket._compute_x_studio_valid_invoiced_so()`<br>`project.task.x_studio_repair_completed_stage_updated` (BugFix-Project)<br>`stock.picking._fix_repair_compute_cash_full_payment_made()` |
| `x_studio_repair_location` | Repair Location | many2one → `stock.location` | Stock location where the item is repaired; filled by the repair-location populate helper and used when creating the Send to Factory transfer and finding the item's current location. | stored | `model stock.location` (stock) | `helpdesk.ticket._create_send_to_factory_picking()`<br>`helpdesk.ticket._current_item_location()`<br>`helpdesk.ticket._repair_populate_repair_location()` |
| `x_studio_repair_reason` | Repair Reason | many2many → `x_repair_reason_custom` | Repair reasons selected for the ticket (from the custom Repair Reason list); shown in the ticket list view. | stored | `model x_repair_reason_custom` | `view Fix-repair.view_5027_odoo_studio_helpdesk_ticket_tree_customization_e` |
| `x_studio_repair_serial_created` | Repair Serial Created | boolean | Flag that the repair serial number and route were already auto-created, preventing re-creation; used in form button conditions. | stored |  | `helpdesk.ticket._repair_studio_auto_create_repair_route()`<br>`helpdesk.ticket._repair_studio_auto_create_repair_serial_nos()`<br>`view Fix-repair.view_4013_odoo_studio_helpdesk_ticket_form_button_e` |
| `x_studio_repair_started_stage_updated` | Repair Started Stage Updated | boolean | Marks that the ticket has passed the Repair Started stage; used by the Valid Delivered SO compute. | stored |  | `helpdesk.ticket._compute_x_studio_valid_delivered_so()` |
| `x_studio_return_receipt_location` | Return Receipt Location | many2one → `stock.location` | Location where the repaired item is received back; used to build the repair route and the plan-intervention and send-to-sales-centre transfers, and for location validation. | stored | `model stock.location` (stock) | `helpdesk.ticket._compute_x_studio_user_location_validation()`<br>`helpdesk.ticket._create_plan_intervention_picking()`<br>`helpdesk.ticket._create_send_to_sales_centre_picking()`<br>`helpdesk.ticket._onchange_repair_populate_repair_location()`<br>`helpdesk.ticket._repair_populate_repair_location()`<details><summary>+3 more</summary>`helpdesk.ticket._repair_studio_auto_create_repair_route()`<br>`helpdesk.ticket._repair_studio_auto_create_repair_serial_nos()`<br>`helpdesk.ticket._repair_studio_user_location_validation()`</details> |
| `x_studio_rug_approval_status` | RUG Approval Status | selection: Pending RUG Approval=Pending RUG Approval; RUG Approved=RUG Approved; RUG Rejected=RUG Rejected | Computed RUG approval status from the linked field-service tasks' sales orders: Approved, Rejected or Pending (the last task with an order wins); shown on the ticket kanban. | computed by `_compute_x_studio_rug_approval_status`; not stored | `helpdesk.ticket._compute_x_studio_rug_approval_status()` | `view Fix-repair.view_4735_odoo_studio_helpdesk_ticket_kanban_customization_e` |
| `x_studio_rug_approved` | RUG Approved | boolean | Stores whether the RUG request was approved; not used by any view or logic in this repo. | stored |  |  |
| `x_studio_rug_confirmed` | RUG Confirmed | boolean | RUG Confirmed flag copied from the ticket type; shown on the ticket form and kanban. | related `ticket_type_id.x_studio_rug_confirmed`; stored | `helpdesk.ticket.ticket_type_id` (helpdesk)<br>`helpdesk.ticket.type.x_studio_rug_confirmed` | `view Fix-repair.ported_view_helpdesk_ticket_form_4012`<br>`view Fix-repair.view_4735_odoo_studio_helpdesk_ticket_kanban_customization_e` |
| `x_studio_rug_repair` | Repair Under Warranty | boolean | Shows whether the ticket type is a Repair Under Warranty (related to the ticket type's RUG flag); controls ticket form elements. | related `ticket_type_id.x_studio_rug`; stored | `helpdesk.ticket.ticket_type_id` (helpdesk)<br>`helpdesk.ticket.type.x_studio_rug` | `view Fix-repair.ported_view_helpdesk_ticket_form_4012`<br>`view Fix-repair.view_4013_odoo_studio_helpdesk_ticket_form_button_e` |
| `x_studio_rug_request_sent` | RUG Request Sent | boolean | Stores whether a RUG approval request was sent; not used by any view or logic in this repo. | stored |  |  |
| `x_studio_s_received_by` | Received By | many2one → `res.users` | User who received the repaired item back at the sales centre (set by Received at Sales Centre); shown read-only under Repair Transfer Details (Sales Centre). | stored | `model res.users` (base) |  |
| `x_studio_s_received_date` | Received Date | datetime | Date and time the repaired item was received back at the sales centre (set by Received at Sales Centre); shown read-only under Repair Transfer Details (Sales Centre). | stored |  |  |
| `x_studio_s_shipped_by` | Shipped By | many2one → `res.users` | User who shipped the item from the sales centre to the factory (set by Send to Factory); shown read-only under Repair Transfer Details (Sales Centre). | stored | `model res.users` (base) |  |
| `x_studio_s_shipped_date` | Shipped Date | datetime | Date and time the sales centre shipped the item to the factory (set by Send to Factory); shown read-only under Repair Transfer Details (Sales Centre). | stored |  |  |
| `x_studio_sale_order` | Sales Order | many2one → `sale.order` | Computed: the sales order of the last linked field-service task that has one; source for materials, quantity and price columns and for the Repair Completed item copy. | computed by `_compute_x_studio_sale_order`; not stored | `helpdesk.ticket._compute_x_studio_sale_order()`<br>`model sale.order` (sale) | `helpdesk.ticket._compute_x_studio_task_status()`<br>`helpdesk.ticket._compute_x_studio_valid_delivered_so()`<br>`helpdesk.ticket.x_studio_materials_used`<br>`helpdesk.ticket.x_studio_quantity`<br>`helpdesk.ticket.x_studio_unit_price`<details><summary>+1 more</summary>`view Fix-repair.view_5027_odoo_studio_helpdesk_ticket_tree_customization_e`</details> |
| `x_studio_sales_price` | Sales Price | char | Text list of the order line unit prices copied when the ticket reaches Repair Completed; shown in the ticket list. | stored |  | `view Fix-repair.view_5027_odoo_studio_helpdesk_ticket_tree_customization_e` |
| `x_studio_send_to_centre` | Send to Centre | boolean | Stores a Send to Centre flag; not used by any view or logic in this repo. | stored |  |  |
| `x_studio_send_to_factory` | Send to Factory | boolean | Stores a Send to Factory flag; not used by any view or logic in this repo. | stored |  |  |
| `x_studio_serial_no` | Serial Number | many2one → `stock.lot` | Serial number (lot) of the item brought in for repair; drives the product sync onchange, repair transfer creation, RUG product auto-selection and the Has Return Picking check. | stored | `model stock.lot` (stock) | `helpdesk.ticket._compute_has_return_picking()`<br>`helpdesk.ticket._create_repair_transfer()`<br>`helpdesk.ticket._onchange_serial_no_product()`<br>`helpdesk.ticket._post_write_serial_product_sync()`<br>`helpdesk.ticket._repair_auto_select_product_for_rug()`<details><summary>+3 more</summary>`helpdesk.ticket._repair_auto_select_product_for_rug_no_company()`<br>`helpdesk.ticket._repair_studio_auto_create_repair_serial_nos()`<br>`stock.return.picking._create_returns()`</details> |
| `x_studio_serial_number` | Serial Number-11 | many2one → `stock.lot` | Secondary serial number field ('Serial Number-11'); only read by the RUG auto-select-product onchange. | stored | `model stock.lot` (stock) | `helpdesk.ticket._onchange_repair_auto_select_product_for_rug()` |
| `x_studio_sn_updated` | SN Updated | boolean | Flag that the serial number/product was already updated on the ticket; set by the RUG auto-select helper and used in form button conditions. | stored |  | `helpdesk.ticket._repair_auto_select_product_for_rug_no_company()`<br>`view Fix-repair.view_4013_odoo_studio_helpdesk_ticket_form_button_e` |
| `x_studio_source_location` | Source Location | many2one → `stock.location` | Source stock location copied from the assigned user's settings; used when auto-creating the repair route and serial numbers. | related `user_id.x_studio_source_location`; stored | `helpdesk.ticket.user_id` (helpdesk)<br>`model stock.location` (stock)<br>`res.users.x_studio_source_location` (studio_usermodel_migration) | `helpdesk.ticket._repair_studio_auto_create_repair_route()`<br>`helpdesk.ticket._repair_studio_auto_create_repair_serial_nos()` |
| `x_studio_source_location_1` | Source Location | many2one → `stock.location` | Second source location copied from the assigned user's settings; used when auto-creating the repair route and serial numbers. | related `user_id.x_studio_source_location_1`; stored | `helpdesk.ticket.user_id` (helpdesk)<br>`model stock.location` (stock)<br>`res.users.x_studio_source_location_1` (studio_usermodel_migration) | `helpdesk.ticket._repair_studio_auto_create_repair_route()`<br>`helpdesk.ticket._repair_studio_auto_create_repair_serial_nos()`<br>`view Fix-repair.ported_view_helpdesk_ticket_form_4012` |
| `x_studio_stage_date` | Stage Date | datetime | Date and time of the ticket's last automatic repair-stage change, stamped by the stage-moving computes and handlers; shown on the ticket kanban. | stored |  | `view Fix-repair.view_4735_odoo_studio_helpdesk_ticket_kanban_customization_e` |
| `x_studio_stage_name` | Stage Name | char | Name of the ticket's current stage (related); not used by any view or logic in this repo. | related `stage_id.name`; stored | `helpdesk.stage.name` (helpdesk)<br>`helpdesk.ticket.stage_id` (helpdesk) |  |
| `x_studio_task_status` | Task Status | boolean | Computed: true when a linked field-service task is done or ended as a quick repair; the first time it moves the ticket to Repair Completed (stage 9/28), stamps Created By/On 8 and copies sales order items. The sales-order fallback branch compares a record to True and never runs. | computed by `_compute_x_studio_task_status`; not stored | `helpdesk.ticket._compute_x_studio_task_status()` |  |
| `x_studio_tracking` | Tracking | selection: lot=By Lots; none=No Tracking; serial=By Unique Serial Number | Tracking mode of the ticket's product (by lots, serial or none), related from the product; shown on the ticket form. | related `product_id.tracking`; not stored | `helpdesk.ticket.product_id` (helpdesk_stock)<br>`product.product.tracking` (stock) | `view Fix-repair.ported_view_helpdesk_ticket_form_4012` |
| `x_studio_unit_price` | Unit Price | char | Value related to the sales order pricelist's item price; shown as Unit Price in the ticket list. Typed as text and its help text describes a rule name, so the value may not be a real price. | related `x_studio_sale_order.pricelist_id.item_ids.price`; not stored | `helpdesk.ticket.x_studio_sale_order`<br>`product.pricelist.item.price` (product)<br>`product.pricelist.item_ids` (product)<br>`sale.order.pricelist_id` (sale) | `view Fix-repair.view_5027_odoo_studio_helpdesk_ticket_tree_customization_e` |
| `x_studio_user_location_validation` | User Location Validation | boolean | Computed: true when the ticket has a Return Receipt Location and the current user is NOT among that location's allowed stock users; checked by the User Location Validation handler to block unauthorised users. | computed by `_compute_x_studio_user_location_validation`; not stored | `helpdesk.ticket._compute_x_studio_user_location_validation()` | `helpdesk.ticket._repair_studio_user_location_validation()` |
| `x_studio_valid_confirm_return` | Valid Confirm Return | boolean | Computed: true when at least one of the ticket's transfers is done; used in ticket form button conditions. | computed by `_compute_x_studio_valid_confirm_return`; not stored | `helpdesk.ticket._compute_x_studio_valid_confirm_return()` | `view Fix-repair.view_4013_odoo_studio_helpdesk_ticket_form_button_e` |
| `x_studio_valid_confirmed2_so` | Valid Confirmed2 SO | boolean | Computed: true when any linked task's sales order is locked (done). The first time, it also moves the ticket to the Estimation Approved stage (stage id 12 or 31 by company) and stamps Stage Date and Created By/On 5. | computed by `_compute_x_studio_valid_confirmed2_so`; not stored | `helpdesk.ticket._compute_x_studio_valid_confirmed2_so()` |  |
| `x_studio_valid_confirmed_so` | Valid Confirmed SO | boolean | Computed: true when any linked task's sales order is in 'Quotation Sent'. The first time, it also moves the ticket to the Estimation Sent stage (hard-coded stage id 10 or 29 by company) and stamps Stage Date and Created By/On 4. | computed by `_compute_x_studio_valid_confirmed_so`; not stored | `helpdesk.ticket._compute_x_studio_valid_confirmed_so()` |  |
| `x_studio_valid_delivered_so` | Valid Delivered SO | boolean | Computed from linked tasks' delivery checks. A customer delivery moves the ticket to Repair Completed (stage 9/28), stamps Created By/On 8 and copies order items, quantities and prices; any done delivery otherwise moves it to Repair Started (stage 11/30, Created By/On 7). | computed by `_compute_x_studio_valid_delivered_so`; not stored | `helpdesk.ticket._compute_x_studio_valid_delivered_so()` |  |
| `x_studio_valid_invoiced_so` | Valid Invoiced SO | boolean | Computed: true when a linked non-Credit task's order counts as invoiced/paid. The first time (before Repair Completed), it also moves the ticket to the Invoice stage (stage id 3 or 22), stamps Created By/On 6 and sets Invoice Stage Updated. | computed by `_compute_x_studio_valid_invoiced_so`; not stored | `helpdesk.ticket._compute_x_studio_valid_invoiced_so()` |  |
| `x_studio_valid_return` | Valid Return | boolean | Computed: true when the ticket has at least one transfer that is not cancelled; used in ticket form button conditions. | computed by `_compute_x_studio_valid_return`; not stored | `helpdesk.ticket._compute_x_studio_valid_return()` | `view Fix-repair.view_4013_odoo_studio_helpdesk_ticket_form_button_e` |
| `x_studio_vehicle_details` | Vehicle Details | char | Vehicle used to deliver the item; shown read-only under Delivery Details on the factory repair page. | stored |  |  |
| `x_studio_virtual_location` | Virtual Location | many2one → `stock.location` | Virtual stock location copied from the assigned user's settings; used when creating the mark-as-done and received-at-sales-centre transfers and the repair route. | related `user_id.x_studio_virtual_location`; stored | `helpdesk.ticket.user_id` (helpdesk)<br>`model stock.location` (stock)<br>`res.users.x_studio_virtual_location` (studio_usermodel_migration) | `helpdesk.ticket._create_mark_as_done_picking()`<br>`helpdesk.ticket._create_received_at_sales_centre_picking()`<br>`helpdesk.ticket._repair_studio_auto_create_repair_route()`<br>`helpdesk.ticket._repair_studio_auto_create_repair_serial_nos()` |
| `x_studio_virtual_location_1` | Virtual Location | many2one → `stock.location` | Second virtual location copied from the assigned user's settings; used in the same transfer and route creation as Virtual Location. | related `user_id.x_studio_virtual_location_1`; stored | `helpdesk.ticket.user_id` (helpdesk)<br>`model stock.location` (stock)<br>`res.users.x_studio_virtual_location_1` (studio_usermodel_migration) | `helpdesk.ticket._create_mark_as_done_picking()`<br>`helpdesk.ticket._create_received_at_sales_centre_picking()`<br>`helpdesk.ticket._repair_studio_auto_create_repair_route()`<br>`helpdesk.ticket._repair_studio_auto_create_repair_serial_nos()` |
| `x_studio_virtual_location_id` | Virtual Location Id | integer | Numeric id of the assigned user's virtual location (related); used in ticket form button conditions. | related `user_id.x_studio_virtual_location.id`; stored | `helpdesk.ticket.user_id` (helpdesk)<br>`res.users.x_studio_virtual_location` (studio_usermodel_migration)<br>`stock.location.id` (stock) | `view Fix-repair.view_4013_odoo_studio_helpdesk_ticket_form_button_e` |
| `x_studio_warranty_card` | Warranty Card | binary | Warranty card attachment uploaded on the ticket; used when changing the repair type to RUG and copied to the ticket's tasks. | stored |  | `helpdesk.ticket._repair_studio_change_repair_type_to_rug()`<br>`project.task.x_studio_warranty_card` (BugFix-Project)<br>`view Fix-repair.ported_view_helpdesk_ticket_form_4012` |
| `x_ticket_locked` | X Ticket Locked | boolean | Computed: true once any linked repair movement is validated (done); freezes the ticket form so intake data stays as it was at the first movement. | computed by `_compute_x_ticket_locked`; not stored | `helpdesk.ticket._compute_x_ticket_locked()` |  |
| `x_x_studio_created_from_help_ticket_stock_picking_count` | Created from Help Ticket count | integer | Computed count of transfers whose 'Created from Help Ticket' is this ticket. | computed by `_compute_x_x_studio_created_from_help_ticket_stock_picking_count`; not stored | `helpdesk.ticket._compute_x_x_studio_created_from_help_ticket_stock_picking_count()` |  |

**Python methods (104):**

| Method | Function | Decorators | Extends standard | Depends on | Used by | Where |
|---|---|---|---|---|---|---|
| `_compute_x_studio_rug_approval_status` | Compute for RUG Approval Status: loops over the ticket's field-service tasks' sales orders and sets Approved, Rejected or Pending (the last task with an order wins). | api.depends('fsm_task_ids.sale_order_id.x_studio_rug_approved', 'fsm_task_ids.sa… |  | `helpdesk.ticket.fsm_task_ids` (helpdesk_fsm)<br>`project.task.sale_order_id` (sale_project)<br>`sale.order.x_studio_rug_approved` (BugFix-Sales)<br>`sale.order.x_studio_rug_rejected` (BugFix-Sales) | `helpdesk.ticket.x_studio_rug_approval_status` | `models/helpdesk_ticket.py:120` |
| `_compute_x_studio_fsm_task_done` | Compute for FSM Task Done: true when any linked field-service task is done or has End Quick Repair ticked. | api.depends('fsm_task_ids') |  | `helpdesk.ticket.fsm_task_ids` (helpdesk_fsm) | `helpdesk.ticket.x_studio_fsm_task_done` | `models/helpdesk_ticket.py:388` |
| `_compute_x_studio_fully_paid_so` | Compute for Fully Paid SO: true when any linked task's order is fully invoiced or the task ended as a quick repair. | api.depends('fsm_task_ids') |  | `helpdesk.ticket.fsm_task_ids` (helpdesk_fsm) | `helpdesk.ticket.x_studio_fully_paid_so` | `models/helpdesk_ticket.py:406` |
| `_compute_x_studio_valid_confirm_return` | Compute for Valid Confirm Return: true when at least one of the ticket's transfers is done. | api.depends('picking_ids') |  | `helpdesk.ticket.picking_ids` (helpdesk_stock) | `helpdesk.ticket.x_studio_valid_confirm_return` | `models/helpdesk_ticket.py:424` |
| `_compute_x_studio_valid_return` | Compute for Valid Return: true when the ticket has at least one transfer that is not cancelled. | api.depends('picking_ids') |  | `helpdesk.ticket.picking_ids` (helpdesk_stock) | `helpdesk.ticket.x_studio_valid_return` | `models/helpdesk_ticket.py:440` |
| `_compute_x_studio_user_location_validation` | Compute for User Location Validation: true when the Return Receipt Location is set and the current user is not in its allowed stock-location users. | api.depends('x_studio_return_receipt_location') |  | `helpdesk.ticket.x_studio_return_receipt_location`<br>`model stock.location` (stock)<br>`stock.location.id` (stock) | `helpdesk.ticket.x_studio_user_location_validation` | `models/helpdesk_ticket.py:456` |
| `_compute_x_studio_valid_confirmed_so` | Compute for Valid Confirmed SO: true when a task's order is 'Quotation Sent'; the first time it also moves the ticket to Estimation Sent (hard-coded stage 10 or 29 by company) and stamps Stage Date and Created By/On 4. | api.depends('fsm_task_ids') |  | `helpdesk.ticket.fsm_task_ids` (helpdesk_fsm)<br>`helpdesk.ticket.x_studio_estimation_sent_stage_updated`<br>`model res.company` (base) | `helpdesk.ticket.x_studio_valid_confirmed_so` | `models/helpdesk_ticket.py:479` |
| `_compute_x_studio_valid_confirmed2_so` | Compute for Valid Confirmed2 SO: true when a task's order is locked; the first time it moves the ticket to Estimation Approved (hard-coded stage 12 or 31) and stamps Created By/On 5. | api.depends('fsm_task_ids') |  | `helpdesk.ticket.fsm_task_ids` (helpdesk_fsm)<br>`helpdesk.ticket.x_studio_estimation_approved_stage_updated`<br>`model res.company` (base) | `helpdesk.ticket.x_studio_valid_confirmed2_so` | `models/helpdesk_ticket.py:507` |
| `_compute_x_studio_valid_invoiced_so` | Compute for Valid Invoiced SO: true when a non-Credit task's order counts as paid; the first time (before Repair Completed) it moves the ticket to the Invoice stage (hard-coded 3 or 22) and stamps Created By/On 6. | api.depends('fsm_task_ids') |  | `helpdesk.ticket.fsm_task_ids` (helpdesk_fsm)<br>`helpdesk.ticket.x_studio_invoice_stage_updated`<br>`helpdesk.ticket.x_studio_repair_complete_stage_updated`<br>`model res.company` (base) | `helpdesk.ticket.x_studio_valid_invoiced_so` | `models/helpdesk_ticket.py:535` |
| `_compute_x_studio_valid_delivered_so` | Compute for Valid Delivered SO: on a customer delivery it moves the ticket to Repair Completed (stage 9/28), stamps Created By/On 8 and copies order items, quantities and prices; otherwise any done delivery moves it to Repair Started (11/30). | api.depends('fsm_task_ids') |  | `helpdesk.ticket.fsm_task_ids` (helpdesk_fsm)<br>`helpdesk.ticket.x_studio_repair_complete_stage_updated`<br>`helpdesk.ticket.x_studio_repair_started_stage_updated`<br>`helpdesk.ticket.x_studio_sale_order`<br>`model res.company` (base)<details><summary>+2 more</summary>`model sale.order.line` (sale)<br>`sale.order.id` (sale)</details> | `helpdesk.ticket.x_studio_valid_delivered_so` | `models/helpdesk_ticket.py:567` |
| `_compute_x_studio_task_status` | Compute for Task Status: true when a linked field-service task is done or ended as a quick repair; the first time it moves the ticket to Repair Completed (hard-coded stage 9/28), stamps Created By/On 8 and copies order items. Its sales-order fallback compares a record to True and never runs. | api.depends('fsm_task_ids') |  | `helpdesk.ticket.fsm_task_ids` (helpdesk_fsm)<br>`helpdesk.ticket.x_studio_repair_complete_stage_updated`<br>`helpdesk.ticket.x_studio_sale_order`<br>`model res.company` (base)<br>`model sale.order.line` (sale)<details><summary>+3 more</summary>`model stock.picking` (stock)<br>`sale.order.id` (sale)<br>`sale.order.state` (sale)</details> | `helpdesk.ticket.x_studio_task_status` | `models/helpdesk_ticket.py:625` |
| `_compute_x_studio_material_availability` | Compute for the ticket's Material Availability: copies the value from the last linked field-service task, defaulting to 'Material Not Ready'. | api.depends('fsm_task_ids') |  | `helpdesk.ticket.fsm_task_ids` (helpdesk_fsm) | `helpdesk.ticket.x_studio_material_availability` | `models/helpdesk_ticket.py:897` |
| `_compute_x_studio_re_estimate_count` | Compute for Re-estimate Count: takes the re-estimate count of the last linked task's sales order. | api.depends('fsm_task_ids') |  | `helpdesk.ticket.fsm_task_ids` (helpdesk_fsm) | `helpdesk.ticket.x_studio_re_estimate_count` | `models/helpdesk_ticket.py:925` |
| `_compute_x_studio_re_estimate_status` | Compute for Re-estimate Status: 'Re-estimated' when any linked task's sales order has been re-estimated at least once, otherwise 'None'. | api.depends('fsm_task_ids') |  | `helpdesk.ticket.fsm_task_ids` (helpdesk_fsm) | `helpdesk.ticket.x_studio_re_estimate_status` | `models/helpdesk_ticket.py:944` |
| `_compute_x_studio_sale_order` | Compute for the ticket's Sales Order: the order of the last linked field-service task that has one. | api.depends('fsm_task_ids') |  | `helpdesk.ticket.fsm_task_ids` (helpdesk_fsm) | `helpdesk.ticket.x_studio_sale_order` | `models/helpdesk_ticket.py:987` |
| `_compute_x_x_studio_created_from_help_ticket_stock_picking_count` | Compute for 'Created from Help Ticket count': counts transfers whose Created from Help Ticket is this ticket. |  |  | `model stock.picking` (stock) | `helpdesk.ticket.x_x_studio_created_from_help_ticket_stock_picking_count` | `models/helpdesk_ticket.py:1032` |
| `_migrate_studio_rug_cluster_to_base` | One-time upgrade helper: hands the seven RUG-related ticket fields over from Studio to this module (sets them to base fields and removes their studio_customization ownership records). Data is kept; safe to re-run. | api.model |  | `model ir.model.data` (base)<br>`model ir.model.fields` (base) |  | `models/helpdesk_ticket.py:1040` |
| `_migrate_studio_location_cluster_to_base` | One-time upgrade helper: hands the nine repair location/picking ticket fields over from Studio to this module (state to base, Studio ownership records removed). Data is kept; safe to re-run. | api.model |  | `model ir.model.data` (base)<br>`model ir.model.fields` (base) |  | `models/helpdesk_ticket.py:1090` |
| `_migrate_studio_stage_marker_cluster_to_base` | One-time upgrade helper: hands the ten stage-marker boolean ticket fields (Send to Factory ... Handed Over) over from Studio to this module. Data is kept; safe to re-run. | api.model |  | `model ir.model.data` (base)<br>`model ir.model.fields` (base) |  | `models/helpdesk_ticket.py:1131` |
| `_migrate_studio_stage_validation_cluster_to_base` | One-time upgrade helper: hands the ten stage-validation computed ticket fields (FSM Task Done ... Task Status) over from Studio to this module. Data is kept; safe to re-run. | api.model |  | `model ir.model.data` (base)<br>`model ir.model.fields` (base) |  | `models/helpdesk_ticket.py:1173` |
| `_migrate_studio_audit_cluster_to_base` | One-time upgrade helper: hands the 29 audit fields (Stage Date, Created By/On 1-10, factory and sales-centre shipped/received) over from Studio to this module. Data is kept; safe to re-run. | api.model |  | `model ir.model.data` (base)<br>`model ir.model.fields` (base) |  | `models/helpdesk_ticket.py:1214` |
| `_migrate_studio_serial_product_cluster_to_base` | One-time upgrade helper: hands the eleven serial-number, repair-reason and item snapshot ticket fields over from Studio to this module. Data is kept; safe to re-run. | api.model |  | `model ir.model.data` (base)<br>`model ir.model.fields` (base) |  | `models/helpdesk_ticket.py:1260` |
| `_migrate_studio_misc_cluster_to_base` | One-time upgrade helper: hands the remaining 20 miscellaneous Studio ticket fields (branch, city, job location, warranty card, etc.) over from Studio to this module. Data is kept; safe to re-run. | api.model |  | `model ir.model.data` (base)<br>`model ir.model.fields` (base) |  | `models/helpdesk_ticket.py:1300` |
| `_migrate_studio_cancel_cluster_to_base` | One-time upgrade helper: hands the eleven cancel/reopen ticket fields over from Studio to this module. Data is kept; safe to re-run. | api.model |  | `model ir.model.data` (base)<br>`model ir.model.fields` (base) |  | `models/helpdesk_ticket.py:1348` |
| `_compute_can_re_estimate` | Compute for Can Re Estimate on tickets: always sets False, so it has no effect. |  |  |  | `helpdesk.ticket.can_re_estimate` | `models/helpdesk_ticket.py:1415` |
| `_compute_has_ready_dispatch_picking` | Compute for Has Ready Dispatch Picking: true when one of the ticket's repair movements going to a customer location is in Ready state. | api.depends('repair_picking_ids.state', 'repair_picking_ids.location_dest_id.usa… |  | `helpdesk.ticket.repair_picking_ids`<br>`stock.location.usage` (stock)<br>`stock.picking.location_dest_id` (stock)<br>`stock.picking.state` (stock) | `helpdesk.ticket.has_ready_dispatch_picking` | `models/helpdesk_ticket.py:1424` |
| `_compute_repair_picking_count` | Compute for Repair Picking Count: number of repair movements linked to the ticket. | api.depends('repair_picking_ids') |  | `helpdesk.ticket.repair_picking_ids` | `helpdesk.ticket.repair_picking_count` | `models/helpdesk_ticket.py:1462` |
| `_compute_x_ticket_locked` | Compute for X Ticket Locked: true once any repair movement of the ticket is done, which freezes the ticket form. | api.depends('repair_picking_ids.state') |  | `helpdesk.ticket.repair_picking_ids`<br>`stock.picking.state` (stock) | `helpdesk.ticket.x_ticket_locked` | `models/helpdesk_ticket.py:1482` |
| `action_view_repair_pickings` | Movements smart-button handler: opens the list of transfers linked to this ticket, with new transfers defaulting to this ticket. |  |  |  | `view Fix-repair.helpdesk_ticket_form_assign_to_me` | `models/helpdesk_ticket.py:1489` |
| `fix_repair_action_direct_return` | One-click Return button: builds the return wizard in the background with the ticket's picking, partner and company (and ticket when in New stage) and immediately creates the return, opening the new RET transfer. |  |  | `helpdesk.ticket.company_id` (helpdesk)<br>`helpdesk.ticket.partner_id` (helpdesk)<br>`helpdesk.ticket.repair_stage_state`<br>`helpdesk.ticket.x_studio_pick_id`<br>`model stock.return.picking` (stock)<details><summary>+2 more</summary>`res.company.id` (base)<br>`res.partner.id` (base)</details> |  | `models/helpdesk_ticket.py:1500` |
| `fix_repair_action_direct_dispatch` | One-click Dispatch button: creates the return of the stored collection transfer back to the customer without showing the wizard; raises an error if no return transfer is stored on the ticket. |  |  | `helpdesk.ticket.company_id` (helpdesk)<br>`helpdesk.ticket.partner_id` (helpdesk)<br>`helpdesk.ticket.x_studio_pick_id`<br>`model stock.return.picking` (stock)<br>`res.company.id` (base)<details><summary>+1 more</summary>`res.partner.id` (base)</details> |  | `models/helpdesk_ticket.py:1595` |
| `_compute_so_fully_paid` | Compute for So Fully Paid: true when every repair-task sales order has non-cancelled invoices and all are posted and In Payment or Paid; gates the Dispatch button. | api.depends('fsm_task_ids.sale_order_id.invoice_ids.state', 'fsm_task_ids.sale_o… |  | `account.move.payment_state` (account)<br>`account.move.state` (account)<br>`helpdesk.ticket.fsm_task_ids` (helpdesk_fsm)<br>`project.task.sale_order_id` (sale_project)<br>`sale.order.invoice_ids` (sale) | `helpdesk.ticket.so_fully_paid` | `models/helpdesk_ticket.py:1647` |
| `_compute_is_tested_ok` | Compute for Is Tested Ok: true when any linked task is marked Tested OK (Quick Repair status) or has End Quick Repair ticked. | api.depends('fsm_task_ids.x_studio_quick_repair_status_1', 'fsm_task_ids.x_studi… |  | `helpdesk.ticket.fsm_task_ids` (helpdesk_fsm)<br>`project.task.x_studio_end_quick_repair` (BugFix-Project)<br>`project.task.x_studio_quick_repair_status_1` (BugFix-Project) | `helpdesk.ticket.is_tested_ok` | `models/helpdesk_ticket.py:1696` |
| `_compute_is_so_cancelled` | Compute for Is So Cancelled: true when at least one linked task's sales order is cancelled. | api.depends('fsm_task_ids.sale_order_id.state') |  | `helpdesk.ticket.fsm_task_ids` (helpdesk_fsm)<br>`project.task.sale_order_id` (sale_project)<br>`sale.order.state` (sale) | `helpdesk.ticket.is_so_cancelled` | `models/helpdesk_ticket.py:1710` |
| `_compute_repair_stage_state` | Compute for Repair Stage State: maps the current stage name (New, Sent to Factory, ..., Received at Sales Centre) to a fixed key, or 'other'. | api.depends('stage_id') |  | `helpdesk.ticket.stage_id` (helpdesk) | `helpdesk.ticket.repair_stage_state` | `models/helpdesk_ticket.py:1718` |
| `_compute_x_studio_handed_over` | Compute for Handed Over: true when more than one of the ticket's transfers is done. | api.depends('picking_ids') |  | `helpdesk.ticket.picking_ids` (helpdesk_stock)<br>`helpdesk.ticket.x_studio_handed_over` | `helpdesk.ticket.x_studio_handed_over` | `models/helpdesk_ticket.py:1735` |
| `_compute_task_done` | Compute for Task Done: true when the ticket has at least one field-service task marked done. |  |  | `model project.task` (project) | `helpdesk.ticket.task_done` | `models/helpdesk_ticket.py:1741` |
| `_compute_has_return_picking` | Compute for Has Return Picking: true when the ticket has any transfer, or for Without-Serial-No repairs when the serial was already received from a customer location. | api.depends('picking_ids', 'x_studio_serial_no') |  | `helpdesk.ticket.picking_ids` (helpdesk_stock)<br>`helpdesk.ticket.x_studio_serial_no`<br>`model stock.location` (stock)<br>`model stock.move.line` (stock) | `helpdesk.ticket.has_return_picking` | `models/helpdesk_ticket.py:1750` |
| `_onchange_serial_no_product` | Onchange of Serial Number: fills Product from the serial and Sales Order from the order that last delivered that serial; clears both when the serial is removed. | api.onchange('x_studio_serial_no') |  | `helpdesk.ticket._get_so_from_serial()`<br>`helpdesk.ticket.product_id` (helpdesk_stock)<br>`helpdesk.ticket.sale_order_id` (helpdesk_sale)<br>`helpdesk.ticket.x_studio_serial_no`<br>`stock.lot.product_id` (stock) |  | `models/helpdesk_ticket.py:1774` |
| `_get_so_from_serial` | Helper: returns the sales order that last delivered the given serial number to a customer (via the move's order line, else by origin name). |  |  | `model sale.order` (sale)<br>`model stock.location` (stock)<br>`model stock.move.line` (stock) | `helpdesk.ticket._onchange_serial_no_product()`<br>`helpdesk.ticket._post_write_serial_product_sync()` | `models/helpdesk_ticket.py:1782` |
| `_post_write_serial_product_sync` | Called after write when Serial Number changes: re-applies Product and Sales Order derived from the serial, overriding Studio automations that clear them (guarded against recursion). |  |  | `helpdesk.ticket._get_so_from_serial()`<br>`helpdesk.ticket.product_id` (helpdesk_stock)<br>`helpdesk.ticket.sale_order_id` (helpdesk_sale)<br>`helpdesk.ticket.x_studio_serial_no`<br>`product.product.id` (product)<details><summary>+1 more</summary>`stock.lot.product_id` (stock)</details> | `helpdesk.ticket.write()` | `models/helpdesk_ticket.py:1803` |
| `_deactivate_clearing_serial_automation` | Upgrade helper: archives every helpdesk ticket automation that triggers on Serial Number changes (the Studio automation that wrongly cleared product, lot and order). | api.model |  | `model base.automation` (base_automation)<br>`model ir.model.fields` (base) |  | `models/helpdesk_ticket.py:1825` |
| `_get_view` | Ticket form-view override: injects hidden helper fields, adds/relabels repair workflow header buttons (Create Serial No, Change to RUG, Send/Receive at Factory and Sales Centre, Return, Dispatch) with visibility rules, and makes fields read-only once the ticket is locked. | api.model | yes |  |  | `models/helpdesk_ticket.py:1858` |
| `action_change_to_rug` | Button handler: changes the ticket type to the type named like 'Under Warranty - RUG', if found. |  |  | `model helpdesk.ticket.type` (helpdesk) |  | `models/helpdesk_ticket.py:2802` |
| `action_create_repair_serial` | Create Serial No button: creates a new serial/lot named after the ticket for its product, links it as the ticket's serial and lot, and marks Repair Serial Created; errors if no product. Each click creates a new lot. |  |  | `helpdesk.ticket.company_id` (helpdesk)<br>`helpdesk.ticket.name` (helpdesk)<br>`helpdesk.ticket.product_id` (helpdesk_stock)<br>`helpdesk.ticket.write()`<br>`model stock.lot` (stock)<details><summary>+2 more</summary>`product.product.id` (product)<br>`res.company.id` (base)</details> |  | `models/helpdesk_ticket.py:2812` |
| `_get_or_create_stage` | Helper: finds the helpdesk stage with the given name for the ticket's team and company (or no company); creates it if missing. |  |  | `helpdesk.ticket.company_id` (helpdesk)<br>`helpdesk.ticket.team_id` (helpdesk)<br>`model helpdesk.stage` (helpdesk)<br>`res.company.id` (base) | `helpdesk.ticket.action_received_at_factory()`<br>`helpdesk.ticket.action_received_at_sales_centre()`<br>`helpdesk.ticket.action_send_to_factory()`<br>`helpdesk.ticket.action_send_to_sales_centre()` | `models/helpdesk_ticket.py:2832` |
| `_move_to_stage` | Helper: moves tickets to the named stage of their team/company; never moves a ticket back to Repair Completed once it has been there. |  |  | `helpdesk.ticket._has_been_at_stage()`<br>`model helpdesk.stage` (helpdesk) |  | `models/helpdesk_ticket.py:2846` |
| `_has_been_at_stage` | Helper: checks the ticket's stage-change tracking history to tell whether it was ever in the given stage. |  |  | `model mail.tracking.value` (mail) | `helpdesk.ticket._move_to_stage()`<br>`helpdesk.ticket.write()` | `models/helpdesk_ticket.py:2871` |
| `write` | Override of write: blocks moving a ticket back to Repair Completed if it was already there (other values still saved), and after saving re-syncs Product and Sales Order from the Serial Number. |  | yes | `helpdesk.ticket._has_been_at_stage()`<br>`helpdesk.ticket._post_write_serial_product_sync()`<br>`model helpdesk.stage` (helpdesk) | `helpdesk.ticket.action_assign_to_me()`<br>`helpdesk.ticket.action_create_repair_serial()`<br>`helpdesk.ticket.action_received_at_factory()`<br>`helpdesk.ticket.action_send_to_factory()`<br>`helpdesk.ticket.action_send_to_sales_centre()` | `models/helpdesk_ticket.py:2884` |
| `action_assign_to_me` | Assign to Me button: sets the current user as the ticket's assignee. |  |  | `helpdesk.ticket.write()` | `view Fix-repair.helpdesk_ticket_form_assign_to_me` | `models/helpdesk_ticket.py:2924` |
| `action_send_to_factory` | Send to Factory button: creates the movement transfer to the repair warehouse's in-transit location, moves the ticket to 'Sent to Factory' and records shipped date/user (sales centre). |  |  | `helpdesk.ticket._create_send_to_factory_picking()`<br>`helpdesk.ticket._get_or_create_stage()`<br>`helpdesk.ticket.write()` | `view Fix-repair.helpdesk_ticket_form_assign_to_me` | `models/helpdesk_ticket.py:2927` |
| `action_received_at_factory` | Received at Factory button: creates the movement into the factory warehouse, moves the ticket to 'Received at Factory' and records received date/user (factory). |  |  | `helpdesk.ticket._create_received_at_factory_picking()`<br>`helpdesk.ticket._get_or_create_stage()`<br>`helpdesk.ticket.write()` | `view Fix-repair.helpdesk_ticket_form_assign_to_me` | `models/helpdesk_ticket.py:2937` |
| `action_generate_fsm_task` | Override of Plan Intervention: after creating the field-service task, moves the item to the Repair location of the centre or factory warehouse depending on Job Location. |  | yes | `helpdesk.ticket._create_plan_intervention_picking()` |  | `models/helpdesk_ticket.py:2949` |
| `_create_mark_as_done_picking` | Helper run when repair is done: moves the item from its current location to the centre's virtual repair location (Centre Repair) or the factory warehouse's in-transit location (Factory Repair). |  |  | `helpdesk.ticket._create_repair_transfer()`<br>`helpdesk.ticket._current_item_location()`<br>`helpdesk.ticket._get_factory_repair_location()`<br>`helpdesk.ticket.x_studio_job_location`<br>`helpdesk.ticket.x_studio_virtual_location_1`<details><summary>+1 more</summary>`helpdesk.ticket.x_studio_virtual_location`</details> |  | `models/helpdesk_ticket.py:2960` |
| `_create_plan_intervention_picking` | Helper: moves the item from its current location to the Repair location of the centre warehouse (Centre Repair) or factory warehouse (Factory Repair); does nothing if not applicable. |  |  | `helpdesk.ticket._create_repair_transfer()`<br>`helpdesk.ticket._current_item_location()`<br>`helpdesk.ticket._get_factory_repair_location()`<br>`helpdesk.ticket.x_studio_job_location`<br>`helpdesk.ticket.x_studio_return_receipt_location` | `helpdesk.ticket.action_generate_fsm_task()` (Fix-Repair-Wizard-Nav, Fix-repair) | `models/helpdesk_ticket.py:2987` |
| `_current_item_location` | Helper: returns where the item currently is, i.e. the destination of the ticket's latest transfer, or the Repair Location if no transfer exists. |  |  | `helpdesk.ticket.x_studio_repair_location`<br>`model stock.picking` (stock) | `helpdesk.ticket._create_mark_as_done_picking()`<br>`helpdesk.ticket._create_plan_intervention_picking()`<br>`helpdesk.ticket._create_received_at_factory_picking()`<br>`helpdesk.ticket._create_received_at_sales_centre_picking()`<br>`helpdesk.ticket._create_send_to_factory_picking()`<details><summary>+1 more</summary>`helpdesk.ticket._create_send_to_sales_centre_picking()`</details> | `models/helpdesk_ticket.py:3010` |
| `_create_send_to_factory_picking` | Helper: creates the movement from the item's current location to the in-transit location of the Repair Location's warehouse. |  |  | `helpdesk.ticket._create_repair_transfer()`<br>`helpdesk.ticket._current_item_location()`<br>`helpdesk.ticket.x_studio_repair_location` | `helpdesk.ticket.action_send_to_factory()` | `models/helpdesk_ticket.py:3023` |
| `_create_send_to_sales_centre_picking` | Helper: creates the movement from the factory to the receiving centre's in-transit location (or its stock location when both are the same warehouse). |  |  | `helpdesk.ticket._create_repair_transfer()`<br>`helpdesk.ticket._current_item_location()`<br>`helpdesk.ticket.x_studio_return_receipt_location` | `helpdesk.ticket.action_send_to_sales_centre()` | `models/helpdesk_ticket.py:3033` |
| `_create_received_at_sales_centre_picking` | Helper: creates the movement from the item's current location to the centre's virtual repair location. |  |  | `helpdesk.ticket._create_repair_transfer()`<br>`helpdesk.ticket._current_item_location()`<br>`helpdesk.ticket.x_studio_virtual_location_1`<br>`helpdesk.ticket.x_studio_virtual_location` | `helpdesk.ticket.action_received_at_sales_centre()` | `models/helpdesk_ticket.py:3058` |
| `_create_received_at_factory_picking` | Helper: creates the movement into the factory warehouse's in-transit (or stock) location; raises an error if the Factory Repair Location setting is not configured. |  |  | `helpdesk.ticket._create_repair_transfer()`<br>`helpdesk.ticket._current_item_location()`<br>`helpdesk.ticket._get_factory_repair_location()`<br>`helpdesk.ticket.company_id` (helpdesk)<br>`res.company.name` (base) | `helpdesk.ticket.action_received_at_factory()` | `models/helpdesk_ticket.py:3070` |
| `_get_factory_repair_location` | Helper: reads the company's Factory Repair Location from system parameters and returns that stock location (empty if unset or invalid). |  |  | `helpdesk.ticket.company_id` (helpdesk)<br>`model ir.config_parameter` (base)<br>`model stock.location` (stock)<br>`res.company.id` (base) | `helpdesk.ticket._create_mark_as_done_picking()`<br>`helpdesk.ticket._create_plan_intervention_picking()`<br>`helpdesk.ticket._create_received_at_factory_picking()` | `models/helpdesk_ticket.py:3101` |
| `_create_repair_transfer` | Helper: creates a one-unit internal transfer of the ticket's product/serial between two locations, linked to the ticket, and marks it done directly by writing the state (not via standard validation), so stock quantities may not be updated. |  |  | `helpdesk.ticket.company_id` (helpdesk)<br>`helpdesk.ticket.partner_id` (helpdesk)<br>`helpdesk.ticket.product_id` (helpdesk_stock)<br>`helpdesk.ticket.x_studio_serial_no`<br>`model stock.move.line` (stock)<details><summary>+3 more</summary>`model stock.picking.type` (stock)<br>`res.company.id` (base)<br>`res.partner.id` (base)</details> | `helpdesk.ticket._create_mark_as_done_picking()`<br>`helpdesk.ticket._create_plan_intervention_picking()`<br>`helpdesk.ticket._create_received_at_factory_picking()`<br>`helpdesk.ticket._create_received_at_sales_centre_picking()`<br>`helpdesk.ticket._create_send_to_factory_picking()`<details><summary>+1 more</summary>`helpdesk.ticket._create_send_to_sales_centre_picking()`</details> | `models/helpdesk_ticket.py:3118` |
| `action_send_to_sales_centre` | Send to Sales Centre button: creates the movement back to the centre, moves the ticket to 'Sent to Sales Centre' and records factory shipped date/user. |  |  | `helpdesk.ticket._create_send_to_sales_centre_picking()`<br>`helpdesk.ticket._get_or_create_stage()`<br>`helpdesk.ticket.write()` | `view Fix-repair.helpdesk_ticket_form_assign_to_me` | `models/helpdesk_ticket.py:3229` |
| `action_received_at_sales_centre` | Received at Sales Centre button: creates the movement into the centre's virtual repair location, moves the ticket to 'Received at Sales Centre', records received date/user and stores the latest collection transfer id for the later return to customer. |  |  | `helpdesk.ticket._create_received_at_sales_centre_picking()`<br>`helpdesk.ticket._get_or_create_stage()`<br>`model stock.picking` (stock) | `view Fix-repair.helpdesk_ticket_form_assign_to_me` | `models/helpdesk_ticket.py:3239` |
| `_repair_seq_no_on_create_or_write` | Replaces the Studio 'Repair Seq.No' automation: gives tickets with an empty or 'New' subject the next number from the repair.seq sequence. |  |  | `helpdesk.ticket.name` (helpdesk)<br>`model ir.sequence` (base) | `helpdesk.ticket.create()` | `models/helpdesk_ticket.py:3287` |
| `_repair_populate_repair_location` | Replaces the Studio 'Auto Populate Repair Location' automation: copies Return Receipt Location into Repair Location (clears it when empty). |  |  | `helpdesk.ticket.x_studio_repair_location`<br>`helpdesk.ticket.x_studio_return_receipt_location` | `helpdesk.ticket._onchange_repair_populate_repair_location()` | `models/helpdesk_ticket.py:3307` |
| `_repair_validate_cancelled_on_unlink` | Replaces the Studio 'Validate Cancelled Tickets' automation: blocks deleting tickets marked Cancelled with an error. |  |  | `helpdesk.ticket.x_studio_cancelled` | `helpdesk.ticket.unlink()` | `models/helpdesk_ticket.py:3318` |
| `_repair_auto_select_product_for_rug` | Replaces Studio 'Auto Select Product for RUG Repairs': from the serial number, finds the customer delivery in the current company and fills Sales Order, picking refs, Product and Lot; clears them when the serial is empty. |  |  | `helpdesk.ticket.lot_id` (helpdesk_stock)<br>`helpdesk.ticket.product_id` (helpdesk_stock)<br>`helpdesk.ticket.sale_order_id` (helpdesk_sale)<br>`helpdesk.ticket.x_studio_normal_repair_without_serial_no`<br>`helpdesk.ticket.x_studio_pick_id`<details><summary>+9 more</summary>`helpdesk.ticket.x_studio_picking_id`<br>`helpdesk.ticket.x_studio_serial_no`<br>`model res.company` (base)<br>`model sale.order` (sale)<br>`model stock.location` (stock)<br>`model stock.move.line` (stock)<br>`product.product.id` (product)<br>`stock.lot.id` (stock)<br>`stock.lot.product_id` (stock)</details> | `helpdesk.ticket._onchange_repair_auto_select_product_for_rug()` | `models/helpdesk_ticket.py:3327` |
| `_repair_studio_send_to_factory` | Port of the Studio Send to Factory action: sets Repair Location to the location flagged as Repair Factory, ticks Send to Factory, stamps shipped and Created By/On 1, and moves to stage 5/24 (hard-coded ids). Errors if no factory location. |  |  | `model res.company` (base)<br>`model stock.location` (stock) |  | `models/helpdesk_ticket.py:3399` |
| `_repair_studio_receive_at_factory` | Port of the Studio Receive at Factory action: ticks Receive at Factory, stamps factory received date/user and Created By/On 2, and moves to stage 6/25 (hard-coded ids). |  |  | `model res.company` (base) |  | `models/helpdesk_ticket.py:3427` |
| `_repair_studio_send_to_sales_centre` | Port of the Studio Send to Sales Centre action: ticks Send to Centre, stamps factory shipped date/user and Created By/On 9, and moves to stage 7/26 (hard-coded ids). |  |  | `model res.company` (base) |  | `models/helpdesk_ticket.py:3447` |
| `_repair_studio_receive_at_sales_centre` | Port of the Studio Receive at Sales Centre action: ticks Receive at Centre, stamps centre received date/user and Created By/On 10, and moves to stage 8/27 (hard-coded ids). |  |  | `model res.company` (base) |  | `models/helpdesk_ticket.py:3467` |
| `_repair_studio_cancel_repair` | Port of the Studio Cancel Repair action: requires a Cancel Reason, remembers the current stage, moves to the cancelled stage (4/23), and sets Cancelled, Cancelled By/Date and Cancel Status. |  |  | `helpdesk.stage.id` (helpdesk)<br>`helpdesk.ticket.stage_id` (helpdesk)<br>`helpdesk.ticket.x_studio_cancel_reason`<br>`model res.company` (base) |  | `models/helpdesk_ticket.py:3487` |
| `_repair_studio_reopen_repair` | Port of the Studio Reopen Repair action: returns the ticket to the stage it had before cancellation, clears Cancelled and sets Reopened, Reopened By/Date and Reopen Status. |  |  | `helpdesk.stage.id` (helpdesk)<br>`helpdesk.ticket.x_studio_cancelled_stage_id` |  | `models/helpdesk_ticket.py:3508` |
| `_repair_studio_auto_create_repair_route` | Port of the Studio repair-route action: checks the user's source and virtual locations, then creates a done one-unit delivery from the source location to the customer for the ticket's product and stores it as the ticket's picking; errors if the return location has no outgoing operation type. |  |  | `helpdesk.ticket.partner_id` (helpdesk)<br>`helpdesk.ticket.product_id` (helpdesk_stock)<br>`helpdesk.ticket.x_studio_pick_id`<br>`helpdesk.ticket.x_studio_picking_id`<br>`helpdesk.ticket.x_studio_repair_serial_created`<details><summary>+17 more</summary>`helpdesk.ticket.x_studio_return_receipt_location`<br>`helpdesk.ticket.x_studio_source_location_1`<br>`helpdesk.ticket.x_studio_source_location`<br>`helpdesk.ticket.x_studio_virtual_location_1`<br>`helpdesk.ticket.x_studio_virtual_location`<br>`model res.company` (base)<br>`model stock.location` (stock)<br>`model stock.move.line` (stock)<br>`model stock.move` (stock)<br>`model stock.picking.type` (stock)<br>`model stock.picking` (stock)<br>`product.product.id` (product)<br>`product.product.name` (product)<br>`product.product.uom_id` (product)<br>`res.partner.id` (base)<br>`stock.location.id` (stock)<br>`uom.uom.id` (uom)</details> |  | `models/helpdesk_ticket.py:3538` |
| `_repair_send_stage13_email` | Helper: when the ticket is in stage 13 (hard-coded id), emails the customer using the given mail template id and logs a note; otherwise errors that the item must be handed over first. |  |  | `helpdesk.stage.id` (helpdesk)<br>`helpdesk.ticket.partner_id` (helpdesk)<br>`helpdesk.ticket.stage_id` (helpdesk)<br>`model mail.template` (mail)<br>`res.partner.id` (base)<details><summary>+1 more</summary>`res.partner.name` (base)</details> | `helpdesk.ticket._repair_send_customer_letter()`<br>`helpdesk.ticket._repair_send_final_notice()`<br>`helpdesk.ticket._repair_send_final_notice_estimated()`<br>`helpdesk.ticket._repair_send_final_notice_scrappage()`<br>`helpdesk.ticket._repair_send_reminding_letter()` | `models/helpdesk_ticket.py:3651` |
| `_repair_send_customer_letter` | Sends the repair customer letter (mail template 56) via the stage-13 email helper. |  |  | `helpdesk.ticket._repair_send_stage13_email()` |  | `models/helpdesk_ticket.py:3670` |
| `_repair_send_final_notice` | Sends the final notice letter (mail template 66) via the stage-13 email helper. |  |  | `helpdesk.ticket._repair_send_stage13_email()` |  | `models/helpdesk_ticket.py:3674` |
| `_repair_send_final_notice_estimated` | Sends the estimated final notice letter (mail template 67) via the stage-13 email helper. |  |  | `helpdesk.ticket._repair_send_stage13_email()` |  | `models/helpdesk_ticket.py:3678` |
| `_repair_send_final_notice_scrappage` | Sends the scrappage final notice letter (mail template 69) via the stage-13 email helper. |  |  | `helpdesk.ticket._repair_send_stage13_email()` |  | `models/helpdesk_ticket.py:3682` |
| `_repair_send_reminding_letter` | Sends the reminding letter (mail template 70) via the stage-13 email helper. |  |  | `helpdesk.ticket._repair_send_stage13_email()` |  | `models/helpdesk_ticket.py:3686` |
| `_repair_auto_select_product_for_rug_no_company` | Shared helper for RUG product auto-select without the company filter on the delivery search: fills Sales Order, picking refs, Product and Lot from the serial (or clears them), optionally setting SN Updated. |  |  | `helpdesk.ticket.lot_id` (helpdesk_stock)<br>`helpdesk.ticket.product_id` (helpdesk_stock)<br>`helpdesk.ticket.sale_order_id` (helpdesk_sale)<br>`helpdesk.ticket.x_studio_normal_repair_without_serial_no`<br>`helpdesk.ticket.x_studio_pick_id`<details><summary>+10 more</summary>`helpdesk.ticket.x_studio_picking_id`<br>`helpdesk.ticket.x_studio_serial_no`<br>`helpdesk.ticket.x_studio_sn_updated`<br>`model res.company` (base)<br>`model sale.order` (sale)<br>`model stock.location` (stock)<br>`model stock.move.line` (stock)<br>`product.product.id` (product)<br>`stock.lot.id` (stock)<br>`stock.lot.product_id` (stock)</details> | `helpdesk.ticket._repair_auto_select_product_for_rug_2()`<br>`helpdesk.ticket._repair_auto_select_product_for_rug_22()` | `models/helpdesk_ticket.py:3697` |
| `_repair_auto_select_product_for_rug_2` | Port of Studio action 1990: runs the RUG product auto-select without company filter and without setting SN Updated. |  |  | `helpdesk.ticket._repair_auto_select_product_for_rug_no_company()` |  | `models/helpdesk_ticket.py:3750` |
| `_repair_auto_select_product_for_rug_22` | Port of Studio action 2450: runs the RUG product auto-select without company filter and sets SN Updated. |  |  | `helpdesk.ticket._repair_auto_select_product_for_rug_no_company()` |  | `models/helpdesk_ticket.py:3754` |
| `_repair_auto_select_product_for_rug_33` | Port of Studio action 2451: unconditionally clears the ticket's Sales Order, picking refs, Product, Lot and SN Updated. |  |  |  |  | `models/helpdesk_ticket.py:3758` |
| `_repair_auto_select_product_for_rug_4` | Port of Studio action 1992: when a ticket type is set, clears Sales Order, picking refs, Product, Lot and Serial Number. |  |  | `helpdesk.ticket.ticket_type_id` (helpdesk) |  | `models/helpdesk_ticket.py:3772` |
| `_repair_studio_cancel_repair_2` | Port of Studio 'Cancel Repair 2': requires a Cancel Reason, then closes the ticket as Repair Completed (stage 9/28), stamps Created By/On 8 and sets Cancelled-2 and Cancel Status 'Cancelled'. |  |  | `helpdesk.ticket.x_studio_cancel_reason`<br>`model res.company` (base) |  | `models/helpdesk_ticket.py:3787` |
| `_repair_studio_change_repair_type_to_rug` | Port of Studio 'Change Repair Type to RUG': requires the Warranty Card, resets linked order line prices to product cost (saving the original price) and sets the ticket type to id 1 (hard-coded RUG type). |  |  | `helpdesk.ticket.fsm_task_ids` (helpdesk_fsm)<br>`helpdesk.ticket.x_studio_warranty_card`<br>`model sale.order` (sale) |  | `models/helpdesk_ticket.py:3812` |
| `_repair_studio_user_location_validation` | Checks that the current user may work with the ticket's Return Receipt Location: when User Location Validation is set, raises an error showing the location and the stock locations the user is permitted for (or that none are set up). Admin (uid 1) is exempt. |  |  | `helpdesk.ticket.x_studio_return_receipt_location`<br>`helpdesk.ticket.x_studio_user_location_validation`<br>`model stock.location` (stock)<br>`stock.location.complete_name` (stock) |  | `models/helpdesk_ticket.py:3834` |
| `_repair_studio_update_rug_approval_in_pipeline` | No-op placeholder for the old Studio action 'Update RUG Approval in Pipeline' (an object-write action with no code); it does nothing. |  |  |  |  | `models/helpdesk_ticket.py:3866` |
| `create` | Override of ticket creation: after creating the tickets, assigns the repair sequence number (replaces the old Studio 'JIN-Helpdesk(Repair) Seq.No' automation). | api.model_create_multi | yes | `helpdesk.ticket._repair_seq_no_on_create_or_write()` |  | `models/helpdesk_ticket.py:3893` |
| `unlink` | Override of ticket deletion: first runs the cancelled-ticket check (blocks deleting cancelled tickets), then deletes (replaces Studio automation 'RR - Validate Cancelled Tickets'). |  | yes | `helpdesk.ticket._repair_validate_cancelled_on_unlink()` |  | `models/helpdesk_ticket.py:3906` |
| `_onchange_repair_auto_select_product_for_rug` | Onchange on Ticket Type and the Serial Number field: automatically selects the product for RUG repairs (replaces Studio automation 'RR - Auto Select Product for RUG Repairs'). | api.onchange('ticket_type_id', 'x_studio_serial_number') |  | `helpdesk.ticket._repair_auto_select_product_for_rug()`<br>`helpdesk.ticket.ticket_type_id` (helpdesk)<br>`helpdesk.ticket.x_studio_serial_number` |  | `models/helpdesk_ticket.py:3918` |
| `_onchange_repair_populate_repair_location` | Onchange on Return Receipt Location: fills the ticket's Repair Location from it (replaces Studio automation 'RR - Auto Populate Repair Location'). | api.onchange('x_studio_return_receipt_location') |  | `helpdesk.ticket._repair_populate_repair_location()`<br>`helpdesk.ticket.x_studio_return_receipt_location` |  | `models/helpdesk_ticket.py:3931` |
| `_deactivate_migrated_ticket_automations` | Migration helper: archives the four old Studio automations (ids 171, 172, 178, 201) whose logic now lives in ticket create/unlink/onchange code. Records are kept, only set inactive. | api.model |  | `model base.automation` (base_automation) |  | `models/helpdesk_ticket.py:3939` |
| `_deactivate_migrated_other_automations` | Migration helper: archives eight old Studio automations (company-id setters on stages, repair reasons, sub reasons, accounts, plus task pipeline update and Super User Validate) now replaced by Python create/write hooks. | api.model |  | `model base.automation` (base_automation) |  | `models/helpdesk_ticket.py:3964` |
| `_migrate_studio_leftover_repair_fields` | One-off migration helper: switches 11 leftover Studio fields on res.users and project.task from 'manual' to code-owned ('base') via SQL, now that Python declarations exist. Data is untouched; already-migrated rows are skipped. | api.model |  | `model ir.model.data` (base)<br>`model ir.model.fields` (base) |  | `models/helpdesk_ticket.py:3990` |
| `_repin_delegated_server_actions_to_native` | One-off migration helper: moves the ownership (external id) of 9 delegated server actions from studio_customization to Fix-repair with an `action_<id>` name, so Studio no longer treats them as its own. Idempotent. | api.model |  | `model ir.model.data` (base) |  | `models/helpdesk_ticket.py:4063` |
| `_sanitize_broken_studio_task_form_xpath` | One-off migration hotfix: rewrites the stored arch of the Studio task form customization (view 3019) via SQL with robust name-based xpaths, keeping the repair buttons, fields and notebook pages and dropping two button changes already handled in code. | api.model |  | `model ir.ui.view` (base) |  | `models/helpdesk_ticket.py:4118` |
| `_fix_studio_report_template_keys` | One-off migration hotfix: for repair reports owned by Fix-repair, renames their QWeb template keys (and internal t-call references) from the studio_customization prefix to Fix-repair so the reports render again, and ensures an external id exists. | api.model |  | `model ir.actions.report` (base)<br>`model ir.model.data` (base)<br>`model ir.ui.view` (base) |  | `models/helpdesk_ticket.py:4271` |
| `_migrate_studio_reports_to_native` | One-off migration helper: transfers Studio-made reports on repair-related models and their QWeb templates to Fix-repair ownership (renames report_name and moves external ids); report content is unchanged. Idempotent. | api.model |  | `model ir.actions.report` (base)<br>`model ir.model.data` (base) |  | `models/helpdesk_ticket.py:4380` |
| `_migrate_studio_views_to_native` | One-off migration helper: transfers Studio-made views on repair-related models (ticket, task, stages, users, settings, repair master data) to Fix-repair ownership with stable external ids; view content is unchanged. Idempotent. | api.model |  | `model ir.model.data` (base)<br>`model ir.ui.view` (base) |  | `models/helpdesk_ticket.py:4491` |
| `_repair_studio_auto_create_repair_serial_nos` | Creates a repair serial number: checks the user's virtual/source locations are set (per company), creates a new lot from the 'repair.serial.seq' sequence, puts it on the ticket as Serial No / Lot and marks Repair Serial Created, then creates the related stock move into a customer location. |  |  | `helpdesk.ticket.lot_id` (helpdesk_stock)<br>`helpdesk.ticket.partner_id` (helpdesk)<br>`helpdesk.ticket.product_id` (helpdesk_stock)<br>`helpdesk.ticket.x_studio_pick_id`<br>`helpdesk.ticket.x_studio_picking_id`<details><summary>+22 more</summary>`helpdesk.ticket.x_studio_repair_serial_created`<br>`helpdesk.ticket.x_studio_return_receipt_location`<br>`helpdesk.ticket.x_studio_serial_no`<br>`helpdesk.ticket.x_studio_source_location_1`<br>`helpdesk.ticket.x_studio_source_location`<br>`helpdesk.ticket.x_studio_virtual_location_1`<br>`helpdesk.ticket.x_studio_virtual_location`<br>`model ir.sequence` (base)<br>`model res.company` (base)<br>`model stock.location` (stock)<br>`model stock.lot` (stock)<br>`model stock.move.line` (stock)<br>`model stock.move` (stock)<br>`model stock.picking.type` (stock)<br>`model stock.picking` (stock)<br>`product.product.id` (product)<br>`product.product.name` (product)<br>`product.product.uom_id` (product)<br>`res.partner.id` (base)<br>`stock.location.id` (stock)<br>`stock.lot.id` (stock)<br>`uom.uom.id` (uom)</details> |  | `models/helpdesk_ticket.py:4562` |
| `_delegate_studio_server_actions_to_native` | Migration helper: rewrites the code of the old Studio server actions (sequence, location, cancel checks, factory/sales-centre send/receive, cancel/reopen, route/serial creation, email actions) into one-line calls to the native Python methods. Only touches unmarked actions; safe on every upgrade. | api.model |  | `model ir.actions.server` (base)<br>`model sale.order` (sale) |  | `models/helpdesk_ticket.py:4682` |

**Server actions (27):**

- **Execute Code** (`server_action_1976_rr_repair_seq_no`, type `code`)
  - Function: Gives the ticket a number from the 'repair.seq' sequence when its name is empty or 'New'. Used by the automation 'JIN-Helpdesk(Repair) Seq.No' (which is archived after migration).
  - Depends on: `model helpdesk.ticket` (helpdesk)
  - Used by: `automation Fix-repair.base_automation_171_jin_helpdesk_repair_seq_no`
  <details><summary>code (3 lines)</summary>

```python

# fix_repair:idempotent-v1
record._repair_seq_no_on_create_or_write()
```
  </details>
- **Execute Code** (`server_action_1989_rr_auto_select_product_for_rug_repairs`, type `code`)
  - Function: Fills the ticket's sale order, picking, product and lot from the customer delivery of its serial number. Used by the automation of the same name.
  - Depends on: `model helpdesk.ticket` (helpdesk)
  - Used by: `automation Fix-repair.base_automation_172_rr_auto_select_product_for_rug_repairs`
  <details><summary>code (3 lines)</summary>

```python

# fix_repair:idempotent-v1
record._repair_auto_select_product_for_rug()
```
  </details>
- **Execute Code** (`server_action_1990_rr_auto_select_product_for_rug_repairs_2`, type `code`)
  - Function: Fills sale order, picking, product and lot from the serial's customer delivery, without the company filter. Used by the automation 'RR - Auto Select Product for RUG Repairs-2'.
  - Depends on: `model helpdesk.ticket` (helpdesk)
  - Used by: `automation Fix-repair.base_automation_173_rr_auto_select_product_for_rug_repairs_2`
  <details><summary>code (3 lines)</summary>

```python

# fix_repair:idempotent-v1
record._repair_auto_select_product_for_rug_2()
```
  </details>
- **Execute Code** (`server_action_1992_rr_auto_select_product_for_rug_repairs_4`, type `code`)
  - Function: When a ticket type is set, clears the ticket's sale order, pickings, product, lot and serial number. Used by automation 'RR - Auto Select Product for RUG Repairs-4'.
  - Depends on: `model helpdesk.ticket` (helpdesk)
  - Used by: `automation Fix-repair.base_automation_175_rr_auto_select_product_for_rug_repairs_4`
  <details><summary>code (3 lines)</summary>

```python

# fix_repair:idempotent-v1
record._repair_auto_select_product_for_rug_4()
```
  </details>
- **Execute Code** (`server_action_2000_rr_auto_populate_repair_location`, type `code`)
  - Function: Copies the ticket's Return Receipt Location into its Repair Location. Used by the automation 'RR - Auto Populate Repair Location'.
  - Depends on: `model helpdesk.ticket` (helpdesk)
  - Used by: `automation Fix-repair.base_automation_178_rr_auto_populate_repair_location`
  <details><summary>code (3 lines)</summary>

```python

# fix_repair:idempotent-v1
record._repair_populate_repair_location()
```
  </details>
- **Execute Code** (`server_action_2222_rr_validate_cancelled_tickets`, type `code`)
  - Function: Blocks deletion of cancelled tickets. Used by the automation 'RR - Validate Cancelled Tickets' (archived after migration).
  - Depends on: `model helpdesk.ticket` (helpdesk)
  - Used by: `automation Fix-repair.base_automation_201_rr_validate_cancelled_tickets`
  <details><summary>code (3 lines)</summary>

```python

# fix_repair:idempotent-v1
record._repair_validate_cancelled_on_unlink()
```
  </details>
- **Execute Code** (`server_action_2451_rr_auto_select_product_for_rug_repairs_33`, type `code`)
  - Function: Clears the ticket's sale order, pickings, product, lot and SN Updated flag. Used by automation 'RR - Auto Select Product for RUG Repairs-33'.
  - Depends on: `model helpdesk.ticket` (helpdesk)
  - Used by: `automation Fix-repair.base_automation_243_rr_auto_select_product_for_rug_repairs_33`
  <details><summary>code (3 lines)</summary>

```python

# fix_repair:idempotent-v1
record._repair_auto_select_product_for_rug_33()
```
  </details>
- **Execute Code** (`server_action_2558_user_location_validation_helpdesk`, type `code`)
  - Function: Checks the user may work with the ticket's Return Receipt Location; raises an error listing the user's permitted locations otherwise. Used by automation 'User Location Validation - Helpdesk'.
  - Depends on: `model helpdesk.ticket` (helpdesk)
  - Used by: `automation Fix-repair.base_automation_252_user_location_validation_helpdesk`
  <details><summary>code (3 lines)</summary>

```python

# fix_repair:idempotent-v1
record._repair_studio_user_location_validation()
```
  </details>
- **RR - Auto Create Repair Route** (`action_repair_auto_create_route`, type `code`)
  - Function: Creates the repair route for the ticket: checks the user's virtual/source locations (per company) and creates a done stock picking with its move and move line.
  - Depends on: `model helpdesk.ticket` (helpdesk)
  - Used by: — (not linked to a button, menu or automation)
  <details><summary>code (5 lines)</summary>

```python

# Fix-repair v253: delegates to native Python method already ported
# from Clear-DB Studio server action 1993.
if record:
    record._repair_studio_auto_create_repair_route()
```
  </details>
- **RR - Auto Create Repair Serial Nos** (`server_action_1994_rr_auto_create_repair_serial_nos`, type `code`)
  - Function: Creates a new repair serial number (lot) for the ticket, sets it as Serial No / Lot, marks Repair Serial Created, and creates the related stock movement.
  - Depends on: `model helpdesk.ticket` (helpdesk)
  - Used by: — (not linked to a button, menu or automation)
  <details><summary>code (3 lines)</summary>

```python

# fix_repair:idempotent-v1
record._repair_studio_auto_create_repair_serial_nos()
```
  </details>
- **RR - Auto Populate Repair Location** (`sa_f5_helpdesk_ticket_rr_auto_populate_repair_location`, type `code`)
  - Function: Copies the ticket's Return Receipt Location into its Repair Location (clears it when empty). Duplicate of the automation-linked action of the same name.
  - Depends on: `model helpdesk.ticket` (helpdesk)
  - Used by: — (not linked to a button, menu or automation)
  <details><summary>code (2 lines)</summary>

```python
# fix_repair:idempotent-v1
record._repair_populate_repair_location()
```
  </details>
- **RR - Auto Select Product for RUG Repairs** (`sa_f5_helpdesk_ticket_rr_auto_select_product_for_rug_repairs`, type `code`)
  - Function: When the ticket has a serial number, finds the delivery that shipped that serial to a customer and fills the ticket's sale order, picking, product and lot from it.
  - Depends on: `model helpdesk.ticket` (helpdesk)
  - Used by: — (not linked to a button, menu or automation)
  <details><summary>code (2 lines)</summary>

```python
# fix_repair:idempotent-v1
record._repair_auto_select_product_for_rug()
```
  </details>
- **RR - Auto Select Product for RUG Repairs-2** (`sa_f5_helpdesk_ticket_rr_auto_select_product_for_rug_repairs_2`, type `code`)
  - Function: Same as 'Auto Select Product for RUG Repairs' but without the company filter on the delivery search: fills sale order, picking, product and lot from the serial's customer delivery.
  - Depends on: `model helpdesk.ticket` (helpdesk)
  - Used by: — (not linked to a button, menu or automation)
  <details><summary>code (2 lines)</summary>

```python
# fix_repair:idempotent-v1
record._repair_auto_select_product_for_rug_2()
```
  </details>
- **RR - Auto Select Product for RUG Repairs-33** (`sa_f5_helpdesk_ticket_rr_auto_select_product_for_rug_repairs_33`, type `code`)
  - Function: Clears the ticket's sale order, pickings, product, lot and SN Updated flag.
  - Depends on: `model helpdesk.ticket` (helpdesk)
  - Used by: — (not linked to a button, menu or automation)
  <details><summary>code (2 lines)</summary>

```python
# fix_repair:idempotent-v1
record._repair_auto_select_product_for_rug_33()
```
  </details>
- **RR - Auto Select Product for RUG Repairs-4** (`sa_f5_helpdesk_ticket_rr_auto_select_product_for_rug_repairs_4`, type `code`)
  - Function: When a ticket type is set, clears the ticket's sale order, pickings, product, lot and serial number.
  - Depends on: `model helpdesk.ticket` (helpdesk)
  - Used by: — (not linked to a button, menu or automation)
  <details><summary>code (2 lines)</summary>

```python
# fix_repair:idempotent-v1
record._repair_auto_select_product_for_rug_4()
```
  </details>
- **RR - Cancel Repair** (`server_action_2220_rr_cancel_repair`, type `code`)
  - Function: Cancel Repair: requires a cancel reason, remembers the current stage, moves the ticket to the Cancelled stage (per company), and records cancelled flag, user, date and status.
  - Depends on: `model helpdesk.ticket` (helpdesk)
  - Used by: — (not linked to a button, menu or automation)
  <details><summary>code (3 lines)</summary>

```python

# fix_repair:idempotent-v1
record._repair_studio_cancel_repair()
```
  </details>
- **RR - Cancel Repair-2** (`server_action_2343_rr_cancel_repair_2`, type `code`)
  - Function: Cancel Repair variant: requires a cancel reason, then closes the ticket at Repair Completed (per company) with audit slot 8 and marks it cancelled.
  - Depends on: `model helpdesk.ticket` (helpdesk)
  - Used by: — (not linked to a button, menu or automation)
  <details><summary>code (3 lines)</summary>

```python

# fix_repair:idempotent-v1
record._repair_studio_cancel_repair_2()
```
  </details>
- **RR - Change Repair Type to RUG** (`server_action_2159_rr_change_repair_type_to_rug`, type `code`)
  - Function: Change to RUG: requires the warranty card to be uploaded, resets linked sale order line prices to product cost (keeping the original price), and changes the ticket type to the RUG type (id 1).
  - Depends on: `model helpdesk.ticket` (helpdesk)
  - Used by: — (not linked to a button, menu or automation)
  <details><summary>code (3 lines)</summary>

```python

# fix_repair:idempotent-v1
record._repair_studio_change_repair_type_to_rug()
```
  </details>
- **RR - RR - Auto Select Product for RUG Repairs-22** (`server_action_2450_rr_rr_auto_select_product_for_rug_repairs_22`, type `code`)
  - Function: Fills sale order, picking, product and lot from the serial's customer delivery without the company filter, and sets SN Updated.
  - Depends on: `model helpdesk.ticket` (helpdesk)
  - Used by: — (not linked to a button, menu or automation)
  <details><summary>code (3 lines)</summary>

```python

# fix_repair:idempotent-v1
record._repair_auto_select_product_for_rug_22()
```
  </details>
- **RR - Receive at Factory** (`server_action_2002_rr_receive_at_factory`, type `code`)
  - Function: Receive at Factory: ticks Received at Factory, records received date/user and audit slot 2, and moves the ticket to the Received at Factory stage (per company).
  - Depends on: `model helpdesk.ticket` (helpdesk)
  - Used by: — (not linked to a button, menu or automation)
  <details><summary>code (3 lines)</summary>

```python

# fix_repair:idempotent-v1
record._repair_studio_receive_at_factory()
```
  </details>
- **RR - Receive at Sales Centre** (`server_action_2006_rr_receive_at_sales_centre`, type `code`)
  - Function: Receive at Sales Centre: ticks Received at Centre, records received date/user and audit slot 10, and moves the ticket to the Received at Sales Centre stage (per company).
  - Depends on: `model helpdesk.ticket` (helpdesk)
  - Used by: — (not linked to a button, menu or automation)
  <details><summary>code (3 lines)</summary>

```python

# fix_repair:idempotent-v1
record._repair_studio_receive_at_sales_centre()
```
  </details>
- **RR - Reopen Repair** (`server_action_2221_rr_reopen_repair`, type `code`)
  - Function: Reopen Repair: returns the ticket to the stage it was in before cancellation and records reopened flag, user, date and status.
  - Depends on: `model helpdesk.ticket` (helpdesk)
  - Used by: — (not linked to a button, menu or automation)
  <details><summary>code (3 lines)</summary>

```python

# fix_repair:idempotent-v1
record._repair_studio_reopen_repair()
```
  </details>
- **RR - Repair Seq.No** (`sa_f5_helpdesk_ticket_rr_repair_seq_no`, type `code`)
  - Function: Gives the ticket a number from the 'repair.seq' sequence when its name is empty or 'New'.
  - Depends on: `model helpdesk.ticket` (helpdesk)
  - Used by: — (not linked to a button, menu or automation)
  <details><summary>code (2 lines)</summary>

```python
# fix_repair:idempotent-v1
record._repair_seq_no_on_create_or_write()
```
  </details>
- **RR - Send to Factory** (`server_action_2001_rr_send_to_factory`, type `code`)
  - Function: Send to Factory: sets the ticket's Repair Location to the stock location flagged as Repair Factory Location (error if none), ticks Send to Factory and records shipped date/user and stage date.
  - Depends on: `model helpdesk.ticket` (helpdesk)
  - Used by: — (not linked to a button, menu or automation)
  <details><summary>code (3 lines)</summary>

```python

# fix_repair:idempotent-v1
record._repair_studio_send_to_factory()
```
  </details>
- **RR - Send to Sales Centre** (`server_action_2007_rr_send_to_sales_centre`, type `code`)
  - Function: Send to Sales Centre: ticks Send to Centre, records shipped date/user and audit slot 9, and moves the ticket to the Sent to Sales Centre stage (per company).
  - Depends on: `model helpdesk.ticket` (helpdesk)
  - Used by: — (not linked to a button, menu or automation)
  <details><summary>code (3 lines)</summary>

```python

# fix_repair:idempotent-v1
record._repair_studio_send_to_sales_centre()
```
  </details>
- **RR - Update RUG Approval in Pipeline** (`server_action_1998_rr_update_rug_approval_in_pipeline`, type `code`)
  - Function: Calls a placeholder method that does nothing; the action has no effect.
  - Depends on: `model helpdesk.ticket` (helpdesk)
  - Used by: — (not linked to a button, menu or automation)
  <details><summary>code (3 lines)</summary>

```python

# fix_repair:idempotent-v1
record._repair_studio_update_rug_approval_in_pipeline()
```
  </details>
- **RR - Validate Cancelled Tickets** (`sa_f5_helpdesk_ticket_rr_validate_cancelled_tickets`, type `code`)
  - Function: Blocks deletion of cancelled tickets with 'Cancelled tickets can not be deleted.'
  - Depends on: `model helpdesk.ticket` (helpdesk)
  - Used by: — (not linked to a button, menu or automation)
  <details><summary>code (2 lines)</summary>

```python
# fix_repair:idempotent-v1
record._repair_validate_cancelled_on_unlink()
```
  </details>
**Automations (9):**

| Name | Record name | State | Function | Depends on | Used by |
|---|---|---|---|---|---|
| JIN-Helpdesk(Repair) Seq.No | `base_automation_171_jin_helpdesk_repair_seq_no` | archived | When a record is created or updated on Helpdesk Ticket, runs _Execute Code_. **Archived — does not run.** | `model helpdesk.ticket` (helpdesk)<br>`server action Fix-repair.server_action_1976_rr_repair_seq_no` |  |
| RR - Auto Populate Repair Location | `base_automation_178_rr_auto_populate_repair_location` | archived | When a watched field changes in the form on Helpdesk Ticket, runs _Execute Code_. **Archived — does not run.** | `model helpdesk.ticket` (helpdesk)<br>`server action Fix-repair.server_action_2000_rr_auto_populate_repair_location` |  |
| RR - Auto Select Product for RUG Repairs | `base_automation_172_rr_auto_select_product_for_rug_repairs` | archived | When a watched field changes in the form on Helpdesk Ticket, runs _Execute Code_. **Archived — does not run.** | `model helpdesk.ticket` (helpdesk)<br>`server action Fix-repair.server_action_1989_rr_auto_select_product_for_rug_repairs` |  |
| RR - Auto Select Product for RUG Repairs-2 | `base_automation_173_rr_auto_select_product_for_rug_repairs_2` | archived | When a record is updated on Helpdesk Ticket and `[]`, runs _Execute Code_. **Archived — does not run.** | `model helpdesk.ticket` (helpdesk)<br>`server action Fix-repair.server_action_1990_rr_auto_select_product_for_rug_repairs_2` |  |
| RR - Auto Select Product for RUG Repairs-33 | `base_automation_243_rr_auto_select_product_for_rug_repairs_33` | archived | When a watched field changes in the form on Helpdesk Ticket and `[]`, runs _Execute Code_. **Archived — does not run.** | `model helpdesk.ticket` (helpdesk)<br>`server action Fix-repair.server_action_2451_rr_auto_select_product_for_rug_repairs_33` |  |
| RR - Auto Select Product for RUG Repairs-4 | `base_automation_175_rr_auto_select_product_for_rug_repairs_4` | archived | When a watched field changes in the form on Helpdesk Ticket, runs _Execute Code_. **Archived — does not run.** | `model helpdesk.ticket` (helpdesk)<br>`server action Fix-repair.server_action_1992_rr_auto_select_product_for_rug_repairs_4` |  |
| RR - Validate Cancelled Tickets | `base_automation_201_rr_validate_cancelled_tickets` | archived | When a record is deleted on Helpdesk Ticket and `[["x_studio_cancelled","=",True]]`, runs _Execute Code_. **Archived — does not run.** | `helpdesk.ticket.x_studio_cancelled`<br>`model helpdesk.ticket` (helpdesk)<br>`server action Fix-repair.server_action_2222_rr_validate_cancelled_tickets` |  |
| Slowness - Test | `base_automation_240_slowness_test` | archived | When a record is created or updated on Helpdesk Ticket and `["&",["team_id","=",1],["ticket_type_id","!=",False]]`, runs nothing (no action linked). **Archived — does not run.** | `helpdesk.ticket.team_id` (helpdesk)<br>`helpdesk.ticket.ticket_type_id` (helpdesk)<br>`model helpdesk.ticket` (helpdesk) |  |
| User Location Validation - Helpdesk | `base_automation_252_user_location_validation_helpdesk` | archived | When a record is created or updated on Helpdesk Ticket and `[["stage_id","=",1]]`, runs _Execute Code_. **Archived — does not run.** | `helpdesk.ticket.stage_id` (helpdesk)<br>`model helpdesk.ticket` (helpdesk)<br>`server action Fix-repair.server_action_2558_user_location_validation_helpdesk` |  |

**Approval rules (1):**

| Name | Record name | Approver group | Function | Depends on | Used by |
|---|---|---|---|---|---|
| Helpdesk Ticket/Reverse Transfer (User types / Internal User) (30) | `ar_relaxed_helpdesk_ticket_reverse_transfer_user_types_internal_user_30` | User types / Internal User | Before action _Reverse Transfer_ on Helpdesk Ticket runs, an approval from **User types / Internal User** is required (step 1). | `group base.group_user` (base)<br>`model helpdesk.ticket` (helpdesk)<br>`window action stock.act_stock_return_picking` (stock) |  |

**Window actions (4):**

| Name | Record name | Function | Depends on | Used by |
|---|---|---|---|---|
| Repair Job Details | `aw_f4_helpdesk_ticket_repair_job_details` | Opens **Helpdesk Ticket** records (kanban,tree,form,pivot,graph,activity). | `model helpdesk.ticket` (helpdesk) |  |
| Repair Job Details | `act_window_2312_repair_job_details` | Opens **Helpdesk Ticket** records (kanban,tree,form,pivot,graph,activity). | `model helpdesk.ticket` (helpdesk) | `menu Fix-repair.menu_f6_repair_job_details` |
| Repair Job Details for the Period - RUG Only | `aw_f4_helpdesk_ticket_repair_job_details_for_the_period_rug_only` | Opens **Helpdesk Ticket** records (kanban,tree,form,pivot,graph,activity). | `model helpdesk.ticket` (helpdesk) |  |
| Repair Job Details for the Period - RUG Only | `act_window_2234_repair_job_details_for_the_period_rug_only` | Opens **Helpdesk Ticket** records (kanban,tree,form,pivot,graph,activity). | `model helpdesk.ticket` (helpdesk) | `menu Fix-repair.menu_f6_repair_job_details_for_the_period_rug_only` |

**Views (9):**

| Name | Record name | Type | What it changes | Function | Depends on | Used by |
|---|---|---|---|---|---|---|
| Odoo Studio: helpdesk.ticket.form customization | `ported_view_helpdesk_ticket_form_4012` | form | before `//form[1]/sheet[1]/notebook[not(@name)][1]`: add field x_studio_rug_repair, field x_studio_rug_confirmed, field x_studio_normal_repair_with_serial_no, field x_studio_normal_repair_without_serial_no, field x_studio_source_location_1, field x_studio_cancel_reason, field x_studio_items, field x_studio_quick_repair_status, field x_studio_tracking; inside `//form[1]/sheet[1]/notebook[not(@name)][1]`: add page 'Warranty Details', page 'Cancel/ Reopen Log' | Helpdesk ticket form: adds hidden anchor fields (RUG repair, RUG confirmed, repair kinds, source location, cancel reason, items, quick repair status, tracking) and two tabs: 'Warranty Details' (warranty card, related information) and 'Cancel/ Reopen Log' (read-only cancel/reopen user and date). | `helpdesk.ticket.x_studio_cancel_reason`<br>`helpdesk.ticket.x_studio_cancelled_by`<br>`helpdesk.ticket.x_studio_cancelled_date`<br>`helpdesk.ticket.x_studio_items`<br>`helpdesk.ticket.x_studio_normal_repair_with_serial_no`<details><summary>+11 more</summary>`helpdesk.ticket.x_studio_normal_repair_without_serial_no`<br>`helpdesk.ticket.x_studio_quick_repair_status`<br>`helpdesk.ticket.x_studio_related_information`<br>`helpdesk.ticket.x_studio_reopened_by`<br>`helpdesk.ticket.x_studio_reopened_date`<br>`helpdesk.ticket.x_studio_rug_confirmed`<br>`helpdesk.ticket.x_studio_rug_repair`<br>`helpdesk.ticket.x_studio_source_location_1`<br>`helpdesk.ticket.x_studio_tracking`<br>`helpdesk.ticket.x_studio_warranty_card`<br>`view helpdesk.helpdesk_ticket_view_form` (helpdesk)</details> |  |
| Odoo Studio: helpdesk.ticket.form-button | `view_4013_odoo_studio_helpdesk_ticket_form_button_e` | form | inside `//form`: add field x_studio_cancelled, field x_studio_job_location, field x_studio_normal_repair_with_serial_no, field x_studio_normal_repair_without_serial_no, field x_studio_pick_id, field x_studio_receive_at_factory, field x_studio_repair_serial_created, field x_studio_rug_repair, field x_studio_sn_updated, field x_studio_valid_confirm_return, field x_studio_valid_return, field x_studio_virtual_location_id; set invisible=(use_product_repairs == False) or ((pickings_count == 0) or (x_studio_cancelled == True)) on `//header/button[@name='1797']`; set invisible=((x_studio_sn_updated == False) and (x_studio_normal_repair_without_serial_no == False)) or ((x_studio_rug_repair != True) or ((ticket_type_id == False) or ((x_studio_valid_return == True) or ((use_product_returns == False) or (x_studio_cancelled == True))))) on `//button[@name='870']`; set invisible=((x_studio_receive_at_factory == False) and (x_studio_job_location == 'Factory Repair')) or ((x_studio_valid_confirm_return == False) or ((x_studio_valid_return == False) or ((use_fsm == False) or ((fsm_task_count > 0) or (x_studio_cancelled == True))))) on `//button[@name='action_generate_fsm_task']`; set context={'default_ticket_id': id, 'default_company_id': company_id, 'default_picking_id': x_studio_pick_id} on `//button[@name='870']`; before `//header/button[@name='assign_ticket_to_self']`: add ; before `//header/button[@name='870']`: add ; after `//header/button[@name='assign_ticket_to_self']`: add button 'Receipt' … | Inactive (archived) ported Studio ticket form customization with button visibility rules for Repair, Return and Plan Intervention, Receipt buttons and a non-clickable stage bar; it has no effect while inactive. | `group stock.group_stock_user` (stock)<br>`helpdesk.ticket.company_id` (helpdesk)<br>`helpdesk.ticket.ticket_type_id` (helpdesk)<br>`helpdesk.ticket.use_product_returns` (helpdesk)<br>`helpdesk.ticket.x_studio_cancelled`<details><summary>+13 more</summary>`helpdesk.ticket.x_studio_job_location`<br>`helpdesk.ticket.x_studio_normal_repair_with_serial_no`<br>`helpdesk.ticket.x_studio_normal_repair_without_serial_no`<br>`helpdesk.ticket.x_studio_pick_id`<br>`helpdesk.ticket.x_studio_receive_at_factory`<br>`helpdesk.ticket.x_studio_repair_serial_created`<br>`helpdesk.ticket.x_studio_rug_repair`<br>`helpdesk.ticket.x_studio_sn_updated`<br>`helpdesk.ticket.x_studio_valid_confirm_return`<br>`helpdesk.ticket.x_studio_valid_return`<br>`helpdesk.ticket.x_studio_virtual_location_id`<br>`view helpdesk.helpdesk_ticket_view_form` (helpdesk)<br>`window action stock.act_stock_return_picking` (stock)</details> |  |
| Odoo Studio: helpdesk.ticket.kanban customization | `view_4735_odoo_studio_helpdesk_ticket_kanban_customization_e` | kanban | after `//field[@name='ticket_type_id']`: add field x_studio_quick_repair_status, field x_studio_rug_confirmed, field x_studio_rug_approval_status, field x_studio_material_availability; after `//div[@class='o_kanban_record_body']/field[@name='tag_ids']`: add field create_date, field x_studio_cancel_status, field x_studio_cancelled_date, field x_studio_reopen_status, field x_studio_reopened_date, field x_studio_stage_date | Helpdesk ticket kanban cards: show Quick Repair status, RUG approval status (for RUG-confirmed tickets), material availability, created date, cancel/reopen status and dates (when set), and stage date. | `helpdesk.ticket.x_studio_cancel_status`<br>`helpdesk.ticket.x_studio_cancelled_date`<br>`helpdesk.ticket.x_studio_material_availability`<br>`helpdesk.ticket.x_studio_quick_repair_status`<br>`helpdesk.ticket.x_studio_reopen_status`<details><summary>+5 more</summary>`helpdesk.ticket.x_studio_reopened_date`<br>`helpdesk.ticket.x_studio_rug_approval_status`<br>`helpdesk.ticket.x_studio_rug_confirmed`<br>`helpdesk.ticket.x_studio_stage_date`<br>`view helpdesk.helpdesk_ticket_view_kanban` (helpdesk)</details> |  |
| Odoo Studio: helpdesk.ticket.tree customization | `view_5027_odoo_studio_helpdesk_ticket_tree_customization_e` | tree | remove `//field[@name='partner_id']`; replace `//tree[1]/field[@name='team_id']`: add field partner_name, field create_date, field x_studio_materials_used, field x_studio_quantity, field x_studio_unit_price, field x_studio_items, field x_studio_qty, field x_studio_sales_price, field close_date; after `//field[@name='legend_done']`: add field x_studio_sale_order; after `//field[@name='sla_deadline']`: add field x_studio_repair_reason | Helpdesk ticket list: removes Customer and Team, adds customer name, created date, materials used, quantity, unit price, items, qty, sales price, closed date, sale order and repair reason columns. | `helpdesk.ticket.close_date` (helpdesk)<br>`helpdesk.ticket.partner_name` (helpdesk)<br>`helpdesk.ticket.x_studio_items`<br>`helpdesk.ticket.x_studio_materials_used`<br>`helpdesk.ticket.x_studio_qty`<details><summary>+6 more</summary>`helpdesk.ticket.x_studio_quantity`<br>`helpdesk.ticket.x_studio_repair_reason`<br>`helpdesk.ticket.x_studio_sale_order`<br>`helpdesk.ticket.x_studio_sales_price`<br>`helpdesk.ticket.x_studio_unit_price`<br>`view helpdesk.helpdesk_tickets_view_tree` (helpdesk)</details> |  |
| helpdesk.ticket.form.assign.to.me | `helpdesk_ticket_form_assign_to_me` | form | before `//field[@name='name']`: add field repair_stage_state, field task_done, field repair_picking_count, field has_ready_dispatch_picking; inside `//div[@name='button_box']`: add button 'action_view_repair_pickings'; set invisible=1 on `//button[@name='action_view_pickings']`; inside `//header`: add button 'Send to Factory', button 'Received at Factory', button 'Send to Sales Centre', button 'Received at Sales Centre', button 'Assign to Me' | Ticket form: adds a Movements smart button (all ticket transfers) replacing the standard Returns button, and header buttons Send to Factory, Received at Factory, Send to Sales Centre, Received at Sales Centre (each at the matching stage) and Assign to Me. | `helpdesk.ticket.action_assign_to_me()`<br>`helpdesk.ticket.action_received_at_factory()`<br>`helpdesk.ticket.action_received_at_sales_centre()`<br>`helpdesk.ticket.action_send_to_factory()`<br>`helpdesk.ticket.action_send_to_sales_centre()`<details><summary>+7 more</summary>`helpdesk.ticket.action_view_repair_pickings()` (Fix-Repair-Wizard-Nav, Fix-repair)<br>`helpdesk.ticket.has_ready_dispatch_picking`<br>`helpdesk.ticket.repair_picking_count`<br>`helpdesk.ticket.repair_stage_state`<br>`helpdesk.ticket.task_done`<br>`helpdesk.ticket.user_id` (helpdesk)<br>`view helpdesk.helpdesk_ticket_view_form` (helpdesk)</details> |  |
| helpdesk.ticket.form.hide.fields | `helpdesk_ticket_form_hide_fields` | form | set invisible=1 on `//field[@name='team_id']` | Helpdesk ticket form: hides the Team field. | `view helpdesk.helpdesk_ticket_view_form` (helpdesk) |  |
| helpdesk.ticket.form.hide.studio.fields | `helpdesk_ticket_form_hide_studio_fields` | form | set invisible=1 on `//field[@name='x_studio_rug_repair']`; set invisible=1 on `//field[@name='x_studio_rug_confirmed']`; set invisible=1 on `//field[@name='x_studio_quick_repair_status']`; set invisible=1 on `//field[@name='x_studio_cancel_reason']`; set invisible=1 on `//field[@name='x_studio_items']`; set invisible=1 on `//field[@name='x_studio_source_location_1']`; set invisible=1 on `//field[@name='x_studio_tracking']`; set invisible=1 on `//field[@name='x_studio_normal_repair_with_serial_no']` … | Helpdesk ticket form: hides the RUG Repair, RUG Confirmed, Quick Repair Status, Cancel Reason, Items, Source Location, Tracking and Normal Repair with/without Serial No fields. | `view helpdesk.helpdesk_ticket_view_form` (helpdesk) |  |
| helpdesk.ticket.form.statusbar.readonly | `helpdesk_ticket_form_statusbar_readonly` | form | set readonly=1 on `//field[@name='stage_id']` | Helpdesk ticket form: makes the stage status bar read-only, so stages change only through workflow buttons. | `view helpdesk.helpdesk_ticket_view_form` (helpdesk) |  |
| helpdesk.ticket.kanban.no.drag | `helpdesk_ticket_kanban_no_drag` | kanban | set records_draggable=0, groups_draggable=0, group_create=0, group_delete=0, group_edit=0, quick_create=0, edit=0, delete=0 on `//kanban`; replace `//templates/t[@t-name='kanban-menu']`: add t; remove `//field[@name='activity_ids'][@widget='kanban_activity']` | Helpdesk ticket kanban: disables dragging cards and columns, creating/editing/deleting columns, quick create, and card edit/delete; removes the card menu and the activity clock. | `view helpdesk.helpdesk_ticket_view_kanban` (helpdesk) |  |

**Mail templates (10):**

| Name | Record name | Function | Depends on | Used by |
|---|---|---|---|---|
| RR- Customer Repair Letter - Test | `mail_template_60_rr_customer_repair_letter_test` | Email template for Helpdesk Ticket; subject: _{{ object.display_name }}_. | `model helpdesk.ticket` (helpdesk) |  |
| RR- Customer Repair Letter - Test2 | `mail_template_63_rr_customer_repair_letter_test2` | Email template for Helpdesk Ticket; subject: _{{ object.display_name }}_. | `model helpdesk.ticket` (helpdesk) |  |
| RR- Customer Repair Letter - Test3 | `mail_template_64_rr_customer_repair_letter_test3` | Email template for Helpdesk Ticket; subject: _{{ object.display_name }}_. | `model helpdesk.ticket` (helpdesk) |  |
| RR- Customer Repair Letter - Test4 | `mail_template_71_rr_customer_repair_letter_test4` | Email template for Helpdesk Ticket; subject: _{{ object.display_name }}_. | `model helpdesk.ticket` (helpdesk) |  |
| Repair - Customer Letter | `mail_template_56_repair_customer_letter` | Email template for Helpdesk Ticket; subject: _{{ object.display_name }}_. | `model helpdesk.ticket` (helpdesk) |  |
| Repair - Customer Letter - 2 | `mail_template_59_repair_customer_letter_2` | Email template for Helpdesk Ticket; subject: _{{ object.display_name }}_. | `model helpdesk.ticket` (helpdesk) |  |
| Repair - Final Notice | `mail_template_66_repair_final_notice` | Email template for Helpdesk Ticket; subject: _{{ object.display_name }}_. | `model helpdesk.ticket` (helpdesk) |  |
| Repair - Final Notice - Estimated | `mail_template_67_repair_final_notice_estimated` | Email template for Helpdesk Ticket; subject: _{{ object.display_name }}_. | `model helpdesk.ticket` (helpdesk) |  |
| Repair - Final Notice - Scrappage | `mail_template_69_repair_final_notice_scrappage` | Email template for Helpdesk Ticket; subject: _{{ object.display_name }}_. | `model helpdesk.ticket` (helpdesk) |  |
| Repair - Reminding Letter | `mail_template_70_repair_reminding_letter` | Email template for Helpdesk Ticket; subject: _{{ object.display_name }}_. | `model helpdesk.ticket` (helpdesk) |  |
