{
    'name': 'Codex Invoice Sequential Approvals System',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Multi-stage approval workflow for Accounting Invoices & Payments',
    'author': 'Codex',
    'depends': ['account', 'web'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
