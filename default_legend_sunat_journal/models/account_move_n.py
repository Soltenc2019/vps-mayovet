from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_repr, float_round
from num2words import num2words

CATALOG52 = [
    ("1002", "TRANSFERENCIA GRATUITA DE UN BIEN Y/O SERVICIO PRESTADO GRATUITAMENTE"),
    ("2000", "COMPROBANTE DE PERCEPCIÓN"),
    ("2001", "BIENES TRANSFERIDOS EN LA AMAZONÍA REGIÓN SELVA PARA SER CONSUMIDOS EN LA MISMA"),
    ("2002", "SERVICIOS PRESTADOS EN LA AMAZONÍA REGIÓN SELVA PARA SER CONSUMIDOS EN LA MISMA"),
    ("2003", "CONTRATOS DE CONSTRUCCIÓN EJECUTADOS EN LA AMAZONÍA REGIÓN SELVA"),
    ("2004", "Agencia de Viaje - Paquete turístico"),
    ("2005", "Venta realizada por emisor itinerante"),
    ("2006", "Operación sujeta a detracción"),
    ("2007", "Operación sujeta al IVAP"),
    ("2008", "VENTA EXONERADA DEL IGV-ISC-IPM. PROHIBIDA LA VENTA FUERA DE LA ZONA COMERCIAL DE TACNA"),
    ("2009", "PRIMERA VENTA DE MERCANCÍA IDENTIFICABLE ENTRE USUARIOS DE LA ZONA COMERCIAL"),
    ("2010", "Restitucion Simplificado de Derechos Arancelarios"),
    ("2011", "EXPORTACION DE SERVICIOS - DECRETO LEGISLATIVO Nº 919"),
]

class AccountMoveLine(models.Model):
    _inherit = 'account.move'

    l10n_pe_edi_legend = fields.Selection(
        selection=CATALOG52,
        string="Código de leyenda")
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            journal_id = vals.get('journal_id')
            if journal_id:
                journal = self.env['account.journal'].browse(journal_id)
                if journal.default_l10n_pe_edi_legend:
                    vals['l10n_pe_edi_legend'] = journal.default_l10n_pe_edi_legend
                    matched_elements = [element for element in CATALOG52 if element[0] == journal.default_l10n_pe_edi_legend]
                    vals['l10n_pe_edi_legend_value'] = matched_elements[0][1]
        return super().create(vals_list)
    


        
        