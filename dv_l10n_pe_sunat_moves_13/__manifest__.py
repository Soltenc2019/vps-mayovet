{
    'name': "Campos Base Registro de Inventario Permanente Valorizado SUNAT Perú",

    'summary': """
        Campos y datos base del formato 13.1 (Registro de Inventario
        Permanente Valorizado) alimentados desde las capas de valoración
        de inventario, sin depender de asientos contables.
    """,

    'author': 'Develogers',
    'website': 'https://develogers.com',
    'support': 'especialistas@develogers.com',
    'license': 'Other proprietary',

    'category': 'Localization',
    'version': '17.0.1.0.0',

    # Solo modulos estandar que el cliente ya tiene instalados:
    # - stock_account: capas de valoracion (cantidad y costo de cada movimiento)
    # - sale_stock / purchase_stock: enlace movimiento -> pedido -> comprobante
    # - l10n_pe_edi: codigo SUNAT de unidad de medida (uom), tipo de documento
    #   (l10n_latam) y codigo UNSPSC del producto (product_unspsc)
    'depends': [
        'stock_account',
        'sale_stock',
        'purchase_stock',
        'l10n_pe_edi',
    ],

    'data': [
        'security/ir.model.access.csv',
        'security/sunat_report_13_security.xml',
        'views/product_template_views.xml',
        'views/stock_picking_type_views.xml',
        'views/sunat_report_13_views.xml',
    ],

    'auto_install': False,
    'application': False,
    'installable': True,
}
