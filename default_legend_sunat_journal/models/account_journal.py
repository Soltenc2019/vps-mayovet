from odoo import api, fields, models, tools, _

CATALOG52 = [
    ("1002", "TRANSFERENCIA GRATUITA DE UN BIEN Y/O SERVICIO PRESTADO GRATUITAMENTE"),
    ("2000", "COMPROBANTE DE PERCEPCIÓN"),
    ("2001", "BIENES TRANSFERIDOS EN LA AMAZONÍA REGIÓN SELVAPARA SER CONSUMIDOS EN LA MISMA"),
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

class AccountJournal(models.Model):
    _inherit = "account.journal"

    default_l10n_pe_edi_legend = fields.Selection(
        selection=CATALOG52,
        string="Codigo de leyenda por defecto", help="Peru: Specific operation type code.")