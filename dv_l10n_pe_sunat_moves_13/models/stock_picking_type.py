from odoo import fields, models

from .sunat_tables import TABLA_12


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    l10n_pe_ple_operation_type = fields.Selection(
        TABLA_12, string='Tipo de operación SUNAT',
        help="Tabla 12 de SUNAT (campo 14 del 13.1). Si se deja vacío se "
             "deduce del movimiento: venta, compra, devolución o ajuste de "
             "inventario. Las devoluciones y los ajustes de inventario se "
             "deducen siempre, aunque este campo esté lleno.")
