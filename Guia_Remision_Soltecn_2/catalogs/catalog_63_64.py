from odoo import models, fields, api

class CatalogTmpl(models.Model):
    _name = 'catalog.tmpl.aero.port'
    _description = 'Catalog template aero-port'

    active = fields.Boolean(string='Active', default=True)
    code = fields.Char(string='Código', size=3, index=True, required=True)
    name = fields.Char(string='Nombre', index=True, required=True)
    ubigeo = fields.Char(string="Ubigeo", size=6, required=True)
    department = fields.Char(string="Departamento", required=True)
    province = fields.Char(string="Provincia", required=True)
    district = fields.Char(string="Distrito", required=True)
    address = fields.Char(string="Dirección", required=True)

class Catalog63(models.Model):
    _name = "catalog.63"
    _description = 'Principales puertos en el Perú'
    _inherit = 'catalog.tmpl.aero.port'

    name = fields.Char(string='Nombre puerto')

class Catalog64(models.Model):
    _name = "catalog.64"
    _description = 'Principales aeropuertos en el Perú'
    _inherit = 'catalog.tmpl.aero.port'

    name = fields.Char(string='Nombre aeropuerto')

    SELECTION_TYPE_AEROPORT = [
        ('nacional','Nacional'),
        ('internacional','Internacional'),
    ]
    type_aeroport = fields.Selection(SELECTION_TYPE_AEROPORT, string="Tipo", required=False)