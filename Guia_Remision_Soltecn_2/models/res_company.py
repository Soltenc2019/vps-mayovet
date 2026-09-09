from datetime import date, datetime, timedelta

from odoo import models, fields, api, _
from odoo.fields import Date, Datetime
from odoo.exceptions import ValidationError, UserError, AccessError

class ResCompany(models.Model):
    _inherit = 'res.company'

    grant_type = fields.Char(string="Grant type", default="password", readonly=True)
    scope = fields.Char(string="Scope", default="https://api-cpe.sunat.gob.pe", readonly=True)
    client_id = fields.Char(string="Client id", default=False, company_dependent=True)
    client_secret = fields.Char(string="Client secret", default=False, company_dependent=True)
    usuario_sol = fields.Char(string="Usuario Sol", default=False, company_dependent=True)
    contrasenia_sol = fields.Char(string="Contraseña Sol", default=False, company_dependent=True)
    access_token = fields.Char(string="Acceso Token Gre", default=False, company_dependent=True)
    # Weiht specify
    specify_weight = fields.Boolean(string="Especificar peso automáticamente", default=True, company_dependent=True)
    specify_weight_by_bultos_paletas = fields.Boolean(string="Especificar por bulto o paleta", default=False, company_dependent=True)
    # picking_type_in_package_default_id = fields.Many2one('stock.package.type')
    # NEW