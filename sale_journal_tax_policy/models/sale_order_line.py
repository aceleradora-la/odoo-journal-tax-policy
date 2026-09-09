from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _compute_tax_ids(self):
        """Give back no tax at all when the invoicing journal forbids them.

        No ``@api.depends`` here on purpose. Odoo collects the dependencies of
        every compute method of the same name along the MRO, so the ones
        declared upstream ('product_id', 'company_id') are kept as they are;
        adding 'order_id.journal_id' would be additive and would make *any*
        journal change recompute -- and wipe -- taxes edited by hand.
        """
        super()._compute_tax_ids()
        for line in self:
            if line.order_id and line.order_id._excludes_taxes():
                line.tax_ids = False

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._drop_taxes_forbidden_by_journal()
        return lines

    def write(self, vals):
        res = super().write(vals)
        if "tax_ids" in vals or "order_id" in vals:
            self._drop_taxes_forbidden_by_journal()
        return res

    def _drop_taxes_forbidden_by_journal(self):
        """Strip taxes that were written explicitly, bypassing the compute.

        ``tax_ids`` is a stored compute with ``readonly=False``, so an explicit
        value always wins over the compute -- think of an import, the external
        API, or a user adding a tax by hand on a line of an order whose journal
        forbids them.
        """
        to_clear = self.filtered(
            lambda line: line.tax_ids
            and not line.display_type
            and line.order_id
            and line.order_id._excludes_taxes()
        )
        if to_clear:
            to_clear.tax_ids = False
