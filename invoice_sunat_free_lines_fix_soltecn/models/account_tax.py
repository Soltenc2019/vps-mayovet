from odoo import models


class AccountTax(models.Model):
    _inherit = 'account.tax'

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
