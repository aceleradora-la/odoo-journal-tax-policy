{
    "name": "Journal Tax Policy - Sales",
    "version": "19.0.1.0.0",
    "category": "Sales/Sales",
    "summary": "Apply the tax policy of the invoicing journal to sales orders",
    "author": "Aceleradora-Latam",
    "website": "https://github.com/aceleradora-la/odoo-journal-tax-policy",
    "license": "AGPL-3",
    "depends": ["account_journal_tax_policy", "sale"],
    "installable": True,
    "application": False,
    # Bridge module: it shows up on its own once both sides are installed, so
    # account_journal_tax_policy never has to depend on sale.
    "auto_install": True,
}
