from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    taxes_removed_by_journal = fields.Boolean(
        string="Taxes Removed by Journal",
        copy=False,
        help="Technical flag telling that the taxes of this order were removed "
        "because of the tax policy of its invoicing journal. It is what lets us "
        "restore the standard taxes if the journal is changed back.",
    )

    def _excludes_taxes(self):
        """Whether taxes must be kept off the lines of this order.

        Only a journal picked by hand counts. When the field is left empty the
        invoice ends up on the sales journal with the lowest sequence, and we
        would rather keep the standard behaviour than guess which one that is.
        """
        self.ensure_one()
        return bool(self.journal_id) and self.journal_id._excludes_taxes()

    def _taxable_order_lines(self):
        self.ensure_one()
        return self.order_line.filtered(lambda line: not line.display_type)

    def _apply_journal_tax_policy(self):
        """Align the taxes of the lines with the policy of the invoicing journal.

        Same deal as ``account.move``: we drop the taxes when the journal
        forbids them and put the standard ones back when moving to a journal
        that allows them again. The restore only happens on orders we emptied
        ourselves, so switching between two regular journals keeps behaving the
        way Odoo does out of the box and does not wipe taxes a salesperson
        edited by hand.
        """
        for order in self:
            lines = order._taxable_order_lines()
            if order._excludes_taxes():
                to_clear = lines.filtered("tax_id")
                if to_clear:
                    to_clear.tax_id = False
                if not order.taxes_removed_by_journal:
                    order.taxes_removed_by_journal = True
            elif order.taxes_removed_by_journal:
                # Our own override of this compute leaves the standard values
                # alone now that the journal allows taxes again.
                lines._compute_tax_id()
                order.taxes_removed_by_journal = False

    @api.onchange("journal_id")
    def _onchange_journal_id_tax_policy(self):
        self._apply_journal_tax_policy()

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders._apply_journal_tax_policy()
        return orders

    def write(self, vals):
        res = super().write(vals)
        if "journal_id" in vals:
            self._apply_journal_tax_policy()
        return res
