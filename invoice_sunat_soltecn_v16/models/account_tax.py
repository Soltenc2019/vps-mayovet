from odoo import api, models, _

# Código de catálogo 07 de SUNAT para la bonificación / transferencia gratuita.
L10N_PE_EDI_BONUS_TAX_CODE = '9996'
# Tasa de IGV que SUNAT exige informar sobre el valor referencial de la
# bonificación, aunque el impuesto no forme parte de los totales del documento.
L10N_PE_EDI_BONUS_IGV_RATE = 0.18


class AccountTax(models.Model):
    _inherit = 'account.tax'

    def _l10n_pe_edi_is_bonus_tax(self):
        """Impuesto usado en las líneas de bonificación (catálogo 07 - 9996)."""
        return bool(self) and all(
            tax.l10n_pe_edi_tax_code == L10N_PE_EDI_BONUS_TAX_CODE for tax in self
        )

    @api.model
    def _add_tax_details_in_base_line(self, base_line, company, rounding_method=None):
        """Odoo 18 sustituye `_compute_taxes_for_single_line` por este método.

        Para las líneas de bonificación SUNAT exige informar el valor
        referencial completo (cantidad x precio, sin aplicar el descuento del
        100 %) y el IGV calculado sobre ese valor, en lugar de la base y el
        impuesto reales de la línea (que son cero).
        """
        super()._add_tax_details_in_base_line(base_line, company, rounding_method=rounding_method)

        taxes_data = base_line['tax_details']['taxes_data']
        if not any(td['tax']._l10n_pe_edi_is_bonus_tax() for td in taxes_data):
            return

        rounding_method = rounding_method or company.tax_calculation_rounding_method
        rate = base_line['rate']
        gross_amount_currency = base_line['quantity'] * base_line['price_unit']
        bonus_tax_amount_currency = gross_amount_currency * L10N_PE_EDI_BONUS_IGV_RATE

        for tax_data in taxes_data:
            if not tax_data['tax']._l10n_pe_edi_is_bonus_tax():
                continue
            base_amount = gross_amount_currency / rate if rate else 0.0
            tax_amount = bonus_tax_amount_currency / rate if rate else 0.0
            if rounding_method == 'round_per_line':
                base_amount = company.currency_id.round(base_amount)
                tax_amount = company.currency_id.round(tax_amount)
            tax_data['raw_base_amount_currency'] = gross_amount_currency
            tax_data['raw_tax_amount_currency'] = bonus_tax_amount_currency
            tax_data['raw_base_amount'] = base_amount
            tax_data['raw_tax_amount'] = tax_amount

    @api.model
    def _get_tax_totals_summary(self, base_lines, currency, company, cash_rounding=None):
        """Odoo 18 sustituye `_prepare_tax_totals` por este método.

        El grupo de impuestos de la bonificación no debe aparecer en los
        totales del documento: se muestra en cero y su importe se descuenta
        del subtotal y del total general.
        """
        tax_totals = super()._get_tax_totals_summary(
            base_lines, currency, company, cash_rounding=cash_rounding)

        # Etiqueta del subtotal sin impuestos usada en los comprobantes peruanos.
        core_untaxed_label = _("Untaxed Amount")
        for subtotal in tax_totals['subtotals']:
            if subtotal.get('name') == core_untaxed_label:
                subtotal['name'] = _("Importe libre de impuestos")

        for subtotal in tax_totals['subtotals']:
            for tax_group in subtotal['tax_groups']:
                involved_taxes = self.browse(tax_group['involved_tax_ids'])
                if not involved_taxes._l10n_pe_edi_is_bonus_tax():
                    continue
                tax_amount_currency = tax_group['tax_amount_currency']
                tax_amount = tax_group['tax_amount']

                subtotal['tax_amount_currency'] -= tax_amount_currency
                subtotal['tax_amount'] -= tax_amount
                tax_totals['tax_amount_currency'] -= tax_amount_currency
                tax_totals['tax_amount'] -= tax_amount
                tax_totals['total_amount_currency'] -= tax_amount_currency
                tax_totals['total_amount'] -= tax_amount

                tax_group.update({
                    'base_amount_currency': 0.0,
                    'base_amount': 0.0,
                    'tax_amount_currency': 0.0,
                    'tax_amount': 0.0,
                    'display_base_amount_currency': 0.0,
                    'display_base_amount': 0.0,
                })

        return tax_totals
