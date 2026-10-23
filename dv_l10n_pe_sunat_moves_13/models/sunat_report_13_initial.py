from odoo import fields, models


class SunatReport13Initial(models.Model):
    _name = 'sunat.report.13.initial'
    _description = 'Saldo inicial del Registro de Inventario Permanente Valorizado'
    _order = 'product_id'

    period = fields.Char(string="Periodo")
    start_date = fields.Date(string='Fecha Inicio')
    end_date = fields.Date(string='Fecha Fin')

    product_id = fields.Many2one('product.product', string="Producto")
    product_cost = fields.Float(string="Costo unitario")
    quantity_on_hand = fields.Float(string="Cantidad a mano")
    total_value = fields.Float(string='Valor total')
