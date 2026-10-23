from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _ple_13_guide_number(self):
        """Numero de la guia de remision remitente emitida para este traslado.

        El campo lo agrega el modulo de guias electronicas del cliente; se lee
        solo si existe para no depender de ese modulo.
        """
        self.ensure_one()
        if 'serial_referral_guide' not in self._fields:
            return False
        return self.serial_referral_guide or False
