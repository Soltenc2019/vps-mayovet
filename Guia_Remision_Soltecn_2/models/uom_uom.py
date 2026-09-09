from odoo import api, fields, tools, models, _
from odoo.exceptions import UserError, ValidationError

class UoM(models.Model):
    _inherit = 'uom.uom'

    measure_unit_code_dam_ds = fields.Char(
        'Código unidad de medida DAM o DS',
        help="Código relacionado al producto para identificar la unidad de medida DAM o DS, lo sposibles valores se encuentran en el catalogo 65.")