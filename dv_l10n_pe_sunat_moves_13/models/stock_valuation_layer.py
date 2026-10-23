import pytz

from odoo import api, models


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    @api.model
    def _ple_13_to_local_date(self, utc_datetime, tz):
        """Fecha local (Peru) de un datetime guardado en UTC.

        Sin esta conversion un movimiento validado despues de las 19:00 del
        ultimo dia del mes caeria en el mes siguiente.
        """
        if not utc_datetime:
            return False
        return pytz.utc.localize(utc_datetime).astimezone(tz).date()

    def _ple_13_date(self, tz):
        self.ensure_one()
        return self._ple_13_to_local_date(self.create_date, tz)

    def _ple_13_cuo(self):
        """Campo 2: identifica la operacion que origino la capa.

        Sin asientos contables, la operacion es el albaran o el desecho. Los
        movimientos sueltos (ajustes de inventario) comparten una referencia
        generica ("Cantidad de producto actualizada"), asi que se identifican
        por su propio movimiento. Todas las capas de una misma operacion
        comparten CUO; el campo 3 es el que las distingue.
        """
        self.ensure_one()
        move = self.stock_move_id
        if move.picking_id:
            cuo = move.picking_id.name
        elif move.scrap_id:
            cuo = move.scrap_id.name
        elif move:
            cuo = f"MV{move.id}"
        else:
            cuo = f"SVL{self.id}"
        return ''.join(c for c in cuo if c.isalnum() or c in '-_/')[:40]

    def _ple_13_operation_type(self, incoming):
        self.ensure_one()
        if not self.stock_move_id:
            # Revaluacion manual: cambia el costo sin mover unidades.
            return '99'
        return self.stock_move_id._ple_13_operation_type(incoming)

    def _ple_13_document(self, incoming, date_limit, tz):
        self.ensure_one()
        if not self.stock_move_id:
            return False
        return self.stock_move_id._ple_13_document(incoming, date_limit, tz)
