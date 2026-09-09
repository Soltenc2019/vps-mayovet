{
    'name': 'Document edi invalid manage Soltecn',
    'version': '17.0.0.0.0',
    'summary': 'Document edi invalid manage',
    'category': 'Invoice',
    'author': 'Solyman',
    'maintainer': 'Solyman',
    'company': 'Solyman',
    'website': 'https://www.Soltecn.com',
    'depends': [
        # 'invoice_sunat_soltecn_v16',
        'account_edi',
        'l10n_pe_edi',
        ],
    'qweb': [],
    'data': [
        # 'security/ir.model.access.csv',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'license': 'AGPL-3',
}