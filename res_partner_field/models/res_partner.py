from odoo import api, fields, models

class ResPartnerCustom(models.Model):
    _inherit = 'res.partner'
    
    type_contact = fields.Selection(
        selection=[('commercial', 'Comercial'), ('internal', 'Interno'),],
        string="Tipo de contacto",
        default='commercial',
        store=True
    )