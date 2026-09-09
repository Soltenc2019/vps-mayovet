from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime

class AccountMove(models.Model): 
    
    _inherit = 'stock.picking'  
    
    driver_id = fields.Many2one('hr.employee', string='Conductor', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", store=True, index=True)
    driver_license = fields.Char(related='driver_id.driver_license', string='Licencia conductor', store=True, readonly=True) 
    vehicle_plate = fields.Char(related='driver_id.vehicle_plate', string='Placa vehículo', store=True, readonly=True)
    vehicle_model = fields.Char(related='driver_id.vehicle_model', string='Modelo vehículo', store=True, readonly=True)
    first_name = fields.Char(related='driver_id.first_name', string='Nombres', store=True, readonly=True)
    family_name = fields.Char(related='driver_id.family_name', string='Apellidos', store=True, readonly=True)
    identification_id = fields.Char(related='driver_id.identification_id', string='DNI', store=True, readonly=True)

    employee_company = fields.Many2one('res.partner', string='Transporte público', store=True, readonly=False)
    # employee_company = fields.Many2one(related='driver_id.employee_company', string='Transporte público', store=True, readonly=False)
    employee_company_name = fields.Char(related='employee_company.name', string='Transporte público nombre', store=True, readonly=True)
    employee_company_ruc = fields.Char(related='employee_company.vat', string='Transporte público ruc', store=True, readonly=True)

    is_m1l = fields.Boolean(string="Es M1 o L", store=True)
    vehicle_plate_m1l = fields.Char(string='Placa vehículo M1 o L', store=True, help="Si el traslado se realiza sin un medio de trasporte M1 o L, sino por una persona, digitar 'SMT' (Sin medio de transporte)")

    departure_date  = fields.Date('Fecha salida', copy=False, store=True, readonly=False,help="Fecha de salida", default= datetime.today())
    arrival_date  = fields.Date('Fecha llegada', copy=False, store=True, readonly=False,help="Fecha de llegada")

    #? NUEVO CAMPO SUNAT 01/06/2026
    merch_delivery_to_driver = fields.Date(string="Fecha de entrega de bienes al transportista", store=True, copy=False, readonly=False)
    
    starting_address_departamento = fields.Many2one(related='starting_address.state_id',string='Ubigeo origen departamento', readonly=True)
    starting_address_provincia = fields.Many2one(related='starting_address.city_id',string='Ubigeo origen provincia', readonly=True)
    starting_address_distrito = fields.Many2one(related='starting_address.l10n_pe_district',string='Ubigeo origen distrito', readonly=True)
    starting_address = fields.Many2one('res.partner',string='Dirección de partida',compute='_compute_starting_address', readonly=True) 

    destination_address_departamento = fields.Many2one(related='destination_address.state_id',string='Ubigeo destino departamento', store=True)
    destination_address_provincia = fields.Many2one(related='destination_address.city_id',string='Ubigeo destino provincia', store=True)
    destination_address_distrito = fields.Many2one(related='destination_address.l10n_pe_district',string='Ubigeo detino distrito', store=True)
    destination_address = fields.Many2one('res.partner', string='Dirección de destino', domain="[('vat', '=?', partner_id_vat)]", store=True)
    partner_id_vat = fields.Char(related='partner_id.vat', string='VAT Partner', store=True, readonly=True)

    transportation_reason = fields.Selection(
        [('01', 'Venta'),
        ('02', 'Compra'),
        ('08', 'Importación'),
        ('09', 'Exportación'),
        ('18', 'Traslado emisor itinerante CP'),
        ('19', 'Traslado a zona primaria'),
        ('14', 'Venta sujeta a confirmación del comprador'),
        ('04', 'Traslado entre establecimiento de la misma empresa'),
        ('13', 'Otros')],
        string='Motivo',
        store=True,
        copy=False, tracking=True)
    handling_instructions = fields.Many2one('transportation.reason.other', string='Descripción razón otros')
    edi_state = fields.Selection(
        selection=[('not_enough', 'Información incompleta'),('to_send', 'Para enviar'), ('sent', 'Enviado'), ('procesado', 'Procesado'), ('ticket','Ticket listo'), ('cdr_aceptado','Aceptado'),('to_cancel', 'Para cancelar'), ('cancelled', 'Cancelado')],
        string="Estado guía remisión electronica",
        store=True,
        default = 'not_enough',
        compute='_compute_edi_state',
        help='Todos los estados de una guía remisión')
    condition = fields.Char(string='Condición de', related = "sale_id.payment_term_id.name", readonly=True)
    comments = fields.Text(string='Comentarios')
    def _default_edi_format_id(self):
        return self.env['account.edi.format'].search([('name','=','Peru UBL 2.1')], limit=1).id
    
    def name_get(self):
        res = []
        for move in self:
            name = move.name
            if move.serial_referral_guide:
                name = "%s" % (move.serial_referral_guide)
            res.append((move.id, name))
        return res

    edi_format_id = fields.Many2one('account.edi.format', required=True, default=_default_edi_format_id)
    origin_invoice = fields.Many2one('account.move',string='Factura origen',compute='_compute_origin_invoice', readonly=True, store=True, copy=False)

    sequence_serial_guide = fields.Char(related='picking_type_id.custom_sequence_id.prefix',string='Serie guía remisión', store=True, readonly=True, copy=False)
    sequence_last_number_guide = fields.Integer(related='picking_type_id.sequence_number_guide',string='Último secuencia de número', store=True, readonly=True, copy=False)
    sequence_number_guide = fields.Integer(string='Secuencia número remisión', readonly=True, copy=False) 
    serial_referral_guide = fields.Char(string='Guía remisión', readonly=True, copy=False)
    
    referral_guide_QR = fields.Char(string='QR guía remisión', readonly=False, copy=False)
    error = fields.Char(string='Descripción error', readonly=True, copy=False)
    blocking_level = fields.Char(string='Tipo error', readonly=True, copy=False)
    response_num_ticket = fields.Char(string='Número de ticket', readonly=True, copy=False)
    fec_recepcion = fields.Datetime(string='Fecha recepción', readonly=True, copy=False)
    cdr_attachment = fields.Binary(string='CDR guía remisión', copy=False)
    picking_type_use_referrer_guide = fields.Boolean(related='picking_type_id.use_referrer_guide',readonly=True)

    transport_type = fields.Selection(string="Tipo de transporte",selection=[('01', 'Transporte público'),('02', 'Transporte privado'),], default='02')

    related_document = fields.One2many('related.document', 'stock_picking',  string='Documentos relacionado', copy=False)
    net_weight_measure_information = fields.Text(string="Sustento diferencia peso bruto total")
    total_transport_handling_unit_quantity = fields.Char("Número de bultos o pallets", compute="_compute_total_transport_handling_unit_quantity", store=True)
    first_package = fields.Char("Contenedor 1")
    first_package_trace = fields.Char("Número de precinto 1")
    second_package = fields.Char("Contenedor 2")
    second_package_trace = fields.Char("Número de precinto 2")
    indicador_traslado_total_damods = fields.Boolean(string="Traslado Total DAM o DS", store=True)
    net_weight_measure = fields.Char(string="Peso bruto total items", compute="_compute_net_gross_weight_measure", store=True)
    gross_weight_measure = fields.Char(string="Peso bruto total carga", compute="_compute_net_gross_weight_measure", store=True)
    SELECTION_AERO_PORT_LOCATION = [
        ('1', 'Puerto'),
        ('2', 'Aeropuerto'),
    ]
    type_aero_port_location = fields.Selection(SELECTION_AERO_PORT_LOCATION, string="Tipo de locación", default="1")
    port_locations = fields.Many2one('catalog.63',string='Puertos')
    aeroport_locations = fields.Many2one('catalog.64',string='Aeropuertos')

    # NEW
    # stock_group = fields.One2many('stock.group.picking', 'stock_picking',  string='Agrupamiento', copy=False)
    specify_weight = fields.Boolean(related="company_id.specify_weight")
    specify_weight_by_bultos_paletas = fields.Boolean(related="company_id.specify_weight_by_bultos_paletas")
    # group_by_bultos_paletas = fields.Boolean(related="company_id.group_by_bultos_paletas")

    # , 'stock_group', 'stock_group.product_id', 'stock_group.quantity'
    
    # def button_validate(self):
    #     res = super(AccountMove, self).button_validate()
    #     for stock in self:
    #         stock._compute_net_gross_weight_measure()
    #     return res

    @api.depends('indicador_traslado_total_damods','transportation_reason','move_line_ids', 'move_line_ids.product_id', 'move_line_ids.quantity', 'move_line_ids_without_package', 'move_line_ids_without_package.quantity')
    def _compute_net_gross_weight_measure(self):
        for stock in self:
            stock.gross_weight_measure = False
            stock.net_weight_measure = False
            # raise ValidationError(str(stock.specify_weight))
            if stock.specify_weight:
                # and stock.state == 'done'
                net_weight_measure = 0
                pallet_bulto_weight_measure = 0
                result_package_id = self.move_line_ids.mapped('result_package_id')
                if result_package_id:
                    for package in result_package_id:
                        pallet_bulto_weight_measure += package.package_type_id.package_type_weight
                        net_weight_measure += package.total_package_items_weight
                for move in stock.move_line_ids.filtered(lambda d: not d.result_package_id):
                    net_weight_measure += move.product_id.weight * move.quantity
                stock.gross_weight_measure = net_weight_measure + pallet_bulto_weight_measure
                if not stock.indicador_traslado_total_damods and stock.transportation_reason in ('08', '09'):
                    stock.net_weight_measure = net_weight_measure

    @api.depends('move_line_ids','move_line_ids.result_package_id')
    def _compute_total_transport_handling_unit_quantity(self):
        for stock in self:
            stock.total_transport_handling_unit_quantity = False
            package_quantity = self.move_line_ids.mapped('result_package_id')
            if package_quantity:
                stock.total_transport_handling_unit_quantity = len(package_quantity)

    @api.onchange('is_m1l')
    def onchange_is_m1l(self):
        if not self.is_m1l:
            self.vehicle_plate_m1l = False

    @api.model
    def _default_transportation_department_id(self):
        return self.env.ref("Guia_Remision_Soltecn_2.transportation_department", False)

    transportation_department_default = fields.Many2one('hr.department', required=False, default=_default_transportation_department_id)

    @api.depends('location_id')
    def _compute_starting_address(self):
        for stock in self:
            partner = self.env['stock.warehouse'].search([('view_location_id','=',stock.location_id.location_id.id)], limit=1).partner_id
            if not partner:
                partner = self.env['stock.warehouse'].search([], limit=1).partner_id
            stock.starting_address = partner

    @api.depends('origin','move_ids_without_package','move_ids_without_package.picking_id','move_ids_without_package.sale_line_id','move_ids_without_package.sale_line_id.invoice_lines','move_ids_without_package.sale_line_id.invoice_lines.move_id','move_ids_without_package.sale_line_id.invoice_lines.move_id.state')
    def _compute_origin_invoice(self):
        for stock in self:
            first_sale_linde_id = False
            stock.origin_invoice = False
            for move_id in stock.move_ids_without_package:
                if move_id.sale_line_id:
                    first_sale_linde_id = move_id.sale_line_id.id
                    break

            value_io = False
            if first_sale_linde_id:
                value_io = self.env['account.move.line'].search([('sale_line_ids','=',first_sale_linde_id),('parent_state','not in',['cancel'])], limit=1).move_id
            else:
                if stock.origin:
                    value_io = self.env['account.move'].search([('invoice_origin','=',stock.origin),('state','not in',['cancel'])], limit=1)
            # raise ValidationError(value_io)
            if value_io:
                stock.origin_invoice = value_io

    @api.depends('driver_id','driver_license','vehicle_plate','identification_id',
    'departure_date','arrival_date','starting_address','destination_address',
    'transportation_reason','state', 'transport_type')
    def _compute_edi_state(self):
        for record in self:
            record.edi_state = 'not_enough'
            enough_information = False
            if record.departure_date and record.arrival_date and record.transportation_reason and record.state == "done" and record.transport_type:
                if record.transportation_reason not in ('08') and not record.starting_address:
                    return
                if record.transportation_reason not in ('09') and not record.destination_address:
                    return
                if record.is_m1l:
                    enough_information = True
                else:
                    if record.transport_type == '01':
                        if record.employee_company and record.employee_company_name and record.employee_company_ruc:
                            enough_information = True
                    elif record.transport_type == '02':
                        if record.driver_id and record.driver_license and record.vehicle_plate:
                            enough_information = True

                if record.sequence_serial_guide:
                    if enough_information:
                        record.edi_state = 'to_send'
                else:
                    raise ValidationError("Se requiere la especificación de serie en "+record.picking_type_id.warehouse_id.name)

    @api.model
    def create(self, vals):
        res = super(AccountMove, self).create(vals)
        for record in self:
            # NEW
            if record.edi_state == 'to_send':
                record.verify_values_before_send()
            # NEW
            if not record.serial_referral_guide and record.edi_state == 'to_send':
                sequence = self.picking_type_id.custom_sequence_id
                number_asigned = sequence.number_next_actual
                serial_referral_guide = sequence.next_by_id()
                if serial_referral_guide:
                    record.serial_referral_guide = serial_referral_guide
                    record.sequence_number_guide = number_asigned
                else:
                    raise ValidationError("No se pudo generar el correlativo, comunicate con su proveedor")
        return res
    
    def write(self, vals):
        res = super(AccountMove, self).write(vals)
        for record in self:
            # NEW
            if record.edi_state == 'to_send':
                record.verify_values_before_send()
            # NEW
            if not record.serial_referral_guide and record.edi_state == 'to_send':
                sequence = record.picking_type_id.custom_sequence_id
                number_asigned = sequence.number_next_actual
                serial_referral_guide = sequence.next_by_id()
                if serial_referral_guide:
                    record.serial_referral_guide = serial_referral_guide
                    record.sequence_number_guide = number_asigned
                else:
                    raise ValidationError("No se pudo generar el correlativo, comunicate con su proveedor")
        return res

    def document_types_validation(self):
        if self.transportation_reason not in ('08','09'):
            if self.related_document.filtered(lambda d: d.related_document_type in ('50', '52')):
                return _("El tipo de documento relacionado no corresponde para motivo de traslado seleccionado")
        if self.transportation_reason in ('08','09'):
            if self.related_document.filtered(lambda d: d.related_document_type not in ('09', '49', '50', '52', '80')):
                return _("El tipo de documento relacionado no corresponde para motivo de traslado seleccionado")
            if not self.related_document.filtered(lambda d: d.related_document_type in ('50', '52')) and not self.indicador_traslado_total_damods:
                return _("No se ha ingresado documentos del tipo Declaracion Aduanera de Mercancias (DAM) o el Declaracion Simplificada (DS) para el motivo de traslado selecionado")
        if self.related_document.filtered(lambda d: d.related_document_type in ('49', '80')) and not self.indicador_traslado_total_damods and not self.move_ids_without_package.filtered(lambda ml: ml.product_id.unspsc_code_id):
            return _("Si ingreso un documento relacionado tipo '49' (solo en caso de GRE-Remitente) u '80', debe existir al menos un item con Partida arancelaria")
        return False
    
    def reason_transportation_validation(self):
        if self.transportation_reason not in ("01","08","09", "04","13", False):
            return _("Guía remisión habilitado para motivo ventas,traslado entre establecimientos, importación, exportación y otros")
        if self.transportation_reason in ('01', '03', '05', '06', '09', '14', '17') and (self.company_id.vat == self.partner_id.vat):
            return _("Destinatario no debe ser igual al remitente.")
        if self.transportation_reason in ('08','09') and not self.indicador_traslado_total_damods and not self.net_weight_measure:
            return _("Si el motivo de traslado es Importacion o Exportacion y no se trata de un traslado total de la DAM o DS, debe indicar el Peso bruto total de los items.")
        if self.transportation_reason in ('08','09') and self.move_ids_without_package.filtered(lambda ml: not ml.damds_number or not ml.damds_serie) and not self.indicador_traslado_total_damods:
            return _("Si el motivo de traslado es importación o exportación y no hay inidicador de traslado total DAM o DS especificado. Se deben de especificar el DAM y DS en las líneas.")
        return False

    def uom_validation(self):
        if self.transportation_reason in ('08','09') and self.move_ids_without_package.filtered(lambda ml: not ml.product_uom.measure_unit_code_dam_ds) and not self.indicador_traslado_total_damods:
            return _("Si el motivo de traslado es importación o exportación, el valor del atributo no está en el listado Catálogo 65 de las líneas de producto.")
        return False
    
    def weight_validation(self):
        if self.specify_weight and any(map(lambda x: not x.weight, self.move_ids_without_package.product_id)):
            return _("Es necesario especificar los pesos de los productos.")
        return False

    def button_validate(self):
        for stock in self:
            if not self.specify_weight and not self.gross_weight_measure and self.edi_state == 'to_send':
                raise ValidationError("Es necesario ingresar el peso bruto total de la carga.")
            stock.departure_date = datetime.today()
        return super(AccountMove, self).button_validate()
            
    def verify_values_before_send(self):
        document_types_validation_return = self.document_types_validation()
        reason_transportation_validation_return = self.reason_transportation_validation()
        uom_validation_return = self.uom_validation()
        weight_validation_return = self.weight_validation()
        if weight_validation_return:
            raise ValidationError(weight_validation_return)
        if document_types_validation_return:
            raise ValidationError(document_types_validation_return)
        if reason_transportation_validation_return:
            raise ValidationError(reason_transportation_validation_return)
        if uom_validation_return:
            raise ValidationError(uom_validation_return)
            
    def action_process_edi_web_services(self):

        docs = self.filtered(lambda d: d.edi_state in ('to_send'))
        doc_type = 'reference_guide'
        self._process_job(docs, doc_type)
    
    def action_check_ticket_edi_web_services(self):
        docs = self.filtered(lambda d: d.edi_state in ('ticket'))
        doc_type = 'check_reference_guide'
        self._process_job(docs, doc_type)

    @api.model
    def _process_job(self, documents, doc_type):
        """Post or cancel move_id (invoice or payment) by calling the related methods on edi_format_id.
        Invoices are processed before payments.

        :param documents: The documents related to this job. If edi_format_id does not support batch, length is one
        :param doc_type:  Are the moves of this job invoice or payments ?
        """
        def _postprocess_post_edi_results(documents, edi_result):
            for document in documents:
                picking = document
                picking_result = edi_result.get(picking, {})
                if picking_result.get('response_num_ticket'):
                    values = {
                        'response_num_ticket': picking_result.get('response_num_ticket', False),
                        'error': picking_result.get('error', False),
                        'blocking_level': picking_result.get('blocking_level', False),
                    }
                    if not values.get('error'):
                        values.update({'edi_state': 'ticket'})
                    document.write(values)
                else:
                    document.write({
                        'error': picking_result.get('error', False),
                        'blocking_level': picking_result.get('blocking_level', False),
                    })

        def _postprocess_post_edi_ticket_results(documents, edi_result):
            attachments_to_unlink = self.env['ir.attachment']
            for document in documents:
                picking = document
                picking_result = edi_result.get(picking, {})
                if picking_result.get('attachment'):
                    # old_attachment = document.message_main_attachment_id
                    values = {
                        # 'message_main_attachment_id': picking_result['attachment'].id,
                        'error': picking_result.get('error', False),
                        'blocking_level': picking_result.get('blocking_level', False),
                        'referral_guide_QR': picking_result.get('referral_guide_QR', False),
                    }
                    if not values.get('error'):
                        values.update({'edi_state': 'cdr_aceptado'})
                    elif values.get('error'):
                        values.update({'edi_state': 'to_send'})
                    document.write(values)
                    # raise ValidationError(not old_attachment.res_model)
                    # if not old_attachment.res_model or not old_attachment.res_id:
                    #     attachments_to_unlink |= old_attachment
                else:
                    values = {
                        'error': picking_result.get('error', False),
                        'blocking_level': picking_result.get('blocking_level', False),
                    }
                    if values.get('error') and not picking_result.get('api', False):
                        values.update({'edi_state': 'to_send'})
                    document.write(values)
        
            # Attachments that are not explicitly linked to a business model could be removed because they are not
            # supposed to have any traceability from the user.
            attachments_to_unlink.unlink()

        test_mode = self._context.get('edi_test_mode', False)
        edi_format = documents[0].edi_format_id
        if doc_type == 'reference_guide':
            edi_result = edi_format._post_reference_guide_edi(documents, test_mode=test_mode)
            _postprocess_post_edi_results(documents, edi_result)
        if doc_type == 'check_reference_guide':
            edi_result = edi_format._post_check_ticket_reference_guide_edi(documents, test_mode=test_mode)
            _postprocess_post_edi_ticket_results(documents, edi_result)

