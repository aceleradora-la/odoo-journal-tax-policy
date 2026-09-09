{
    "name": "Journal Tax Policy - Sales",
    "version": "17.0.1.0.0",
    "category": "Sales/Sales",
    "summary": "Apply the tax policy of the invoicing journal to sales orders",
    "author": "aceleradora.la",
    "website": "https://aceleradora.la",
    "license": "AGPL-3",
    "depends": ["account_journal_tax_policy", "sale"],
    "data": [
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "application": False,
    # Bridge module: it shows up on its own once both sides are installed, so
    # account_journal_tax_policy never has to depend on sale.
    "auto_install": True,
}
