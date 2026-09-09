from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_repr, float_round
from num2words import num2words

class AccountMoveLine(models.Model):
    _inherit = 'account.move'

    reference_downpayments_invoice = fields.Many2many("account.move",'model_1_rel','id','move_id',string="Referencia anticipos", domain=[('edi_state', '=', 'sent'),('move_type', '=', 'out_invoice')])
    # , domain=[('edi_state', '=', 'sent'),('move_type', '=', 'out_invoice')]

    l10n_pe_edi_amount_in_words = fields.Char(string="Amount in Words", compute='_l10n_pe_edi_amount_in_words')
    ruc_client = fields.Char(related='partner_id.vat', string='RUC/DNI cliente', store=True, readonly=True)
    sucursal_address = fields.Many2one('res.partner', related='journal_id.sucursal_address', string='Dirección Sucursal', readonly=True)

    # Detraction
    l10n_pe_edi_base_detraction = fields.Monetary(string='Base Detracción', store=True, compute='_compute_detraction', tracking=True)
    l10n_pe_edi_total_detraction = fields.Monetary(string='Total Detracción', store=True, compute='_compute_detraction', tracking=True)
    l10n_pe_edi_total_detraction_signed_not_rounded = fields.Monetary(string='Total Detracción soles', store=True, currency_field='currency_id_pen', compute='_compute_detraction', tracking=True)
    l10n_pe_edi_total_detraction_signed = fields.Monetary(string='Total Detracción Signed', store=True, currency_field='currency_id_pen', compute='_compute_detraction', tracking=True)
    l10n_pe_edi_amount_total_detraction = fields.Monetary(string='Monto total con Detracción', store=True, compute='_compute_detraction', tracking=True)
    l10n_pe_edi_porcentage_detraction = fields.Integer(string='Porcentage detracción', store=True, compute='_compute_detraction')

    # Retention
    l10n_pe_edi_retention_type_id = fields.Many2one('l10n_pe_edi.catalog.23', string='Tipo de retención')
    l10n_pe_edi_base_retention = fields.Monetary(string='Base retención', store=True, compute='_compute_retention', tracking=True)
    l10n_pe_edi_total_retention = fields.Monetary(string='Total retención', store=True, compute='_compute_retention', tracking=True)
    l10n_pe_edi_total_retention_signed = fields.Monetary(string='Total retención firmada', currency_field='currency_id_pen', store=True, compute='_compute_retention', tracking=True)
    l10n_pe_edi_amount_total_retention = fields.Monetary(string='Monto total con retención', store=True, compute='_compute_retention', tracking=True)

    # Currency PEN
    currency_id_pen = fields.Many2one('res.currency',default=lambda self: self.env['res.currency'].search([('name', '=', 'PEN')]).id,readonly=True)
    currency_id_name = fields.Char(related="currency_id.name",readonly=True)

    # @api.model_create_multi
    # def create(self, vals_list):
    #     for vals in vals_list:
    #         journal_id = vals.get('journal_id')
    #         if journal_id:
    #             journal = self.env['account.journal'].browse(journal_id)
    #             if journal.default_l10n_pe_edi_legend:
    #                 vals['l10n_pe_edi_legend'] = journal.default_l10n_pe_edi_legend
    #     return super().create(vals_list)

    # Default invoice report for Electronic invoice
    def _get_name_invoice_report(self):
        self.ensure_one()
        if self.l10n_latam_use_documents and self.company_id.country_id.code == 'PE':
            return 'invoice_sunat_soltecn_v16.report_invoice_document'
        return super()._get_name_invoice_report()

    @api.depends('amount_total','currency_id')
    def _l10n_pe_edi_amount_in_words(self):
        """Transform the amount to text
        """
        for move in self:
            amount_base, amount = divmod(move.amount_total, 1)
            amount = round(amount, 2)
            amount = int(round(amount * 100, 2))

            lang_code = self.env.context.get('lang') or self.env.user.lang
            lang = self.env['res.lang'].search([('code', '=', lang_code)])
            words = num2words(amount_base, lang=lang.iso_code)
            result = _('%(words)s CON %(amount)02d/100 %(currency_label)s') % {
                'words': words,
                'amount': amount,
                'currency_label': move.currency_id.name == 'PEN' and 'SOLES' or move.currency_id.currency_unit_label,
            }
            move.l10n_pe_edi_amount_in_words = result.upper()

    @api.depends('l10n_pe_edi_operation_type','amount_total','currency_id','amount_untaxed')
    def _compute_detraction(self):
        for move in self:
            move.l10n_pe_edi_porcentage_detraction = False
            move.l10n_pe_edi_total_detraction_signed_not_rounded = False
            move.l10n_pe_edi_total_detraction_signed = False
            move.l10n_pe_edi_total_detraction = False
            move.l10n_pe_edi_amount_total_detraction = False
            move.l10n_pe_edi_base_detraction = False
            if move.l10n_pe_edi_operation_type in ('1001','1002','1003','1004'):
                lines_p = move.invoice_line_ids.filtered(lambda line: line.display_type == "product")
                if lines_p:
                    max_percent = max(lines_p.mapped('product_id.l10n_pe_withhold_percentage'))
                    move.l10n_pe_edi_porcentage_detraction = max_percent               
                    # move.l10n_pe_edi_base_detraction = move.amount_untaxed * (max_percent / 100)
                    # move.l10n_pe_edi_total_detraction = move.amount_total * (max_percent/100.0) 
                    # move.l10n_pe_edi_total_detraction_signed = move.l10n_pe_edi_total_detraction * move.currency_id.rate
                    # move.l10n_pe_edi_amount_total_detraction = move.amount_total - move.l10n_pe_edi_total_detraction
                    l10n_pe_edi_total_detraction_temp = move.amount_total * (max_percent / 100)
                    move.l10n_pe_edi_total_detraction_signed_not_rounded = l10n_pe_edi_total_detraction_temp / move.currency_id.rate
                    move.l10n_pe_edi_total_detraction_signed = float_round(move.l10n_pe_edi_total_detraction_signed_not_rounded,precision_digits=0)
                    move.l10n_pe_edi_total_detraction = move.l10n_pe_edi_total_detraction_signed_not_rounded * move.currency_id.rate
                    move.l10n_pe_edi_amount_total_detraction = move.amount_total - move.l10n_pe_edi_total_detraction
                    move.l10n_pe_edi_base_detraction = move.l10n_pe_edi_total_detraction / (move.amount_total / move.amount_untaxed)

    # Retention
    @api.depends('l10n_pe_edi_retention_type_id', 'amount_untaxed', 'amount_total')
    def _compute_retention(self):
        for move in self:
            move.l10n_pe_edi_base_retention = False
            move.l10n_pe_edi_total_retention = False
            move.l10n_pe_edi_total_retention_signed = False
            move.l10n_pe_edi_amount_total_retention = False
            if move.l10n_pe_edi_retention_type_id:
                move.l10n_pe_edi_base_retention = move.amount_untaxed * (move.l10n_pe_edi_retention_type_id.rate / 100)
                move.l10n_pe_edi_total_retention = move.amount_total * (move.l10n_pe_edi_retention_type_id.rate / 100)
                move.l10n_pe_edi_total_retention_signed = move.l10n_pe_edi_total_retention * move.l10n_pe_edi_retention_type_id.rate
                move.l10n_pe_edi_amount_total_retention = move.amount_total - move.l10n_pe_edi_total_retention

    #def _l10n_pe_edi_get_spot(self):
    #    if self.l10n_pe_edi_operation_type in ['1001', '1002', '1003', '1004'] and self.move_type in ('out_invoice'):
    #        max_percent = max(self.invoice_line_ids.mapped('product_id.l10n_pe_withhold_percentage'), default=0)
    #        if max_percent <= 0:
    #            raise UserError("Se debe especificar un servicio con porcetaje de detracción especificado")
    #        if abs(self.amount_total_signed) < 700:
    #            raise UserError("Tipo de operación detracción el monto en soles debe de ser mayor o igual a 700")
    #        line = self.invoice_line_ids.filtered(lambda r: r.product_id.l10n_pe_withhold_percentage == max_percent)[0]
    #        national_bank = self.env.ref('l10n_pe_edi.peruvian_national_bank', raise_if_not_found=False)
    #        national_bank_account_number = False
    #        if national_bank:
    #            national_bank_account = self.company_id.bank_ids.filtered(lambda b: b.bank_id == national_bank)
    #            if national_bank_account:
    #                # just take the first one (but not meant to have multiple)
    #                national_bank_account_number = national_bank_account[0].acc_number
    #
    #        return {
    #            'ID': 'Detraccion',
    #            'PaymentMeansID': line.product_id.l10n_pe_withhold_code,
    #            'PayeeFinancialAccount': national_bank_account_number,
    #            'PaymentMeansCode': '999',
    #            # 'spot_amount': float_round(self.amount_total * (max_percent/100.0), precision_rounding=2),
    #            'spot_amount': self.amount_total * (max_percent/100.0),
    #            'Amount': float_round(self.amount_total_signed * (max_percent/100.0), precision_digits=0),
    #            'PaymentPercent': max_percent,
    #            'spot_message': "Operación sujeta al sistema de Pago de Obligaciones Tributarias-SPOT, Banco de la Nacion %% %s Cod Serv. %s" % (
    #                line.product_id.l10n_pe_withhold_percentage, line.product_id.l10n_pe_withhold_code) if self.amount_total_signed >= 700.0 else False
    #        }
    #    else:
    #        return {}

    #OVERRIDE
    def _l10n_pe_edi_get_spot(self):
        self.ensure_one()
        max_percent = max(self.invoice_line_ids.mapped('product_id.l10n_pe_withhold_percentage'), default=0)
        if not max_percent or not self.l10n_pe_edi_operation_type in ['1001', '1002', '1003', '1004'] or self.move_type == 'out_refund':
            return {}
        
        if max_percent <= 0:
            raise UserError("Se debe especificar un servicio con porcetaje de detracción especificado")

        if abs(self.amount_total_signed) < 700:
            raise UserError("Tipo de operación detracción el monto en soles debe de ser mayor o igual a 700")

        line = self.invoice_line_ids.filtered(lambda r: r.product_id.l10n_pe_withhold_percentage == max_percent)[0]
        national_bank = self.env.ref('l10n_pe.peruvian_national_bank')
        national_bank_account = self.company_id.bank_ids.filtered(lambda b: b.bank_id == national_bank)
        # just take the first one (but not meant to have multiple)
        national_bank_account_number = national_bank_account[0].acc_number if national_bank_account else False

        # Odoo 18 añadió 'currency' y 'has_installments' al dict (los consume
        # l10n_pe_edi/views/report_invoice.xml) y eliminó 'spot_message'.
        # Se devuelven ambos conjuntos de claves para no romper ninguno.
        has_installments = len(self.line_ids.filtered(lambda l: l.display_type == 'payment_term')) > 1

        return {
            'id': 'Detraccion',
            'currency': self.company_id.currency_id,
            'payment_means_id': line.product_id.l10n_pe_withhold_code,
            'payee_financial_account': national_bank_account_number,
            'payment_means_code': '999',
            'spot_amount': self.amount_total * (max_percent/100.0),
            'amount': float_round(self.amount_total_signed * (max_percent/100.0), precision_rounding=2),
            'payment_percent': max_percent,
            'has_installments': has_installments,
            'spot_message': "Operación sujeta al sistema de Pago de Obligaciones Tributarias-SPOT, Banco de la Nacion %s%% Cod Serv. %s" % (
                line.product_id.l10n_pe_withhold_percentage, line.product_id.l10n_pe_withhold_code) if self.amount_total_signed >= 700.0 else False
        }

    #NEW
    def _l10n_pe_edi_get_retention(self):
        if not self.l10n_pe_edi_retention_type_id:
            return {}
        
        return {
            'charge_indicator': 'false',
            'allowance_charge_reason_code': '62',
            'multiplier_factor': self.l10n_pe_edi_retention_type_id.rate / 100,
            'amount': self.l10n_pe_edi_total_retention,
            'base_amount': self.amount_total,
            'currency_dp': 2,
            'currency_name': self.currency_id.name,
        }
    
    #NEW
    def _l10n_pe_edi_get_reference_downpayments(self):

        if not self.reference_downpayments_invoice:
            return {}

        #AdditionalDocumentReference
        aditional_document_reference_downpayments_vals = []

        #PrepaidPayment
        prepaid_payment_downpayments_vals = []

        downpayments = self.reference_downpayments_invoice

        amount_allowance = 0

        index = 1

        for downpayment in downpayments:
            amount_allowance += downpayment.amount_untaxed

            mapping = {
                '01': '02',
                '03': '03',
            }

            document_type = mapping.get(downpayment.l10n_latam_document_type_id_code, 'default_value')
            
            aditional_document_val = {
                'id' : downpayment.sequence_prefix + str(downpayment.sequence_number),
                'document_type' : document_type,
                'index' : index,
                'party_identification_code': self.company_id.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code,
                'party_identification_vat': self.company_id.partner_id.vat,
            }

            prepaid_payment_val = {
                'index' : index,
                'currency_name' : downpayment.currency_id.name,
                'amount_total' : abs(downpayment.amount_total)
            }

            aditional_document_reference_downpayments_vals.append(aditional_document_val)
            prepaid_payment_downpayments_vals.append(prepaid_payment_val)

            index += 1
  
        return {
            'charge_indicator': 'false',
            'allowance_charge_reason_code': '04',
            'aditional_document_vals': aditional_document_reference_downpayments_vals,
            'prepaid_payment_vals': prepaid_payment_downpayments_vals,
            'amount': amount_allowance,
            'base_amount': ( amount_allowance * 2 ) + self.amount_untaxed,
            'currency_dp': 2,
            'currency_name': self.currency_id.name,
        }


        
        