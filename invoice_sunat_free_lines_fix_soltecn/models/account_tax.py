from odoo import api, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.model
    def _add_tax_details_in_base_line(self, base_line, company, rounding_method=None):
        """invoice_sunat_soltecn_v16 fuerza el IGV referencial del 18 % en todo
        impuesto 9996, incluidos los hijos de un grupo ("0% Libre Final" pasaba a
        cobrar 18 %). Aquí se restaura el cálculo estándar de esos hijos: el grupo
        ya resuelve su importe con su propio porcentaje y el resto de hijos.
        """
        super()._add_tax_details_in_base_line(base_line, company, rounding_method=rounding_method)

        rounding_method = rounding_method or company.tax_calculation_rounding_method
        rate = base_line['rate']
        for tax_data in base_line['tax_details']['taxes_data']:
            if not tax_data.get('group') or not tax_data['tax']._l10n_pe_edi_is_bonus_tax():
                continue
            # Mismo cálculo que account.tax._add_tax_details_in_base_line del core.
            tax_amount = tax_data['tax_amount'] / rate if rate else 0.0
            base_amount = tax_data['base_amount'] / rate if rate else 0.0
            if rounding_method == 'round_per_line':
                tax_amount = company.currency_id.round(tax_amount)
                base_amount = company.currency_id.round(base_amount)
            tax_data['raw_tax_amount_currency'] = tax_data['tax_amount']
            tax_data['raw_tax_amount'] = tax_amount
            tax_data['raw_base_amount_currency'] = tax_data['base_amount']
            tax_data['raw_base_amount'] = base_amount
