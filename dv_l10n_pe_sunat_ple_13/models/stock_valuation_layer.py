from odoo import models

from odoo.addons.dv_l10n_pe_sunat_moves_13.models.sunat_tables import OPERACIONES_CON_DOCUMENTO

from .ple_format import format_positive_value, product_ple_fields, product_ple_tail


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    def ple_13_01_fields(self, report, balance_quantity, balance_cost,
                         extra_cost=0.0, correlative=1, tz=None):
        """Genera la tupla del formato 13.1 para esta capa de valoracion.

        extra_cost: costo sin unidades (p. ej. diferencia de precio de la
        factura de compra) atribuido a esta capa. Ver
        ple.report.13._split_13_01_lines().
        correlative: posicion de la capa dentro de su CUO (campo 3).

        Devuelve (tupla, saldo_cantidad, saldo_costo, sin_documento), donde
        sin_documento indica una operacion 01-06 sin comprobante ni guia.
        """
        self.ensure_one()
        tz = tz or report._ple_13_tz()
        quantity = self.quantity
        cost = self.value + extra_cost

        # El sentido lo dan las unidades, no el costo: una recepcion a costo
        # cero sigue siendo un ingreso. Solo una capa sin unidades (ajuste de
        # valor) se clasifica por el signo del costo.
        incoming = quantity > 0 or (not quantity and cost > 0)
        if incoming:
            in_quantity, in_cost = abs(quantity), cost
            out_quantity, out_cost = 0, 0
        else:
            in_quantity, in_cost = 0, 0
            out_quantity, out_cost = -abs(quantity), cost

        balance_quantity += in_quantity + out_quantity
        balance_cost += in_cost + out_cost

        in_unit_cost = in_cost / in_quantity if in_quantity else 0
        out_unit_cost = out_cost / out_quantity if out_quantity else 0
        balance_unit_cost = balance_cost / balance_quantity if balance_quantity else 0

        operation = self._ple_13_operation_type(incoming)
        document = self._ple_13_document(incoming, report.end_date, tz) or {}
        missing_document = operation in OPERACIONES_CON_DOCUMENTO and not document

        ple_13_01 = [
            # 1 Periodo
            report.period,
            # 2 CUO: la operacion (albaran) que origino la capa
            self._ple_13_cuo(),
            # 3 Correlativo de la capa dentro de su CUO; 'M' = movimiento del mes
            'M' + str(correlative).rjust(9, '0'),
            # 4 Codigo de establecimiento anexo
            report.establishment_code,
            # 5-9 Catalogo, tipo de existencia, codigo propio y UNSPSC
            *product_ple_fields(self.product_id),
            # 10 Fecha de emision del documento (o del movimiento si no hay)
            document.get('date') or self._ple_13_date(tz),
            # 11-13 Tipo, serie y numero del documento; '00' / '0' si no hay
            document.get('type') or '00',
            document.get('serie') or '0',
            document.get('number') or '0',
            # 14 Tipo de operacion (Tabla 12)
            operation,
            # 15-17 Descripcion, unidad de medida y metodo de valuacion
            *product_ple_tail(self.product_id),
            # 18 Cantidad de unidades fisicas del bien ingresado
            format_positive_value(in_quantity, 8, True),
            # 19 Costo unitario del bien ingresado
            format_positive_value(in_unit_cost, 8, True),
            # 20 Costo total del bien ingresado
            format_positive_value(in_cost, 2, True),
            # 21 Cantidad de unidades fisicas del bien retirado
            format_positive_value(out_quantity, 8, False),
            # 22 Costo unitario del bien retirado
            format_positive_value(out_unit_cost, 8, True),
            # 23 Costo total del bien retirado
            format_positive_value(out_cost, 2, False),
            # 24 Cantidad de unidades fisicas del saldo final
            format_positive_value(balance_quantity, 8, False),
            # 25 Costo unitario del saldo final
            format_positive_value(balance_unit_cost, 8, True),
            # 26 Costo total del saldo final
            format_positive_value(balance_cost, 2, False),
            # 27 Estado de la operacion
            '1',
            # 28 Vacio: al unir con '|' cierra el registro con el palote final
            '',
        ]
        return ple_13_01, balance_quantity, balance_cost, missing_document
