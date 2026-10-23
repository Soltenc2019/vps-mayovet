{
    'name': """
		PLE 13 - Registro de Inventario Permanente Valorizado Sunat Perú TXT XLS
    """,

    'summary': """
        Permite generar el libro 13.1 del PLE de Sunat Perú
        (Registro de Inventario Permanente Valorizado) en TXT y XLS.
    """,

    'author': 'Develogers',
    'website': 'https://develogers.com',
    'support': 'especialistas@develogers.com',
    'license': 'Other proprietary',

    'category': 'Localization',
    'version': '17.0.1.0.0',

    'depends': [
        'dv_l10n_pe_sunat_moves_13',
    ],

    'data': [
        'security/ir.model.access.csv',
        'security/ple_report_security.xml',
        'views/ple_report_views.xml',
        'views/menuitem_views.xml',
    ],

    'auto_install': False,
    'application': True,
    'installable': True,
}
