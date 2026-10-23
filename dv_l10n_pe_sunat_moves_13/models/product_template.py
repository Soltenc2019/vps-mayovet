from odoo import fields, models

from .sunat_tables import TABLA_05, COST_METHOD_TO_TABLA_14


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_pe_ple_existence_type = fields.Selection(
        TABLA_05, string='Tipo de existencia (SUNAT)', default='01',
        help="Tabla 5 de SUNAT. Se declara en el campo 6 del Registro de "
             "Inventario Permanente Valorizado (13.1).")


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def get_l10n_table_14_code(self):
        """Codigo Tabla 14 del metodo de valuacion (campo 17), segun el
        metodo de costeo de la categoria del producto."""
        return COST_METHOD_TO_TABLA_14.get(self.cost_method, '9')
