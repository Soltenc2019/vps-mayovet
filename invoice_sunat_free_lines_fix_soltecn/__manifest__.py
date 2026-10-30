{
    'name': 'Invoice SUNAT - Free Lines Fix',
    'version': '18.0.0.0.0',
    'summary': 'Corrige impuestos y XML de líneas gratuitas con grupos "Libre Final"',
    'description': """
Correcciones sobre invoice_sunat_soltecn_v16 para líneas gratuitas (9996):

* El IGV referencial forzado al 18 % solo se aplica a impuestos 9996 sueltos,
  no a los hijos de los grupos "18% Libre Final" / "0% Libre Final".
* En el XML solo se informan tributos con código SUNAT (se omiten los hijos
  contables "Substraer base" y "... Gasto").
* El TaxTotal del comprobante no incluye el tributo gratuito 9996.
* Las líneas gratuitas no suman al valor de venta (LineExtensionAmount /
  TaxExclusiveAmount).
""",
    'category': 'Invoice',
    'author': 'Solyman',
    'maintainer': 'Solyman',
    'company': 'Solyman',
    'website': 'https://www.Soltecn.com',
    'depends': [
        'invoice_sunat_soltecn_v16',
        'l10n_pe_edi',
    ],
    'data': [],
    'installable': True,
    'license': 'AGPL-3',
}
