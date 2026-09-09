import re
from num2words import num2words

from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tools.float_utils import float_round

class AccountMove(models.Model):
    _inherit = 'account.move'

    available_guide_reference = fields.Many2many("stock.picking", string="Guías disponibles")

    def _get_invoice_values_odoofact(self):
        values = super(AccountMove, self)._get_invoice_values_odoofact()
        if self.available_guide_reference:
            value = getattr(self,'_get_invoice_picking_values_custom_%s' % self._get_ose_supplier())(self.available_guide_reference)
            values["guias"] = value
        return values
    
    def _get_invoice_picking_values_custom_odoofact(self, pick_numbers):
        data = []
        for pick in pick_numbers:
            values = {
                'guia_tipo': 1, # REMITENTE (1) - Transportista (2)
                'guia_serie_numero': pick.serial_referral_guide
            }
            data.append(values)
        return data