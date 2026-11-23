{
    'name': 'Redondear costos de productos (uso único)',
    'version': '18.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Redondea a N decimales los costos ya guardados. Instalar, usar y desinstalar.',
    'description': """
Addon de uso único (Solyman)
============================
Redondea el campo Costo (standard_price) de productos/variantes (y opcionalmente
de lotes) que fueron guardados con muchos decimales por el costo promedio.

* Inventario > Configuración > Redondear costos (uso único)
* Vista previa antes de aplicar.
* NO genera capas de valoración ni asientos contables (disable_auto_svl).
* Después de usarlo se puede desinstalar: no deja campos ni datos propios.
""",
    'author': 'Solyman',
    'license': 'LGPL-3',
    'depends': ['stock_account'],
    'data': [
        'views/round_cost_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
}
