{
    "name": "Journal Tax Policy",
    "version": "18.0.1.0.0",
    "category": "Accounting/Accounting",
    "summary": "Decide per sales/purchase journal whether its documents carry taxes",
    "author": "Aceleradora-Latam",
    "website": "https://github.com/aceleradora-la/odoo-journal-tax-policy",
    "license": "AGPL-3",
    "depends": ["account"],
    "data": [
        "views/account_journal_views.xml",
        "views/account_move_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
