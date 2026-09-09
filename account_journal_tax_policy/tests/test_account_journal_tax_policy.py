from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import Form, tagged


@tagged("post_install", "-at_install")
class TestAccountJournalTaxPolicy(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sale_journal = cls.company_data["default_journal_sale"]
        cls.purchase_journal = cls.company_data["default_journal_purchase"]
        cls.no_tax_sale_journal = cls.env["account.journal"].create(
            {
                "name": "Sales without taxes",
                "code": "SNTX",
                "type": "sale",
                "company_id": cls.company_data["company"].id,
                "tax_policy": "no_tax",
            }
        )
        cls.no_tax_purchase_journal = cls.env["account.journal"].create(
            {
                "name": "Purchases without taxes",
                "code": "PNTX",
                "type": "purchase",
                "company_id": cls.company_data["company"].id,
                "tax_policy": "no_tax",
            }
        )

    def _create_invoice(self, journal, move_type="out_invoice", partner=None, line_vals=None):
        return (
            self.env["account.move"]
            .with_company(self.company_data["company"])
            .create(
                {
                    "move_type": move_type,
                    "partner_id": (partner or self.partner_a).id,
                    "invoice_date": "2024-01-01",
                    "journal_id": journal.id,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "product_id": self.product_a.id,
                                "quantity": 1,
                                "price_unit": 100.0,
                                **(line_vals or {}),
                            }
                        )
                    ],
                }
            )
        )

    # ------------------------------------------------------------------
    # A journal with the standard policy must not change at all
    # ------------------------------------------------------------------

    def test_standard_journal_keeps_the_product_taxes(self):
        invoice = self._create_invoice(self.sale_journal)
        self.assertEqual(invoice.invoice_line_ids.tax_ids, self.tax_sale_a)

    def test_switching_between_two_standard_journals_keeps_manual_taxes(self):
        other_journal = self.env["account.journal"].create(
            {
                "name": "Other sales",
                "code": "OSAL",
                "type": "sale",
                "company_id": self.company_data["company"].id,
            }
        )
        invoice = self._create_invoice(self.sale_journal)
        invoice.invoice_line_ids.tax_ids = [Command.clear()]

        invoice.journal_id = other_journal

        self.assertFalse(
            invoice.invoice_line_ids.tax_ids,
            "Odoo does not recompute taxes on a journal change, and neither should we "
            "as long as no 'no_tax' journal was involved.",
        )

    # ------------------------------------------------------------------
    # A 'no_tax' journal never carries taxes
    # ------------------------------------------------------------------

    def test_no_tax_journal_drops_the_product_taxes(self):
        invoice = self._create_invoice(self.no_tax_sale_journal)
        self.assertFalse(invoice.invoice_line_ids.tax_ids)
        self.assertEqual(invoice.amount_total, 100.0)

    def test_no_tax_journal_drops_the_supplier_taxes(self):
        bill = self._create_invoice(self.no_tax_purchase_journal, move_type="in_invoice")
        self.assertFalse(bill.invoice_line_ids.tax_ids)

    def test_no_tax_journal_ignores_the_fiscal_position(self):
        """partner_b maps tax_sale_a to tax_sale_b, we still want nothing."""
        invoice = self._create_invoice(self.no_tax_sale_journal, partner=self.partner_b)
        self.assertEqual(invoice.fiscal_position_id, self.fiscal_pos_a)
        self.assertFalse(invoice.invoice_line_ids.tax_ids)

    def test_no_tax_journal_drops_explicitly_written_taxes(self):
        """Sales and purchase orders push their own taxes, bypassing the compute."""
        invoice = self._create_invoice(
            self.no_tax_sale_journal,
            line_vals={"tax_ids": [Command.set(self.tax_sale_a.ids)]},
        )
        self.assertFalse(invoice.invoice_line_ids.tax_ids)

    def test_no_tax_journal_drops_taxes_added_afterwards(self):
        invoice = self._create_invoice(self.no_tax_sale_journal)

        invoice.invoice_line_ids.tax_ids = [Command.set(self.tax_sale_a.ids)]

        self.assertFalse(invoice.invoice_line_ids.tax_ids)

    def test_no_tax_journal_drops_taxes_of_a_line_added_afterwards(self):
        invoice = self._create_invoice(self.no_tax_sale_journal)

        invoice.write(
            {
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "quantity": 1,
                            "price_unit": 50.0,
                            "tax_ids": [Command.set(self.tax_sale_a.ids)],
                        }
                    )
                ]
            }
        )

        self.assertFalse(invoice.invoice_line_ids.tax_ids)

    # ------------------------------------------------------------------
    # Switching the journal back and forth
    # ------------------------------------------------------------------

    def test_switching_to_a_no_tax_journal_drops_the_taxes(self):
        invoice = self._create_invoice(self.sale_journal)
        self.assertEqual(invoice.invoice_line_ids.tax_ids, self.tax_sale_a)

        invoice.journal_id = self.no_tax_sale_journal

        self.assertFalse(invoice.invoice_line_ids.tax_ids)
        self.assertTrue(invoice.taxes_removed_by_journal)
        self.assertEqual(invoice.amount_total, 100.0)

    def test_switching_back_restores_the_standard_taxes(self):
        invoice = self._create_invoice(self.sale_journal)
        invoice.journal_id = self.no_tax_sale_journal
        self.assertFalse(invoice.invoice_line_ids.tax_ids)

        invoice.journal_id = self.sale_journal

        self.assertEqual(invoice.invoice_line_ids.tax_ids, self.tax_sale_a)
        self.assertFalse(invoice.taxes_removed_by_journal)

    def test_switching_back_applies_the_fiscal_position_mapping(self):
        invoice = self._create_invoice(self.sale_journal, partner=self.partner_b)
        self.assertEqual(invoice.invoice_line_ids.tax_ids, self.tax_sale_b)
        invoice.journal_id = self.no_tax_sale_journal
        self.assertFalse(invoice.invoice_line_ids.tax_ids)

        invoice.journal_id = self.sale_journal

        self.assertEqual(invoice.invoice_line_ids.tax_ids, self.tax_sale_b)

    # ------------------------------------------------------------------
    # The same, through the form view
    # ------------------------------------------------------------------

    def test_onchange_journal_id_both_ways(self):
        move_form = Form(
            self.env["account.move"]
            .with_company(self.company_data["company"])
            .with_context(default_move_type="out_invoice")
        )
        move_form.partner_id = self.partner_a
        move_form.journal_id = self.sale_journal
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_a
            line_form.price_unit = 100.0

        move_form.journal_id = self.no_tax_sale_journal
        invoice = move_form.save()
        self.assertFalse(invoice.invoice_line_ids.tax_ids)

        move_form = Form(invoice)
        move_form.journal_id = self.sale_journal
        invoice = move_form.save()
        self.assertEqual(invoice.invoice_line_ids.tax_ids, self.tax_sale_a)

    # ------------------------------------------------------------------
    # Out of scope documents
    # ------------------------------------------------------------------

    def test_sections_and_notes_are_left_alone(self):
        invoice = self._create_invoice(self.no_tax_sale_journal)
        invoice.write(
            {
                "invoice_line_ids": [
                    Command.create({"display_type": "line_section", "name": "A section"}),
                    Command.create({"display_type": "line_note", "name": "A note"}),
                ]
            }
        )
        invoice.journal_id = self.sale_journal

        product_lines = invoice.invoice_line_ids.filtered(
            lambda line: line.display_type == "product"
        )
        self.assertEqual(product_lines.tax_ids, self.tax_sale_a)

    def test_posted_invoice_is_left_alone(self):
        invoice = self._create_invoice(self.sale_journal)
        invoice.action_post()

        invoice._apply_journal_tax_policy()

        self.assertEqual(invoice.invoice_line_ids.tax_ids, self.tax_sale_a)

    # ------------------------------------------------------------------
    # Regression: the journal switched twice before saving
    # ------------------------------------------------------------------

    def test_journal_toggled_twice_on_a_new_invoice(self):
        """Switch away and back on an invoice that was never saved.

        The flag that remembers we emptied the taxes has to survive the
        onchange round trip, which is why it sits in the form view as an
        invisible field.
        """
        move_form = Form(
            self.env["account.move"]
            .with_company(self.company_data["company"])
            .with_context(default_move_type="out_invoice")
        )
        move_form.partner_id = self.partner_a
        move_form.journal_id = self.sale_journal
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_a
            line_form.price_unit = 100.0

        move_form.journal_id = self.no_tax_sale_journal
        move_form.journal_id = self.sale_journal
        invoice = move_form.save()

        self.assertEqual(invoice.invoice_line_ids.tax_ids, self.tax_sale_a)
        self.assertFalse(invoice.taxes_removed_by_journal)

    def test_journal_toggled_twice_on_a_saved_invoice(self):
        """Same round trip, starting from an invoice that already exists."""
        invoice = self._create_invoice(self.sale_journal)

        move_form = Form(invoice)
        move_form.journal_id = self.no_tax_sale_journal
        move_form.journal_id = self.sale_journal
        invoice = move_form.save()

        self.assertEqual(invoice.invoice_line_ids.tax_ids, self.tax_sale_a)
        self.assertFalse(invoice.taxes_removed_by_journal)
