from odoo import api, models
from odoo.tools import float_compare

FREE_TAX_CODE = '9996'


class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.model
    def _add_tax_details_in_base_line(self, base_line, company, rounding_method=None):
        """En los grupos "Libre Final" el hijo "... Gasto" (-18 %) debe anular
        exactamente al hijo 9996 (+18 %). Con el 9996 incluido en el precio y
        redondeo por línea no ocurre: el 9996 se redondea sobre el precio con IGV
        (96.27 -> 14.69) y el gasto sobre la base ya redondeada (81.58 -> 14.68),
        y la línea gratuita queda cobrando 0.01. Aquí el gasto se iguala al
        negativo del 9996.
        """
        super()._add_tax_details_in_base_line(base_line, company, rounding_method=rounding_method)

        tax_details = base_line['tax_details']
        taxes_data = tax_details['taxes_data']
        for gra_data in taxes_data:
            gra_tax = gra_data['tax']
            if (
                not gra_data.get('group')
                or gra_tax.l10n_pe_edi_tax_code != FREE_TAX_CODE
                or gra_tax.amount_type != 'percent'
                or not gra_tax.amount
            ):
                continue
            for expense_data in taxes_data:
                expense_tax = expense_data['tax']
                if (
                    expense_data.get('group') != gra_data['group']
                    or expense_tax.l10n_pe_edi_tax_code
                    or expense_tax.amount_type != 'percent'
                    or float_compare(expense_tax.amount, -gra_tax.amount, precision_digits=4)
                ):
                    continue
                delta_currency = -gra_data['raw_tax_amount_currency'] - expense_data['raw_tax_amount_currency']
                delta = -gra_data['raw_tax_amount'] - expense_data['raw_tax_amount']
                expense_data['tax_amount'] = -gra_data['tax_amount']
                expense_data['raw_tax_amount_currency'] = -gra_data['raw_tax_amount_currency']
                expense_data['raw_tax_amount'] = -gra_data['raw_tax_amount']
                tax_details['raw_total_included_currency'] += delta_currency
                tax_details['raw_total_included'] += delta

    def _l10n_pe_edi_is_bonus_tax(self):
        """invoice_sunat_soltecn_v16 trata como bonificación todo impuesto 9996:
        le fuerza el IGV referencial del 18 % (_add_tax_details_in_base_line) y lo
        oculta de los totales (_get_tax_totals_summary).

        Eso solo vale para un 9996 usado suelto. Los hijos 9996 de un grupo
        ("18% Libre Final" / "0% Libre Final") se calculan con su propio porcentaje
        y el grupo ya los compensa con sus otros hijos ("Substraer base",
        "... Gasto"); tratarlos como bonificación cobraba un IGV inexistente en el
        0 % y restaba dos veces el IGV en los totales del 18 %.
        """
        if not super()._l10n_pe_edi_is_bonus_tax():
            return False
        return not self.with_context(active_test=False).search_count(
            [('children_tax_ids', 'in', self.ids)], limit=1)
