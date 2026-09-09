from odoo import _, api, fields, tools, models
from odoo.exceptions import UserError, ValidationError

class StockMove(models.Model):
    _inherit = "stock.move"

    damds_number = fields.Char(string="Numeración de la DAM o DS")
    damds_serie = fields.Char(string="Número de serie en la DAM o DS")
    # stock_group_paleta_bulto = fields.Many2one('stock.group.picking', string="Paleta o bulto")
    # NEW