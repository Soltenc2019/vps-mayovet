from odoo import api, fields, models, _

class StockPackageType(models.Model):
    _inherit = "stock.package.type"

    # measure_unit_code = fields.Char(string="Código unidad de medida", help="Catálogo 03")
    # measure_unit_code_dam_ds = fields.Char(string="Código unidad de medida DAM o DS", help="Catálogo 65")
    package_type_uom = fields.Many2one('uom.uom', "Unidad Medida")
    package_type_weight = fields.Float(string="Peso tipo paquete")
    package_type_default = fields.Boolean(string="Tipo de paquete por defecto", help="Al crear un paquete este será el por defecto")