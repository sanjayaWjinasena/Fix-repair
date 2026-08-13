# -*- coding: utf-8 -*-
from lxml import etree
from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountMoveLine(models.Model):
    """Native compute methods that back Studio compute strings on
    account.move.line. Rewriter installs one-line delegations into the
    Studio compute code so safe_eval overhead per compute becomes
    negligible; actual work runs at native Python speed.
    """
    _inherit = 'account.move.line'

    def _fix_repair_compute_credit_limit_2(self):
        for rec in self:
            rec.x_studio_credit_limit_2 = rec.partner_id.credit_limit or 0

    @api.model
    def _delegate_studio_computes_to_native(self):
        IrField = self.env['ir.model.fields'].sudo()
        # Reuse the sale.order marker constant
        marker = self.env['sale.order']._FIX_REPAIR_IDEMPOTENCE_MARKER

        delegations = [
            ('x_studio_credit_limit_2',
             'credit_limit',
             'self._fix_repair_compute_credit_limit_2()'),
        ]
        for name, guard_substring, call in delegations:
            field = IrField.search([
                ('model', '=', 'account.move.line'),
                ('name', '=', name),
            ], limit=1)
            if not field:
                continue
            code = field.compute or ''
            if marker in code:
                continue
            if guard_substring not in code:
                continue
            field.write({'compute': f"{marker}\n{call}\n"})


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_rug_invoice = fields.Boolean(compute='_compute_is_rug_invoice')
    is_rug_account_set = fields.Boolean(compute='_compute_is_rug_account_set')

    @api.depends('invoice_origin', 'move_type')
    def _compute_is_rug_invoice(self):
        for move in self:
            if move.move_type != 'out_invoice' or not move.invoice_origin:
                move.is_rug_invoice = False
                continue
            so = self.env['sale.order'].sudo().search(
                [('name', '=', move.invoice_origin)], limit=1
            )
            # RUG-invoice treatment only applies to WARRANTY repairs:
            # quotation_type == 'Repair', NOT customer-pays (formerly the
            # 'Not Under Warranty' quotation type), and NOT rug-rejected
            # mid-flow. Anything else falls back to a normal customer-
            # pays invoice: Register Payment stays available, the
            # "Change to RUG Account" button stays hidden, and
            # _rug_auto_settle is a no-op on action_post.
            move.is_rug_invoice = (
                so.x_studio_quotation_type == 'Repair'
                and not so.x_repair_customer_pays
                and not so.x_studio_rug_rejected
            )

    @api.depends('invoice_line_ids.account_id', 'company_id')
    def _compute_is_rug_account_set(self):
        """True when every product line on this invoice already uses the
        company's configured RUG account. Used to hide the 'Change to
        RUG Account' button once it has been clicked (or the lines were
        created on that account already)."""
        for move in self:
            config = self.env['x_repair_accounts'].sudo().search(
                [('x_studio_company_id', '=', move.company_id.id)], limit=1
            )
            rug_account = config.x_studio_rug_account if config else False
            product_lines = move.invoice_line_ids.filtered(
                lambda l: l.display_type not in ('line_section', 'line_note')
            )
            move.is_rug_account_set = bool(
                rug_account
                and product_lines
                and all(l.account_id == rug_account for l in product_lines)
            )

    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            for sheet in arch.xpath('//sheet'):
                for fname in ('is_rug_invoice', 'is_rug_account_set'):
                    fld = etree.Element('field')
                    fld.set('name', fname)
                    fld.set('invisible', '1')
                    sheet.insert(0, fld)
                break
            for header in arch.xpath('//header'):
                btn = etree.Element('button')
                btn.set('name', 'action_change_to_rug_account')
                btn.set('string', 'Change to RUG Account')
                btn.set('type', 'object')
                btn.set('class', 'btn-secondary')
                btn.set('invisible',
                        'not is_rug_invoice or state != "draft" or is_rug_account_set')
                header.insert(0, btn)
                break

            # Register Payment: hide on RUG-confirmed invoices, but ONLY while
            # the RUG is still confirmed. If it's been rejected the customer
            # pays the invoice and we want Register Payment available again.
            #
            # Previously referenced x_studio_rug_confirmed / x_studio_rug_rejected
            # directly — those fields live on sale.order, not account.move.
            # On dev env's account.move form, OWL couldn't resolve them
            # ("Name 'x_studio_rug_confirmed' is not defined") and the entire
            # invoice form crashed to render. Switched to is_rug_invoice which
            # is a proper account.move field (compute above) that already
            # encodes the same predicate: Repair quotation type, not customer-
            # pays, not rug-rejected — i.e. a warranty invoice that will
            # auto-settle via _rug_auto_settle() on post, so no manual
            # Register Payment is needed.
            for btn in arch.xpath("//button[@name='action_register_payment']"):
                existing = btn.get('invisible', '')
                extra = "is_rug_invoice"
                btn.set('invisible', f"({existing}) or {extra}" if existing else extra)

            # Post (Confirm) button on RUG invoices: hide until the
            # lines have been reassigned to the RUG account. The
            # workflow requires the salesperson to click
            # "Change to RUG Account" first, then Post — the
            # _rug_auto_settle side effect on action_post depends on
            # invoice lines already sitting on the RUG account.
            # Posting a RUG invoice before that reassignment leaves
            # the auto-settle a no-op and the balance sits stuck on
            # the standard Debtors account without the offsetting
            # RUG-account entry.
            #
            # is_rug_invoice AND not is_rug_account_set → hide Post.
            # Non-RUG invoices are unaffected.
            for btn in arch.xpath("//button[@name='action_post']"):
                existing = btn.get('invisible', '')
                extra = "(is_rug_invoice and not is_rug_account_set)"
                btn.set('invisible', f"({existing}) or {extra}" if existing else extra)

            # Fields-disable branch: freeze the invoice form once it
            # is Confirmed (state='posted'). Odoo core respects
            # state=posted for most account.move fields, but Studio-
            # added x_studio_* fields and any other view-arch
            # additions don't consistently honour it — leaving room
            # for post-post edits to drift the invoice header data
            # away from the accounting entries it's now anchored to.
            #
            # OR the readonly on every top-level <field> under the
            # sheet with "state == 'posted'". Non-posted moves
            # (draft, cancelled) keep their editable state.
            #
            # not(ancestor::field): skip fields inside embedded
            # views (invoice_line_ids grid, tax_totals sub-widgets,
            # line_ids one2many, chatter, etc.). Those subrecords
            # are on account.move.line / other models; Odoo's own
            # line readonly rules apply to them.
            for field_el in arch.xpath(
                    "//sheet//field[not(ancestor::field)]"):
                if field_el.get('invisible') == '1':
                    continue
                existing = field_el.get('readonly', '')
                extra = "state == 'posted'"
                field_el.set(
                    'readonly',
                    f"({existing}) or ({extra})" if existing else extra,
                )
        return arch, view

    def action_change_to_rug_account(self):
        for move in self:
            config = self.env['x_repair_accounts'].sudo().search(
                [('x_studio_company_id', '=', move.company_id.id)], limit=1
            )
            if not config or not config.x_studio_rug_account:
                raise UserError(
                    f"No RUG account configured for company '{move.company_id.name}'. "
                    "Please set it up in Repair Accounts."
                )
            rug_account = config.x_studio_rug_account
            product_lines = move.invoice_line_ids.filtered(
                lambda l: l.display_type not in ('line_section', 'line_note')
            )
            product_lines.write({'account_id': rug_account.id})

    def action_post(self):
        res = super().action_post()
        for move in self:
            if (move.move_type == 'out_invoice'
                    and move.is_rug_invoice
                    and move.state == 'posted'):
                move._rug_auto_settle()
        return res

    def _rug_auto_settle(self):
        """Skip the Register Payment step on a freshly posted RUG invoice
        by creating an internal clearing entry DR <RUG account> / CR
        <Debtors> for the receivable balance, then reconciling the two
        Debtors lines. The invoice's payment_state moves straight to
        'paid'; the RUG account's CR (from the invoice) and DR (from
        the clearing) net to zero so no real bank movement is involved.

        No-op when:
          • no unreconciled receivable line exists (already settled)
          • the configured per-company RUG account is missing
          • the invoice doesn't have any line on the RUG account (i.e.
            'Change to RUG Account' wasn't clicked before post)
        """
        self.ensure_one()
        if self.payment_state in ('paid', 'partial', 'reversed'):
            return

        receivable_lines = self.line_ids.filtered(
            lambda l: l.account_id.account_type == 'asset_receivable'
            and not l.reconciled
            and (l.debit or l.credit)
        )
        if not receivable_lines:
            return

        config = self.env['x_repair_accounts'].sudo().search(
            [('x_studio_company_id', '=', self.company_id.id)], limit=1
        )
        if not config or not config.x_studio_rug_account:
            return
        rug_account = config.x_studio_rug_account

        invoice_rug_lines = self.line_ids.filtered(
            lambda l: l.account_id == rug_account
        )
        if not invoice_rug_lines:
            return

        journal = self.env['account.journal'].sudo().search(
            [('type', '=', 'general'),
             ('company_id', '=', self.company_id.id)],
            limit=1,
        )
        if not journal:
            raise UserError(
                f"No miscellaneous (type='general') journal found for "
                f"'{self.company_id.name}'. Cannot auto-settle the RUG invoice."
            )

        amount = sum(receivable_lines.mapped('debit')) - sum(receivable_lines.mapped('credit'))
        if amount <= 0:
            return

        receivable_account = receivable_lines[0].account_id
        clearing = self.env['account.move'].sudo().create({
            'journal_id': journal.id,
            'company_id': self.company_id.id,
            'partner_id': self.partner_id.id,
            'date': self.invoice_date or fields.Date.context_today(self),
            'ref': f'RUG settlement — {self.name}',
            'line_ids': [
                (0, 0, {
                    'account_id': rug_account.id,
                    'partner_id': self.partner_id.id,
                    'debit': amount,
                    'credit': 0,
                    'name': f'RUG settlement — {self.name}',
                }),
                (0, 0, {
                    'account_id': receivable_account.id,
                    'partner_id': self.partner_id.id,
                    'debit': 0,
                    'credit': amount,
                    'name': f'RUG settlement — {self.name}',
                }),
            ],
        })
        clearing.action_post()

        # Reconcile Debtors: invoice DR ↔ clearing CR → invoice goes 'paid'
        (
            receivable_lines
            | clearing.line_ids.filtered(lambda l: l.account_id == receivable_account)
        ).reconcile()

        # Reconcile RUG account: invoice CR ↔ clearing DR → both net to zero
        invoice_rug_unrec = invoice_rug_lines.filtered(lambda l: not l.reconciled)
        if invoice_rug_unrec and rug_account.reconcile:
            (
                invoice_rug_unrec
                | clearing.line_ids.filtered(lambda l: l.account_id == rug_account)
            ).reconcile()
