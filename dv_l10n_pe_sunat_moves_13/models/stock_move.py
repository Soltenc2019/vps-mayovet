from odoo import models


def split_document_number(number):
    """Separa 'F001-00000123' en ('F001', '00000123') para los campos 12 y 13.

    Sin guion no hay serie que separar: la serie va '0' (lo que SUNAT pide
    cuando no existe) y el numero completo va al campo 13.
    """
    number = ''.join((number or '').split()).replace('|', '')
    if '-' in number:
        serie, folio = number.split('-', 1)
    else:
        serie, folio = '', number
    return (serie[:20] or '0'), (folio[:20] or '0')


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _ple_13_partner(self):
        self.ensure_one()
        order = self.sale_line_id.order_id or self.purchase_line_id.order_id
        return (order.partner_id or self.picking_id.partner_id).commercial_partner_id

    def _ple_13_is_foreign(self):
        country = self._ple_13_partner().country_id
        return bool(country) and country.code != 'PE'

    def _ple_13_operation_type(self, incoming):
        """Campo 14 (Tabla 12) del movimiento.

        incoming: True si el movimiento ingresa existencias (la capa suma
        unidades), False si las retira.

        Orden de prioridad:
          1. Ajuste de inventario -> 28. Es un hecho del movimiento, no del
             tipo de operacion, asi que no se deja configurar.
          2. Devolucion -> 24 (entra lo que devolvio el cliente) o 25 (sale
             lo que se devuelve al proveedor). Odoo suele usar el mismo tipo
             de operacion del envio original para la devolucion, por eso se
             decide antes que lo configurado.
          3. Lo configurado en el tipo de operacion del albaran.
          4. Venta (01, o 17 si el cliente es del exterior) / compra (02, o
             18 si el proveedor es del exterior), segun el pedido.
          5. 99 Otros.
        """
        self.ensure_one()
        if self.is_inventory:
            return '28'
        if self.origin_returned_move_id:
            return '24' if incoming else '25'
        configured = self.picking_type_id.l10n_pe_ple_operation_type
        if configured:
            return configured
        if self.sale_line_id:
            if incoming:
                return '24'
            return '17' if self._ple_13_is_foreign() else '01'
        if self.purchase_line_id:
            if not incoming:
                return '25'
            return '18' if self._ple_13_is_foreign() else '02'
        return '99'

    def _ple_13_invoice(self, incoming, date_limit):
        """Comprobante publicado que sustenta el movimiento (campos 10 a 13).

        Solo cuentan comprobantes del mismo sentido que el movimiento -una
        salida por venta se sustenta con la factura o boleta, una devolucion
        del cliente con la nota de credito- y emitidos hasta el cierre del
        periodo: SUNAT exige que la fecha del campo 10 no pase del periodo
        informado. Si hay varios, se toma el primero emitido.
        """
        self.ensure_one()
        if self.sale_line_id:
            invoices = self.sale_line_id.invoice_lines.move_id
            move_type = 'out_refund' if incoming else 'out_invoice'
        elif self.purchase_line_id:
            invoices = self.purchase_line_id.invoice_lines.move_id
            move_type = 'in_invoice' if incoming else 'in_refund'
        else:
            return self.env['account.move']
        invoices = invoices.filtered(
            lambda m: m.state == 'posted'
            and m.move_type == move_type
            and m.l10n_latam_document_type_id
            and (m.invoice_date or m.date) <= date_limit)
        return invoices.sorted(lambda m: (m.invoice_date or m.date, m.id))[:1]

    def _ple_13_document(self, incoming, date_limit, tz):
        """Documento que sustenta el movimiento: dict con date, type, serie y
        number, o False si no hay ninguno.

        Primero el comprobante de pago; si no lo hay (p. ej. una entrega que
        se factura el mes siguiente), la guia de remision del traslado, que
        tambien es un documento valido para el 13.1 (Tabla 10, codigo 09).
        """
        self.ensure_one()
        invoice = self._ple_13_invoice(incoming, date_limit)
        if invoice:
            serie, number = split_document_number(invoice.l10n_latam_document_number)
            return {
                'date': invoice.invoice_date or invoice.date,
                'type': invoice.l10n_latam_document_type_id.code,
                'serie': serie,
                'number': number,
            }
        picking = self.picking_id
        guide = picking and picking._ple_13_guide_number()
        if guide:
            serie, number = split_document_number(guide)
            done = picking.date_done or self.date
            return {
                'date': self.env['stock.valuation.layer']._ple_13_to_local_date(done, tz),
                'type': '09',
                'serie': serie,
                'number': number,
            }
        return False
