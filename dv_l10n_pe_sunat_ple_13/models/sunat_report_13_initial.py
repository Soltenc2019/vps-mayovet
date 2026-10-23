from odoo import models

from .ple_format import format_positive_value, product_ple_fields, product_ple_tail


class SunatReport13Initial(models.Model):
    _inherit = 'sunat.report.13.initial'

    def ple_13_01_fields(self, report, correlative=1):
        """Tupla del saldo inicial: primera fila del Kardex del producto."""
        self.ensure_one()
        ple_13_01 = [
            # 1 Periodo
            report.period,
            # 2 CUO del saldo inicial del periodo
            f"SI{report.period[:6]}",
            # 3 Correlativo: 'A' = apertura
            'A' + str(correlative).rjust(9, '0'),
            # 4 Codigo de establecimiento anexo
            report.establishment_code,
            # 5-9 Identicos a los de los movimientos del producto
            *product_ple_fields(self.product_id),
            # 10 Fecha: inicio del periodo
            report.start_date,
            # 11-13 El saldo inicial no tiene documento: '00' / '0' / '0'
            '00',
            '0',
            '0',
            # 14 Tabla 12, codigo 16 = SALDO INICIAL
            '16',
            # 15-17 Descripcion, unidad de medida y metodo de valuacion
            *product_ple_tail(self.product_id),
            # 18-23 Sin ingresos ni retiros
            '0.00', '0.00', '0.00', '0.00', '0.00', '0.00',
            # 24 Cantidad del saldo inicial
            format_positive_value(self.quantity_on_hand, 8, False),
            # 25 Costo unitario del saldo inicial
            format_positive_value(self.product_cost, 8, True),
            # 26 Costo total del saldo inicial
            format_positive_value(self.total_value, 2, False),
            # 27 Estado de la operacion
            '1',
            # 28 Vacio: cierra el registro con el palote final
            '',
        ]
        return ple_13_01, self.quantity_on_hand, self.total_value
