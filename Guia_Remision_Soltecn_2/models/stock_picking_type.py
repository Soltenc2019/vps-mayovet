from odoo import api, fields, models, _

class PickingTypeCustom(models.Model):
    _inherit = "stock.picking.type"

    use_referrer_guide = fields.Boolean('Usa guía remisión', default=False)
    sequence_prefix_guide = fields.Char('Prefijo guía remisión')
    sequence_number_guide = fields.Integer('Secuencia guía remisión')
    custom_sequence_id = fields.Many2one('ir.sequence', string='Secuencia Guía',copy=False)