from odoo import Command, api, fields, models

# ``line_subsection`` only exists from Odoo 19 on, listing it here is harmless
# on the older series and keeps a single code base across 17, 18 and 19.
NON_TAXABLE_DISPLAY_TYPES = ("line_section", "line_subsection", "line_note")


class AccountMove(models.Model):
    _inherit = "account.move"

    taxes_removed_by_journal = fields.Boolean(
        string="Taxes Removed by Journal",
        copy=False,
        readonly=True,
        help="Technical flag telling that the taxes of this document were "
        "removed because of the tax policy of its journal. It is what lets us "
        "restore the standard taxes if the journal is changed back.",
    )

    def _excludes_taxes(self):
        """Whether taxes must be kept off the lines of this document."""
        self.ensure_one()
        if not self.journal_id or not self.journal_id._excludes_taxes():
            return False
        return self.is_sale_document(include_receipts=True) or self.is_purchase_document(
            include_receipts=True
        )

    def _taxable_invoice_lines(self):
        self.ensure_one()
        return self.invoice_line_ids.filtered(
            lambda line: line.display_type not in NON_TAXABLE_DISPLAY_TYPES
        )

    def _apply_journal_tax_policy(self):
        """Align the taxes of the lines with the policy of the journal.

        Both directions are covered: dropping the taxes when the journal
        forbids them, and putting the standard ones back when we move to a
        journal that allows them again. The restore only happens on documents
        we emptied ourselves, so switching between two regular journals keeps
        behaving the way Odoo does out of the box -- in particular it does not
        wipe taxes an accountant edited by hand.
        """
        for move in self:
            if move.state != "draft":
                continue
            if move._excludes_taxes():
                lines = move._taxable_invoice_lines().filtered("tax_ids")
                if lines:
                    lines.tax_ids = [Command.clear()]
                if not move.taxes_removed_by_journal:
                    move.taxes_removed_by_journal = True
            elif move.taxes_removed_by_journal:
                for line in move._taxable_invoice_lines():
                    line.tax_ids = line._get_computed_taxes()
                move.taxes_removed_by_journal = False

    @api.onchange("journal_id")
    def _onchange_journal_id_tax_policy(self):
        self._apply_journal_tax_policy()

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        moves._apply_journal_tax_policy()
        return moves

    def write(self, vals):
        res = super().write(vals)
        if "journal_id" in vals:
            self._apply_journal_tax_policy()
        return res
