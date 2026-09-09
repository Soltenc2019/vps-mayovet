from odoo import api, fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def _get_aggregated_properties(self, move_line=False, move=False):
        """Odoo 18 extrajo el cálculo de las claves de agrupación a este método.

        Añadimos aquí los datos extra que consume el reporte de guía de
        remisión (código interno, descripción del movimiento, lotes y peso).
        """
        res = super()._get_aggregated_properties(move_line=move_line, move=move)
        move = move or move_line.move_id
        res.update({
            'default_code': move.product_id.default_code,
            'product_name_only': move.description_picking,
            'lots': '',
            'weight_total': 0.0,
        })
        return res

    def _get_aggregated_product_quantities(self, **kwargs):
        """Acumula lotes y peso total por línea agregada."""
        aggregated_move_lines = super()._get_aggregated_product_quantities(**kwargs)
        if not self.lot_id:
            return aggregated_move_lines
        for move_line in self:
            if kwargs.get('except_package') and move_line.result_package_id:
                continue
            line_key = self._get_aggregated_properties(move_line=move_line)['line_key']
            line = aggregated_move_lines.get(line_key)
            if not line:
                continue
            if move_line.lot_id:
                line['lots'] += '%s, ' % move_line.lot_id.name
            line['weight_total'] += move_line.product_id.weight * move_line.quantity
        return aggregated_move_lines
