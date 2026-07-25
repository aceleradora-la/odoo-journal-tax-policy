from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    tax_policy = fields.Selection(
        selection=[
            ("standard", "Standard"),
            ("no_tax", "Never apply taxes"),
        ],
        string="Tax Policy",
        default="standard",
        required=True,
        help="Only meaningful on Sales and Purchase journals.\n\n"
        "Standard: taxes come from the product and are mapped by the fiscal "
        "position, exactly as Odoo does out of the box.\n\n"
        "Never apply taxes: the lines of the documents issued through this "
        "journal are always kept without taxes, whatever the product, the "
        "account or the fiscal position say.",
    )

    def _excludes_taxes(self):
        """Whether this journal forbids taxes on the lines of its documents."""
        self.ensure_one()
        return self.tax_policy == "no_tax" and self.type in ("sale", "purchase")
