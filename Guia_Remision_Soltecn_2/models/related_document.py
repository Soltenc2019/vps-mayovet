from odoo import models, fields, api

class RelatedDocument(models.Model):
    _name = 'related.document'
    _description = 'Related document'

    stock_picking = fields.Many2one('stock.picking', string='Stock picking', index=True, required=True, readonly=True, auto_join=True, ondelete="cascade", check_company=True)
    PE_RELATED_DOCUMENT = [
        ('01', 'Factura'),
        ('03', 'Boleta de Venta'),
        # ('04', 'Liquidación de Compra'),
        ('09', 'Guía de Remisión Remitente'),
        # ('12', 'Ticket o cinta emitido por máquina registradora'),
        # ('31', 'Guía de Remisión Transportista'),
        # ('48', 'Comprobante de Operaciones - Ley N° 29972'),
        ('49', 'Constancia de Depósito - IVAP (Ley 28211)'),
        ('50', 'Declaración Aduanera de Mercancías'),
        ('52', 'Declaración Simplificada (DS)'),
        # ('65', 'Autorización de Circulación para transportar MATPEL - Callao'),
        # ('66', 'Autorización de Circulación para transporte de carga y mercancías en Lima Metropolitana'),
        # ('67', 'Permiso de Operación Especial para el servicio de transporte de MATPEL - MTC'),
        # ('68', 'Habilitación Sanitaria de Transporte Terrestre de Productos Pesqueros y Acuícolas'),
        # ('69', 'Permiso / Autorización de operación de transporte de mercancías'),
        # ('71', 'Resolución de Adjudicación de bienes - SUNAT'),
        # ('72', 'Resolución de Comiso de bienes - SUNAT'),
        # ('73', 'Guía de Transporte Forestal o de Fauna - SERFOR'),
        # ('74', 'Guía de Tránsito - SUCAMEC'),
        # ('75', 'Autorización para operar como empresa de Saneamiento Ambiental - MINSA'),
        # ('76', 'Autorización para manejo y recojo de residuos sólidos peligrosos y no peligrosos'),
        # ('77', 'Certificado fitosanitario la movilización de plantas, productos vegetales, y otros artículos reglamentados'),
        # ('78', 'Registro Único de Usuarios y Transportistas de Alcohol Etílico'),
        ('80', 'Constancia de Depósito - Detracción'),
        # ('81', 'Código de autorización emitida por el SCOP'),
        # ('82', 'Declaración jurada de mudanza'),
    ]
    related_document_number = fields.Char(
        string="Documento relacionado",
        help="(Serie)-(Secuencia sin ceros a la izquierda) / Ejem. H001-450",
        copy=False,
    )
    related_document_type = fields.Selection(
        selection=PE_RELATED_DOCUMENT,
        string="Tipo documento relacionado",
        copy=False,
    )
