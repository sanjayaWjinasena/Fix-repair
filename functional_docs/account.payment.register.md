# Fix-repair — `account.payment.register`

[← back to Functional_Documentation.md](../Functional_Documentation.md)

### `account.payment.register` — Register Payment

*Extends a model created by `account`.* Python: `models/account_payment_register.py`.

**Summary:**

<!-- SUMMARY:model:account.payment.register -->
Changes the Register Payment wizard in two ways. `_compute_amount` keeps an Amount the user has already entered when the journal changes, instead of resetting it to the invoice residual. `action_create_payments` calls `_validate_repair_advance_threshold`, which blocks payment on non-RUG repair invoices when the total paid after this payment would be below the company's advance-payment percentage.
<!-- /SUMMARY -->

**Python methods (5):**

| Method | Function | Decorators | Extends standard | Depends on | Used by | Where |
|---|---|---|---|---|---|---|
| `_compute_amount` | Override of the Register Payment wizard amount compute: keeps any non-zero amount already entered instead of resetting it to the invoice balance when the journal or currency changes. |  | yes |  |  | `models/account_payment_register.py:9` |
| `action_create_payments` | Override of Create Payment: first enforces the repair advance-payment minimum, then, once an invoice is in payment or paid, moves the helpdesk ticket of each non-RUG-approved repair order to 'Advance Received' if it is still in an earlier stage. |  | yes | `account.move.line.move_id` (account)<br>`account.payment.register._validate_repair_advance_threshold()`<br>`account.payment.register.line_ids` (account)<br>`model project.task` (project) |  | `models/account_payment_register.py:66` |
| `_validate_repair_advance_threshold` | Raises an error when a payment on a customer-pays or RUG-rejected repair invoice would leave total paid below the company's advance-payment percentage of the order total. |  |  | `account.payment.register._format_money()`<br>`account.payment.register._format_pct()` | `account.payment.register.action_create_payments()` (Fix-Repair-Wizard-Nav, Fix-repair) | `models/account_payment_register.py:113` |
| `_format_pct` | Helper that formats a percentage without trailing zeros (50.0 to '50') for error messages. | staticmethod |  |  | `account.payment.register._validate_repair_advance_threshold()` | `models/account_payment_register.py:184` |
| `_format_money` | Helper that formats an amount with thousands separators and two decimals for error messages. | staticmethod |  |  | `account.payment.register._validate_repair_advance_threshold()` | `models/account_payment_register.py:189` |
