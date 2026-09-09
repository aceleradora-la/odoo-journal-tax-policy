from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestSaleJournalTaxPolicy(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.sale_journal = cls.company_data["default_journal_sale"]
        cls.no_tax_journal = cls.env["account.journal"].create(
            {
                "name": "Sales without taxes",
                "code": "SNTX",
                "type": "sale",
                "company_id": cls.company.id,
                "tax_policy": "no_tax",
            }
        )
        # Invoice on ordered quantities so that _create_invoices() has
        # something to work with without the stock module around.
        cls.product_a.invoice_policy = "order"

    def _create_order(self, journal=None, partner=None, line_vals=None, with_line=True):
        vals = {
            "partner_id": (partner or self.partner_a).id,
            "journal_id": journal.id if journal else False,
        }
        if with_line:
            vals["order_line"] = [
                Command.create(
                    {
                        "product_id": self.product_a.id,
                        "product_uom_qty": 1.0,
                        **(line_vals or {}),
                    }
                )
            ]
        return self.env["sale.order"].with_company(self.company).create(vals)

    # ------------------------------------------------------------------
    # Nothing changes without a 'no_tax' journal
    # ------------------------------------------------------------------

    def test_standard_journal_keeps_the_product_taxes(self):
        order = self._create_order(self.sale_journal)
        self.assertEqual(order.order_line.tax_ids, self.tax_sale_a)

    def test_empty_journal_keeps_the_product_taxes(self):
        """An empty journal means 'whatever the invoice picks', so stay standard."""
        order = self._create_order()
        self.assertFalse(order.journal_id)
        self.assertEqual(order.order_line.tax_ids, self.tax_sale_a)

    def test_switching_between_two_standard_journals_keeps_manual_taxes(self):
        other_journal = self.env["account.journal"].create(
            {
                "name": "Other sales",
                "code": "OSAL",
                "type": "sale",
                "company_id": self.company.id,
            }
        )
        order = self._create_order(self.sale_journal)
        order.order_line.tax_ids = False

        order.journal_id = other_journal

        self.assertFalse(
            order.order_line.tax_ids,
            "No 'no_tax' journal was involved, so we must not touch the taxes.",
        )

    # ------------------------------------------------------------------
    # A 'no_tax' journal never carries taxes
    # ------------------------------------------------------------------

    def test_no_tax_journal_drops_the_product_taxes(self):
        order = self._create_order(self.no_tax_journal)
        self.assertFalse(order.order_line.tax_ids)
        self.assertEqual(order.amount_total, order.amount_untaxed)

    def test_line_added_after_the_journal_has_no_taxes(self):
        """Pick the journal first, load the lines afterwards."""
        order = self._create_order(self.no_tax_journal, with_line=False)

        order.write(
            {
                "order_line": [
                    Command.create(
                        {"product_id": self.product_a.id, "product_uom_qty": 1.0}
                    )
                ]
            }
        )

        self.assertFalse(order.order_line.tax_ids)

    def test_no_tax_journal_ignores_the_fiscal_position(self):
        """partner_b maps tax_sale_a to tax_sale_b, we still want nothing."""
        order = self._create_order(self.no_tax_journal, partner=self.partner_b)
        self.assertEqual(order.fiscal_position_id, self.fiscal_pos_a)
        self.assertFalse(order.order_line.tax_ids)

    def test_no_tax_journal_drops_explicitly_written_taxes(self):
        order = self._create_order(
            self.no_tax_journal,
            line_vals={"tax_ids": [Command.set(self.tax_sale_a.ids)]},
        )
        self.assertFalse(order.order_line.tax_ids)

    def test_no_tax_journal_drops_taxes_added_afterwards(self):
        order = self._create_order(self.no_tax_journal)

        order.order_line.tax_ids = [Command.set(self.tax_sale_a.ids)]

        self.assertFalse(order.order_line.tax_ids)

    # ------------------------------------------------------------------
    # Switching the journal back and forth
    # ------------------------------------------------------------------

    def test_switching_to_a_no_tax_journal_drops_the_taxes(self):
        order = self._create_order(self.sale_journal)
        self.assertEqual(order.order_line.tax_ids, self.tax_sale_a)

        order.journal_id = self.no_tax_journal

        self.assertFalse(order.order_line.tax_ids)
        self.assertTrue(order.taxes_removed_by_journal)
        self.assertEqual(order.amount_total, order.amount_untaxed)

    def test_switching_back_restores_the_standard_taxes(self):
        order = self._create_order(self.sale_journal)
        order.journal_id = self.no_tax_journal
        self.assertFalse(order.order_line.tax_ids)

        order.journal_id = self.sale_journal

        self.assertEqual(order.order_line.tax_ids, self.tax_sale_a)
        self.assertFalse(order.taxes_removed_by_journal)

    def test_switching_back_applies_the_fiscal_position_mapping(self):
        order = self._create_order(self.sale_journal, partner=self.partner_b)
        self.assertEqual(order.order_line.tax_ids, self.tax_sale_b)
        order.journal_id = self.no_tax_journal
        self.assertFalse(order.order_line.tax_ids)

        order.journal_id = self.sale_journal

        self.assertEqual(order.order_line.tax_ids, self.tax_sale_b)

    # ------------------------------------------------------------------
    # End to end: the invoice built from the order
    # ------------------------------------------------------------------

    def test_invoice_created_from_the_order_has_no_taxes(self):
        order = self._create_order(self.no_tax_journal)
        order.action_confirm()

        invoice = order._create_invoices()

        self.assertEqual(invoice.journal_id, self.no_tax_journal)
        self.assertFalse(invoice.invoice_line_ids.tax_ids)
        self.assertEqual(invoice.amount_total, invoice.amount_untaxed)
