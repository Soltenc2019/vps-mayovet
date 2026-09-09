# © 2004-2009 Tiny SPRL (<http://tiny.be>).
# © 2014-2017 Tecnativa - Pedro M. Baeza
# © 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
{
    "name": "Purchase order lines with discounts",
    "author": "Tiny, "
    "Acysos S.L., "
    "Tecnativa, "
    "ACSONE SA/NV,"
    "GRAP,"
    "Odoo Community Association (OCA)",
    "version": "18.0.1.0.0",
    "category": "Purchase Management",
    "website": "https://github.com/OCA/purchase-workflow",
    "summary": "Descuento por defecto de proveedor y descuento en el análisis de compras",
    "description": """
Odoo 18 incorpora de serie el descuento en las líneas de pedido de compra
(`purchase.order.line.discount`), en las tarifas de proveedor
(`product.supplierinfo.discount`), en sus vistas y en el informe PDF del pedido.

Este módulo conserva únicamente lo que el núcleo NO cubre:

* Descuento por defecto configurable en el proveedor
  (`res.partner.default_supplierinfo_discount`) y su propagación a las nuevas
  tarifas de proveedor.
* Sincronización del descuento de la línea de pedido hacia la tarifa de
  proveedor creada automáticamente.
* Campo `discount` en el informe de análisis de compras, con el precio medio
  calculado neto de descuento.
    """,
    "depends": ["purchase_stock"],
    "data": [
        "views/res_partner_view.xml",
    ],
    "license": "AGPL-3",
    "installable": True,
    "images": ["images/purchase_discount.png"],
}
