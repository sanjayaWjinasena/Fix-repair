"""Tests for the repair helpdesk-ticket actions fixed in the refactor."""

from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestHelpdeskTicketActions(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ticket = cls.env["helpdesk.ticket"].create({"name": "Refactor test ticket"})
        cls.rug_type = cls.env["helpdesk.ticket.type"].search(
            [("name", "ilike", "Under Warranty - RUG")], limit=1
        ) or cls.env["helpdesk.ticket.type"].create({"name": "Under Warranty - RUG"})
        # internal user with no helpdesk rights at all
        cls.plain_user = new_test_user(
            cls.env, login="refactor_plain_user", groups="base.group_user"
        )

    def test_dispatch_without_collection_shows_message(self):
        """Dispatch before collection raises a UserError, not a NameError."""
        self.ticket.x_studio_pick_id = False
        with self.assertRaises(UserError):
            self.ticket.fix_repair_action_direct_dispatch()

    def test_change_to_rug_sets_type(self):
        self.ticket.action_change_to_rug()
        self.assertEqual(self.ticket.ticket_type_id, self.rug_type)

    def test_change_to_rug_requires_edit_rights(self):
        """The sudo() write must not let users without ticket rights edit it."""
        with self.assertRaises(AccessError):
            self.ticket.with_user(self.plain_user).action_change_to_rug()

    def test_create_repair_serial_requires_edit_rights(self):
        product = self.env["product.product"].create({"name": "Refactor test product"})
        self.ticket.product_id = product
        with self.assertRaises(AccessError):
            self.ticket.with_user(self.plain_user).action_create_repair_serial()

    def test_create_repair_serial_without_product(self):
        self.ticket.product_id = False
        with self.assertRaises(UserError):
            self.ticket.action_create_repair_serial()
