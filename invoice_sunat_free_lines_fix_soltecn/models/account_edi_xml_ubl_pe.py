from odoo import models

from odoo.addons.invoice_sunat_soltecn_v16.models.account_edi_xml_ubl_pe import FREE_AFFECTATION_REASONS

FREE_TAX_CODE = '9996'


class AccountEdiXmlUBLPE(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl_pe'

    def _export_invoice_vals(self, invoice):
        # EXTENDS invoice_sunat_soltecn_v16
        vals = super()._export_invoice_vals(invoice)

        for tax_total in vals['vals'].get('tax_total_vals', []):
            # Solo tributos SUNAT: fuera los hijos sin código de los grupos "Libre Final".
            tax_total['tax_subtotal_vals'] = [
                sub for sub in tax_total.get('tax_subtotal_vals', [])
                if sub['tax_category_vals']['tax_scheme_vals'].get('id')
            ]
            # El total de impuestos del comprobante no incluye el tributo gratuito.
            if invoice.l10n_pe_edi_legend != '1002':
                tax_total['tax_amount'] = sum(
                    sub['tax_amount'] for sub in tax_total['tax_subtotal_vals']
                    if sub['tax_category_vals']['tax_scheme_vals'].get('id') != FREE_TAX_CODE
                )
        return vals

    def _get_invoice_monetary_total_vals(self, invoice, taxes_vals, line_extension_amount, allowance_total_amount, charge_total_amount):
        # EXTENDS invoice_sunat_soltecn_v16
        vals = super()._get_invoice_monetary_total_vals(invoice, taxes_vals, line_extension_amount, allowance_total_amount, charge_total_amount)

        # Las líneas gratuitas no forman parte del valor de venta.
        amount_free = sum(
            line.price_subtotal
            for line in invoice.invoice_line_ids
            if line.display_type == 'product' and line.l10n_pe_edi_affectation_reason in FREE_AFFECTATION_REASONS
        )
        vals['line_extension_amount'] -= amount_free
        vals['tax_exclusive_amount'] -= amount_free
        return vals

    def _get_invoice_line_tax_totals_vals_list(self, line, taxes_vals):
        # EXTENDS invoice_sunat_soltecn_v16
        # El módulo base toma el código SUNAT del primer impuesto de cada grupo de
        # detalle. En los grupos "Libre Final" ese impuesto puede ser un hijo sin
        # código ("Substraer base", "... Gasto"). Se descartan los detalles sin
        # ningún impuesto con código y, en el resto, el impuesto con código va primero.
        tax_details = {}
        for key, tax_detail_vals in taxes_vals['tax_details'].items():
            coded = [td for td in tax_detail_vals['taxes_data'] if td['tax'].l10n_pe_edi_tax_code]
            if not coded:
                continue
            not_coded = [td for td in tax_detail_vals['taxes_data'] if not td['tax'].l10n_pe_edi_tax_code]
            tax_details[key] = {**tax_detail_vals, 'taxes_data': coded + not_coded}

        vals_list = super()._get_invoice_line_tax_totals_vals_list(line, {**taxes_vals, 'tax_details': tax_details})

        # En líneas gratuitas el total de la línea es la suma de los tributos informados.
        if line.l10n_pe_edi_affectation_reason in FREE_AFFECTATION_REASONS:
            for vals in vals_list:
                vals['tax_amount'] = sum(sub['tax_amount'] for sub in vals['tax_subtotal_vals'])
        return vals_list
