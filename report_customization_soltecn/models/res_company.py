from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError, AccessError

class ResCompany(models.Model):
    _inherit = 'res.company'

    max_column_logo = fields.Integer(string="Columnas ocupadas logo", default=2)
    space_body_header = fields.Integer(string="Espaciado de cuerpo a cabecera", default=0)
    padding_top_layout = fields.Integer(string="Padding top layout", default=1)

class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    max_column_logo = fields.Integer(related='company_id.max_column_logo', readonly=False)
    space_body_header = fields.Integer(related="company_id.space_body_header", readonly=False)
    padding_top_layout = fields.Integer(related="company_id.padding_top_layout", readonly=False)