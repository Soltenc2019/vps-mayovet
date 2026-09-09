import operator as py_operator
from ast import literal_eval
from collections import defaultdict
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools import float_is_zero, check_barcode_encoding
from odoo.tools.float_utils import float_round
from odoo.tools.mail import html2plaintext, is_html_empty
from datetime import date, datetime

class Product(models.Model):
    _inherit = "product.product"

    lots_format = fields.Char(string='Lotes')

    lot_ids = fields.Many2many('stock.lot', string='Lotes', compute="_compute_visible_lots")

    # def _compute_visible_lots(self):
    #     for product in self:
    #         lots = self.env['stock.lot'].search([('product_id', '=', product.id)])
    #         lines = []

    #         for lot in lots:
    #             expiry_date = ''
    #             if lot.expiration_date:
    #                 expiry_date = datetime.strftime(lot.expiration_date, '%d/%m/%Y %H:%M:%S')
    #             lines.append(f"{lot.name} : {expiry_date}")

    #         product.lots_format = ', '.join(lines) if lines else ''

    def _compute_visible_lots(self):
        for product in self:
            lots = self.env['stock.lot'].with_context(show_expiry=True).search([('product_id', '=', product.id)])
            product.lot_ids = lots


class StockLot(models.Model):
    _inherit = 'stock.lot'
    
    # def name_get(self):
    #     res = []
    #     show_expiry = self._context.get('show_expiry', False)
    #     for lot in self:
    #         name = lot.name
    #         if show_expiry and lot.expiration_date:
    #             expiry_str = lot.expiration_date.strftime('%d/%m/%Y')
    #             name = f"{lot.name} : {expiry_str}"
    #         res.append((lot.id, name))
    #     return res
    
    def _compute_display_name(self):
        for lot in self:
            show_expiry = self._context.get('show_expiry')
            if show_expiry and lot.expiration_date:
                expiry_str = datetime.strftime(lot.expiration_date, '%d/%m/%Y')
                lot.display_name = f"{lot.name} : {expiry_str}"
            else:
                lot.display_name = lot.name
            