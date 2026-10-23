import datetime
import io
import zipfile
from base64 import b64encode, encodebytes
from collections import defaultdict

import xlsxwriter

from odoo import fields, models
from odoo.exceptions import UserError

from .ple_headers import PLE_13_1_HEADER


class PleReport13(models.Model):
    _name = 'ple.report.13'
    _description = 'PLE 13 - Estructura del Registro de Inventario Permanente Valorizado'
    _inherit = 'sunat.report.13'

    # Se redeclaran con tablas propias: heredados tal cual, compartirian la
    # tabla relacional con sunat.report.13.
    line_01_ids = fields.Many2many(
        'stock.valuation.layer', 'ple_report_13_svl_rel', 'report_id', 'layer_id',
        string='Movimientos valorizados', readonly=True)
    sunat_report_13_initial_ids = fields.Many2many(
        'sunat.report.13.initial', 'ple_report_13_initial_rel', 'report_id', 'initial_id',
        string='Saldos iniciales', readonly=True)

    ple_txt_01_binary = fields.Binary(string='TXT 13.1', readonly=True)
    ple_txt_01_filename = fields.Char(readonly=True)
    ple_xls_01_binary = fields.Binary(string='XLS 13.1', readonly=True)
    ple_xls_01_filename = fields.Char(readonly=True)
    ple_txt_zip_binary = fields.Binary(string='Archivo ZIP', readonly=True)
    ple_txt_zip_filename = fields.Char(string='Nombre del ZIP', readonly=True)

    l10n_pe_ple_warning = fields.Text(
        string='Observaciones', readonly=True, copy=False,
        help="Situaciones que el archivo no muestra a simple vista: saldos "
             "negativos (se declaran en valor absoluto) y ventas o compras sin "
             "comprobante ni guía (SUNAT exige documento para las operaciones "
             "01 a 06).")

    # ------------------------------------------------------------------
    # Lineas del Kardex
    # ------------------------------------------------------------------

    def _sort_13_01_lines(self, layers):
        """Orden cronologico estricto: el saldo corrido depende de el."""
        return layers.sorted(key=lambda l: (l.create_date, l.id))

    def _split_13_01_lines(self, layers):
        """Atribuye los costos sin unidades a la capa que encarecieron.

        Una diferencia de precio en la factura de compra (o un costo en
        destino) genera una capa con importe pero SIN unidades, enlazada por
        stock_valuation_layer_id a la capa de la recepcion. Emitirla como
        fila propia daria cantidad 0 con costo; se suma a la fila de la
        recepcion, que es donde pertenece.

        Si la recepcion cayo en un periodo anterior no se puede fusionar, y
        se emite como fila propia de ajuste de valor.

        Devuelve (capas_a_emitir, {id_de_capa: costo_extra}).
        """
        value_only = layers.filtered(lambda l: not l.quantity and l.stock_valuation_layer_id)
        if not value_only:
            return layers, {}

        movements = layers - value_only
        extra_cost = defaultdict(float)
        orphans = self.env['stock.valuation.layer']
        for layer in value_only:
            if layer.stock_valuation_layer_id in movements:
                extra_cost[layer.stock_valuation_layer_id.id] += layer.value
            else:
                orphans |= layer
        return movements | orphans, extra_cost

    def _correlatives_13_01(self, layers):
        """Campo 3: posicion de cada capa dentro de su CUO, por orden de id."""
        sequence = defaultdict(int)
        correlatives = {}
        for layer in layers.sorted('id'):
            cuo = layer._ple_13_cuo()
            sequence[cuo] += 1
            correlatives[layer.id] = sequence[cuo]
        return correlatives

    def _build_ple_warning(self, negativos, sin_documento):
        lineas = []
        if negativos:
            lineas += [
                "%s producto(s) cierran el periodo con SALDO NEGATIVO." % len(negativos),
                "Se declararon en valor absoluto. Revisar los movimientos de inventario:",
            ]
            for producto, cantidad, costo in sorted(negativos, key=lambda n: n[1]):
                lineas.append("    %-28s %12.4f uds   %12.2f" % (
                    (producto.default_code or producto.display_name or '?')[:28],
                    cantidad, costo))
            lineas.append("")
        if sin_documento:
            lineas += [
                "%s movimiento(s) de venta/compra SIN comprobante ni guía de remisión" % len(sin_documento),
                "emitidos hasta el cierre del periodo. SUNAT rechaza las operaciones",
                "01 a 06 con documento '00'. Emitir o registrar el documento:",
            ]
            for cuo, producto in sorted(set(sin_documento)):
                lineas.append("    %-24s %s" % (cuo, producto))
        return "\n".join(lineas) or False

    def get_values_list(self):
        self.ensure_one()
        tz = self._ple_13_tz()
        values_list = []
        negativos = []
        sin_documento = []

        layers = self.line_01_ids.sudo()
        correlatives = self._correlatives_13_01(layers)
        # Una sola agrupacion por producto: cada capa pertenece a un unico
        # Kardex, asi que ningun movimiento puede imprimirse dos veces.
        layers_by_product = layers.grouped('product_id')

        def emit_kardex(product_layers, balance_quantity, balance_cost):
            product_layers, extra_cost = self._split_13_01_lines(product_layers)
            for layer in self._sort_13_01_lines(product_layers):
                ple_13, balance_quantity, balance_cost, missing = layer.ple_13_01_fields(
                    self, balance_quantity, balance_cost,
                    extra_cost.get(layer.id, 0.0), correlatives[layer.id], tz)
                values_list.append(self._ple_line(ple_13))
                if missing:
                    sin_documento.append((ple_13[1], layer.product_id.display_name))
            return balance_quantity, balance_cost

        # Productos con saldo inicial: la fila del saldo abre el Kardex y los
        # movimientos del periodo continuan ese saldo.
        for correlative, initial in enumerate(self.sunat_report_13_initial_ids.sudo(), 1):
            ple_13, balance_quantity, balance_cost = initial.ple_13_01_fields(self, correlative)
            values_list.append(self._ple_line(ple_13))
            product_layers = layers_by_product.pop(initial.product_id, layers.browse())
            balance_quantity, balance_cost = emit_kardex(
                product_layers, balance_quantity, balance_cost)
            if round(balance_quantity, 8) < 0:
                negativos.append((initial.product_id, balance_quantity, balance_cost))

        # Productos sin saldo inicial: el Kardex arranca en cero.
        for product, product_layers in layers_by_product.items():
            balance_quantity, balance_cost = emit_kardex(product_layers, 0.0, 0.0)
            if round(balance_quantity, 8) < 0:
                negativos.append((product, balance_quantity, balance_cost))

        # Se recalcula en cada generacion: si ya no hay observaciones, queda limpio.
        self.l10n_pe_ple_warning = self._build_ple_warning(negativos, sin_documento)
        return values_list

    # ------------------------------------------------------------------
    # Archivos
    # ------------------------------------------------------------------

    def _ple_value_to_string(self, value):
        if isinstance(value, (datetime.date, datetime.datetime)):
            return value.strftime('%d/%m/%Y')
        if value is False or value is None:
            return ''
        return str(value)

    def _ple_line(self, values):
        return '|'.join(self._ple_value_to_string(value) for value in values)

    def _ple_filename(self, has_data):
        """Nombre del archivo segun SUNAT:
        LE + RUC + AAAA + MM + 00 + 130100 + 00 + operacion(1) + contenido +
        moneda(1 = soles) + generado por el PLE(1).
        """
        self.ensure_one()
        if not self.company_id.vat:
            raise UserError("No se ha configurado el RUC de la compañía.")
        return 'LE%s%s%02d00130100001%s11' % (
            self.company_id.vat, self.year, int(self.month), '1' if has_data else '0')

    def _ple_xlsx(self, values_list, sheet_name):
        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer, {'in_memory': True, 'strings_to_formulas': False})
        sheet = workbook.add_worksheet(sheet_name[:31])
        for column, head in enumerate(PLE_13_1_HEADER):
            sheet.write(0, column, head)
        for row, line in enumerate(values_list, 1):
            for column, value in enumerate(line.split('|')):
                sheet.write(row, column, value)
        workbook.close()
        return encodebytes(buffer.getvalue())

    def _ple_zip(self, txt_filename, txt_content):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as zf:
            zf.writestr(txt_filename, txt_content)
        return encodebytes(buffer.getvalue())

    def generate_report(self):
        for record in self:
            record.update_report()
            values_list = record.get_values_list()
            has_data = bool(values_list)
            filename = record._ple_filename(has_data)
            # SUNAT exige presentar el libro aunque no tenga movimientos.
            txt_content = '\r\n'.join(values_list) if has_data else ' '
            record.write({
                'ple_txt_01_binary': b64encode(txt_content.encode()),
                'ple_txt_01_filename': filename + '.txt',
                'ple_xls_01_binary': record._ple_xlsx(values_list, filename[2:]),
                'ple_xls_01_filename': filename + '.xlsx',
                'ple_txt_zip_binary': record._ple_zip(filename + '.txt', txt_content),
                'ple_txt_zip_filename': 'PLE_13.zip',
            })
        return super().generate_report()

    def action_draft(self):
        super().action_draft()
        self.write({
            'ple_txt_01_binary': False,
            'ple_txt_01_filename': False,
            'ple_xls_01_binary': False,
            'ple_xls_01_filename': False,
            'ple_txt_zip_binary': False,
            'ple_txt_zip_filename': False,
        })
