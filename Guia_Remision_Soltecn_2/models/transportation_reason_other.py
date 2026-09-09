from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class TransportationReasonOther(models.Model): 
    _name = 'transportation.reason.other'
    _description = 'Motivo de traslado - Otros'

    name = fields.Char(string="Nombre")
    active = fields.Boolean(string="Activo", default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Nombre de razón debe ser única'),
    ]