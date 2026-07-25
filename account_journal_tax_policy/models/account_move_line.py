from odoo import Command, api, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_computed_taxes(self):
        """Give back no tax at all when the journal forbids them.

        This is the single funnel Odoo 17 to 19 goes through to derive the
        taxes of an invoice line -- product taxes, account taxes and the
        fiscal position mapping all end up here -- so overriding it covers
        every recomputation path at once.
        """
        self.ensure_one()
        if self.move_id and self.move_id._excludes_taxes():
            return self.env["account.tax"]
        return super()._get_computed_taxes()

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._drop_taxes_forbidden_by_journal()
        return lines

    def write(self, vals):
        res = super().write(vals)
        if "tax_ids" in vals or "move_id" in vals:
            self._drop_taxes_forbidden_by_journal()
        return res

    def _drop_taxes_forbidden_by_journal(self):
        """Strip taxes that were written explicitly, bypassing the compute.

        ``tax_ids`` is a stored compute with ``readonly=False``, so an explicit
        value always wins over :meth:`_get_computed_taxes`. Sales and purchase
        orders push their own taxes when they build the invoice, and so do
        imports and the external API, so the compute never runs for
        those lines.
        """
        to_clear = self.filtered(
            lambda line: line.tax_ids
            and line.display_type == "product"
            and line.move_id.state == "draft"
            and line.move_id._excludes_taxes()
        )
        if to_clear:
            to_clear.tax_ids = [Command.clear()]
