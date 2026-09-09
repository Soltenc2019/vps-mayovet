{
    'name': 'Force CDR Consultation',
    'version': '18.0.0.0.0',
    'summary': 'Force CDR Consultation Soltecn',
    'category': '',
    'author': 'Solyman',
    'maintainer': 'Solyman',
    'company': 'Solyman',
    'website': 'https://www.Soltecn.com',
    "depends": [
        'invoice_sunat_soltecn_v16',
        'account_edi',
        'l10n_pe_edi'
        # 'crm'
        # "point_of_sale"
        ],
    'data': [
        # 'views/crm_lead_view.xml',
        'views/account_move_views.xml',
        ],
    'installable': True,
    'license': 'AGPL-3',
}