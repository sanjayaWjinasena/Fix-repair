# -*- coding: utf-8 -*-
from lxml import etree
from markupsafe import Markup, escape
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Mirrors the linked helpdesk ticket's repair_stage_state for use in view
    # expressions (e.g. gating Create Invoice on Repair Completed for RUG SOs).
    ticket_repair_stage_state = fields.Char(compute='_compute_ticket_repair_stage_state')

    def _compute_ticket_repair_stage_state(self):
        for order in self:
            task = order.sudo().task_id or self.env['project.task'].sudo().search(
                [('sale_order_id', '=', order.id)], limit=1
            )
            ticket = task.helpdesk_ticket_id if task else None
            order.ticket_repair_stage_state = (ticket.repair_stage_state or '') if ticket else ''

    @api.model
    def _fix_advance_payment_project_field(self):
        """Fix Studio server action 'Create Advance Payment' that passes
        record.id (sale.order ID) to x_studio_project_no_1 which is a
        Many2one to project.project — causing a FK violation when the SO id
        does not match any project.project id.

        Correct substitution: record.x_studio_project_no.id (the Project No
        field on sale.order, also Many2one to project.project).
        Search by code content so it survives action ID changes in Studio.
        Handles both space variants Studio may write (with or without space
        after the colon).
        """
        action = self.env['ir.actions.server'].sudo().search([
            ('model_id.model', '=', 'sale.order'),
            ('code', 'like', "x_studio_project_no_1"),
            ('code', 'like', "account.payment"),
        ], limit=1)
        if not action:
            return
        new = ("'x_studio_project_no_1': "
               "record.x_studio_project_no.id if record.x_studio_project_no else False,")
        code = action.code or ''
        # Studio may write the dict with or without a space after the colon
        for old in (
            "'x_studio_project_no_1':record.id,",
            "'x_studio_project_no_1': record.id,",
        ):
            if old in code:
                code = code.replace(old, new)
                break

        # Odoo 17 requires payment_method_line_id on account.payment.
        # Use the first inbound method line from the journal chosen above.
        pm_old = "'journal_id':journal.id})"
        pm_new = (
            "'journal_id':journal.id,"
            "'payment_method_line_id':"
            "journal.inbound_payment_method_line_ids[:1].id "
            "if journal.inbound_payment_method_line_ids else False})"
        )
        if pm_old in code:
            code = code.replace(pm_old, pm_new)

        action.write({'code': code})

    @api.model
    def _ensure_not_under_warranty_selection(self):
        """Add 'Not Under Warranty' to x_studio_quotation_type if absent.

        In Odoo 17 selection values live in ir.model.fields.selection,
        not in a column on ir_model_fields itself.
        Called from data/fix_repair_data.xml and inline before any write.
        """
        field = self.env['ir.model.fields'].sudo().search([
            ('model', '=', 'sale.order'),
            ('name', '=', 'x_studio_quotation_type'),
        ], limit=1)
        if not field:
            return
        IrSel = self.env['ir.model.fields.selection'].sudo()
        if not IrSel.search([
            ('field_id', '=', field.id),
            ('value', '=', 'Not Under Warranty'),
        ], limit=1):
            IrSel.create({
                'field_id': field.id,
                'value': 'Not Under Warranty',
                'name': 'Not Under Warranty',
                'sequence': 100,
            })

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            # Inject ticket_repair_stage_state so client can evaluate button conditions.
            for sheet in arch.xpath("//sheet"):
                fld = etree.Element('field')
                fld.set('name', 'ticket_repair_stage_state')
                fld.set('invisible', '1')
                sheet.insert(0, fld)
                break

            # Create Invoice: for RUG-confirmed SOs, only show once the ticket
            # reaches Repair Completed stage.
            for btn in arch.xpath("//button[@id='create_invoice']"):
                existing = btn.get('invisible', '')
                extra = "(x_studio_rug_confirmed and ticket_repair_stage_state != 'repair_completed')"
                btn.set('invisible', f"({existing}) or {extra}" if existing else extra)

            # Order Payment Type: editable in draft/sent for all customers
            for el in arch.xpath("//field[@name='x_studio_order_payment_method']"):
                el.set('readonly', "state in ('cancel', 'done', 'sale')")

            # Quotation Type: editable in draft/sent until an FSM task is linked.
            # Allows switching between Repair and Not Under Warranty; locks once
            # Plan Intervention is clicked (task_id set) or the SO is confirmed.
            for el in arch.xpath("//field[@name='x_studio_quotation_type']"):
                el.set('readonly',
                       "(task_id != False) or "
                       "(state not in ['draft', 'sent'])")

            # RUG Request button: only on Repair quotations, before request is sent
            rug_req_invisible = (
                "(x_studio_quotation_type != 'Repair') or "
                "(state not in ['draft', 'sent']) or "
                "(x_studio_rug_request_sent == True) or "
                "(x_studio_rug_rejected == True) or "
                "(x_studio_rug_approved == True)"
            )
            for btn in arch.xpath("//button[@name='1980']"):
                btn.set('invisible', rug_req_invisible)

            # Approve/Reject RUG buttons: only on Repair quotations, after request is sent
            rug_approve_invisible = (
                "(x_studio_quotation_type != 'Repair') or "
                "(state not in ['draft', 'sent']) or "
                "(x_studio_rug_request_sent == False) or "
                "(x_studio_rug_rejected == True) or "
                "(x_studio_rug_approved == True)"
            )
            # Approve: rewire to our method so it confirms the SO directly (no send wizard)
            for btn in arch.xpath("//button[@name='1981']"):
                btn.set('invisible', rug_approve_invisible)
                btn.set('type', 'object')
                btn.set('name', 'action_approve_rug_direct')
            # Reject: keep Studio server action, only override visibility
            for btn in arch.xpath("//button[@name='2004']"):
                btn.set('invisible', rug_approve_invisible)

            # Confirm button: hide on Repair SOs until RUG is approved
            for btn in arch.xpath("//button[@name='action_confirm']"):
                existing = btn.get('invisible', '')
                extra = "(x_studio_quotation_type == 'Repair' and not x_studio_rug_approved)"
                btn.set('invisible', f"({existing}) or {extra}" if existing else extra)

            # Send PRO-FORMA Invoice: not used — hide both instances.
            for btn in arch.xpath("//button[contains(@id, 'send_proforma')]"):
                btn.set('invisible', '1')

            # Cancel: not used in the repair workflow — hide entirely.
            for btn in arch.xpath("//button[@name='action_cancel']"):
                btn.set('invisible', '1')

            # Create Advance Payment: not used — hide entirely.
            for btn in arch.xpath("//button[@name='2341']"):
                btn.set('invisible', '1')

            # Send by Email: Not Under Warranty type has no RUG flow — show directly
            # Studio has hidden all action_quotation_send buttons via an always-true
            # `state not in ['False']` guard; inject a clean button for this type.
            for header in arch.xpath("//header"):
                btn = etree.Element('button')
                btn.set('name', 'action_quotation_send')
                btn.set('string', 'Send by Email')
                btn.set('type', 'object')
                btn.set('class', 'btn-primary')
                btn.set('invisible',
                    "x_studio_quotation_type != 'Not Under Warranty' "
                    "or state not in ('draft', 'sent')"
                )
                header.insert(0, btn)

        return arch, view

    @api.onchange('partner_id')
    def _onchange_partner_payment_method(self):
        for order in self:
            if order.partner_id.x_studio_payment_method:
                order.x_studio_order_payment_method = order.partner_id.x_studio_payment_method

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('x_studio_order_payment_method'):
                partner_id = vals.get('partner_id')
                if partner_id:
                    partner = self.env['res.partner'].sudo().browse(partner_id)
                    if partner.x_studio_payment_method:
                        vals['x_studio_order_payment_method'] = partner.x_studio_payment_method
        return super().create(vals_list)

    def action_quotation_send(self):
        action = super().action_quotation_send()
        if self.x_studio_quotation_type != 'Not Under Warranty':
            return action

        # Move linked helpdesk ticket from Diagnosis → Estimation Sent to Customer
        # when the Send by Email button is clicked (mirrors the RUG flow where
        # clicking Request RUG Approval triggers the same transition).
        self._move_ticket_to_stage(self, 'Estimation Sent to Customer')

        # Build the full portal URL (get_portal_url returns a relative path)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        portal_url = base_url + self.get_portal_url()

        link_line = Markup(
            '<div style="margin-top:24px; text-align:center;">'
            '<a href="{url}" '
            'style="display:inline-block; padding:12px 24px; '
            'background-color:#875A7B; color:#ffffff; text-decoration:none; '
            'border-radius:4px; font-family:Arial,sans-serif; font-size:14px; '
            'font-weight:bold;">'
            'View Quotation'
            '</a>'
            '</div>'
        ).format(url=escape(portal_url))

        ctx = action.get('context', {})
        template_id = ctx.get('default_template_id')
        if template_id:
            template = self.env['mail.template'].browse(template_id)
            rendered = template._render_field('body_html', self.ids, options={'post_process': True})
            body = rendered.get(self.id, '') or ''
            ctx['default_body'] = body + link_line
            # Clear the template so the composer uses our pre-built body directly
            ctx['default_template_id'] = False
            ctx['default_use_template'] = False
        else:
            ctx['default_body'] = ctx.get('default_body', '') + link_line

        action['context'] = ctx
        return action

    def action_confirm(self):
        result = super().action_confirm()
        for order in self:
            if order.x_studio_quotation_type == 'Not Under Warranty':
                self._move_ticket_to_stage(order, 'Estimation Approval Received')
        return result

    def action_approve_rug_direct(self):
        self.write({'x_studio_rug_approved': True})
        # write() moves the ticket to 'Estimation Approval Received'.
        # Confirm button becomes visible once rug_approved=True; user clicks it manually.

    def _move_ticket_to_stage(self, order, stage_name):
        """Find the linked helpdesk ticket and move it to the named stage."""
        sudo_order = order.sudo()
        task = sudo_order.task_id or self.env['project.task'].sudo().search(
            [('sale_order_id', '=', order.id)], limit=1
        )
        ticket = task.sudo().helpdesk_ticket_id if task else False
        if not ticket:
            return
        stage = self.env['helpdesk.stage'].sudo().search(
            [('name', '=', stage_name),
             ('team_ids', 'in', ticket.team_id.ids),
             '|',
             ('x_studio_company_id', '=', ticket.company_id.id),
             ('x_studio_company_id', '=', False)],
            limit=1
        )
        if stage:
            ticket.sudo().write({'stage_id': stage.id})

    def write(self, vals):
        # When partner changes on a draft/sent SO, sync Order Payment Type from customer
        if vals.get('partner_id') and not vals.get('x_studio_order_payment_method'):
            partner = self.env['res.partner'].sudo().browse(vals['partner_id'])
            if partner.x_studio_payment_method:
                vals = dict(vals, x_studio_order_payment_method=partner.x_studio_payment_method)

        res = super().write(vals)

        # RUG request sent → Estimation Sent to Customer
        if vals.get('x_studio_rug_request_sent'):
            for order in self:
                self._move_ticket_to_stage(order, 'Estimation Sent to Customer')

        # RUG approved or rejected → Estimation Approval Received
        if vals.get('x_studio_rug_approved') or vals.get('x_studio_rug_rejected'):
            for order in self:
                self._move_ticket_to_stage(order, 'Estimation Approval Received')

        # RUG approved → reprice all lines to product cost price
        if vals.get('x_studio_rug_approved'):
            for order in self:
                if order.x_studio_quotation_type == 'Repair':
                    for line in order.order_line:
                        if line.product_id:
                            line.write({'price_unit': line.product_id.standard_price})

        return res
