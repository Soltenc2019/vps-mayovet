from requests.exceptions import ConnectionError as ReqConnectionError, HTTPError, InvalidSchema, InvalidURL, ReadTimeout
from odoo.tools.zeep.wsse.username import UsernameToken
from odoo.tools.zeep import Client, Settings, Transport
from odoo.tools.zeep.exceptions import Fault
from lxml import etree
from lxml import objectify
from copy import deepcopy

from odoo import models, api, _
from odoo.tools.translate import LazyTranslate
from odoo.addons.iap.tools.iap_tools import iap_jsonrpc
from odoo.exceptions import AccessError
from odoo.tools import float_round, html_escape
from odoo.exceptions import ValidationError
import io
import logging
import base64

_logger = logging.getLogger(__name__)
_lt = LazyTranslate(__name__)
from markupsafe import Markup, escape
class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    def _l10n_pe_edi_cancel_invoices_step_1_sunat_digiflow_common(
            self, company, invoices, void_filename, void_str, credentials):

        self.ensure_one()

        # =========================
        # 🔍 DEBUG INICIAL
        # =========================
        _logger.warning("==== SUNAT DEBUG START ====")
        _logger.warning("VOID FILENAME: %s", void_filename)
        _logger.warning("WSDL: %s", credentials.get('wsdl'))

        # =========================
        # XML firmado
        # =========================
        void_tree = objectify.fromstring(void_str)
        # Odoo 18: el certificado es certificate.certificate y la firma se hace
        # desde account.edi.format._l10n_pe_sign().
        void_tree = self._l10n_pe_sign(company.sudo().l10n_pe_edi_certificate_id, void_tree)

        void_str = etree.tostring(
            void_tree,
            xml_declaration=True,
            encoding='ISO-8859-1'
        )

        # Mostrar XML (preview)
        xml_preview = void_str.decode('utf-8', errors='ignore')
        _logger.warning("XML PREVIEW:\n%s", xml_preview)

        # Guardar XML en disco (CLAVE)
        with open('/tmp/debug_void.xml', 'wb') as f:
            f.write(void_str)

        # =========================
        # ZIP
        # =========================
        zip_filename = '%s.zip' % void_filename
        xml_filename = '%s.xml' % void_filename

        zip_void_str = self._l10n_pe_edi_zip_edi_document([
            (xml_filename, void_str)
        ])

        _logger.warning("ZIP FILENAME: %s", zip_filename)
        _logger.warning("XML FILENAME INSIDE ZIP: %s", xml_filename)
        _logger.warning("ZIP SIZE: %s bytes", len(zip_void_str))

        # Guardar ZIP (MUY IMPORTANTE)
        with open('/tmp/debug_void.zip', 'wb') as f:
            f.write(zip_void_str)

        # =========================
        # ENVÍO A SUNAT
        # =========================
        try:
            settings = Settings(raw_response=True)

            client = Client(
                wsdl=credentials['wsdl'],
                wsse=credentials['token'],
                settings=settings,
            )

            _logger.warning("SENDING TO SUNAT...")

            result = client.service.sendSummary(zip_filename, zip_void_str)

            _logger.warning("HTTP STATUS: %s", result.status_code)

            # Mostrar respuesta cruda
            if result.content:
                response_preview = result.content.decode('utf-8', errors='ignore')[:1000]
                _logger.warning("SUNAT RESPONSE:\n%s", response_preview)

            result.raise_for_status()

        except Exception as e:
            import traceback

            response_text = ''
            if hasattr(e, 'response') and e.response:
                response_text = e.response.content.decode('utf-8', errors='ignore')

            _logger.error("ERROR EN ENVÍO SUNAT")
            _logger.error("ERROR: %s", str(e))
            _logger.error("TRACEBACK:\n%s", traceback.format_exc())

            if response_text:
                _logger.error("SUNAT RESPONSE:\n%s", response_text)

            full_error = str(e)
            if response_text:
                full_error += "\n\nSUNAT RESPONSE:\n" + response_text

            return {
                'error': self._l10n_pe_edi_get_general_error_messages(full_error)['L10NPE08'],
                'blocking_level': 'warning'
            }

        # =========================
        # PROCESAR RESPUESTA
        # =========================
        soap_response = result.content

        soap_response_decoded = self._l10n_pe_edi_decode_soap_response(soap_response)

        if soap_response_decoded.get('error'):
            return {
                'error': soap_response_decoded['error'],
                'blocking_level': 'error',
                'code': soap_response_decoded.get('code')
            }

        cdr_number = soap_response_decoded['number']

        _logger.warning("==== SUNAT DEBUG END ====")

        return {
            'xml_document': void_str,
            'cdr': soap_response,
            'cdr_number': cdr_number
        }

    @api.model
    def _l10n_pe_edi_get_general_error_messages(self, error=None):
        base_msg = _lt("There was an error in the connection or the response from the OSE server. Please try again later.")

        if error:
            return {
                'L10NPE08': base_msg + "<br/><br/><b>DETAIL:</b><br/>" + escape(str(error)).replace('\n', '<br/>'),
                'L10NPE17': _lt("There are problems with the connection to the IAP server. Please try again in a few minutes."),
                'L10NPE18': _lt("The URL provided for the IAP server is wrong, please go to Settings --> System Parameters and add the right URL to parameter l10n_pe_edi.endpoint."),
            }
        else:
            return {
                'L10NPE08': base_msg,
                'L10NPE17': _lt("There are problems with the connection to the IAP server. Please try again in a few minutes."),
                'L10NPE18': _lt("The URL provided for the IAP server is wrong, please go to Settings --> System Parameters and add the right URL to parameter l10n_pe_edi.endpoint."),
            }


    def _l10n_pe_edi_get_edi_values(self, invoice):
        self.ensure_one()
        price_precision = 10
        # self.env['decimal.precision'].precision_get('Product Price')

        def format_float(amount, precision=2):
            ''' Helper to format monetary amount as a string with 2 decimal places. '''
            if amount is None or amount is False:
                return None
            return '%.*f' % (precision, amount)

        spot = invoice._l10n_pe_edi_get_spot()
        invoice_date_due_vals_list = []
        first_time = True
        is_retention = invoice.l10n_pe_edi_retention_type_id
        for rec_line in invoice.line_ids.filtered(lambda l: l.account_type == 'asset_receivable'):
            amount = rec_line.amount_currency
            if spot and first_time:
                amount -= spot['spot_amount']
            if is_retention and first_time:
                amount -= invoice.l10n_pe_edi_total_retention
            first_time = False
            invoice_date_due_vals_list.append({'amount': rec_line.move_id.currency_id.round(amount),
                                               'currency_name': rec_line.move_id.currency_id.name,
                                               'date_maturity': rec_line.date_maturity})
        spot = invoice._l10n_pe_edi_get_spot()
        if not spot:
            total_after_spot = abs(invoice.amount_total)
        else:
            total_after_spot = abs(invoice.amount_total) - spot['spot_amount']

        if is_retention:
            total_after_spot = abs(invoice.amount_total) - invoice.l10n_pe_edi_total_retention
        values = {
            **invoice._prepare_edi_vals_to_export(),
            'spot': spot,
            'total_after_spot': total_after_spot,
            'PaymentMeansID': invoice._l10n_pe_edi_get_payment_means(),
            'is_refund': invoice.move_type in ('out_refund', 'in_refund'),
            'certificate_date': invoice.invoice_date,
            'price_precision': price_precision,
            'format_float': format_float,
            'invoice_date_due_vals_list': invoice_date_due_vals_list,
        }

        # Invoice lines.
        for line_vals in values['invoice_line_vals_list']:
            # raise ValidationError(str(line_vals['line'].price_subtotal))
            line = line_vals['line']
            is_free = line.tax_ids[0].l10n_pe_edi_tax_code in ('9996')
            line_vals['price_unit_type_code'] = '01' if not line.currency_id.is_zero(line_vals['price_unit_after_discount']) else '02'
            line_vals['price_subtotal_unit'] = float_round(line.price_subtotal / line.quantity, precision_digits=price_precision) if line.quantity and not is_free else 0.0
            line_vals['price_total_unit'] = (float_round(line.price_total / line.quantity, precision_digits=price_precision) if line.quantity else 0.0) if not is_free else line_vals['gross_price_total_unit']
            # if is_free:
            #     line_vals['line'].price_subtotal = line_vals['line'].quantity * line_vals['price_total_unit']
            #     line_vals['line'].price_total = line_vals['line'].quantity * line_vals['price_total_unit']
            # raise ValidationError(str(line_vals['line'].price_subtotal)+" / "+str(line_vals['line'].quantity)+' / '+str(line_vals['price_total_unit']))
            # float_round(line.price_total / line.quantity, precision_digits=price_precision) if line.quantity else 0.0
        # raise ValidationError(str(values['invoice_line_vals_list']))
        # Tax details.
        def grouping_key_generator(base_line, tax_data):
            tax = tax_data['tax']
            return {
                'l10n_pe_edi_code': tax.tax_group_id.l10n_pe_edi_code,
                'l10n_pe_edi_international_code': tax.l10n_pe_edi_international_code,
                'l10n_pe_edi_tax_code': tax.l10n_pe_edi_tax_code,
            }

        values['tax_details'] = invoice._prepare_edi_tax_details()
        values['tax_details_grouped'] = invoice._prepare_edi_tax_details(grouping_key_generator=grouping_key_generator)
        values['isc_tax_amount'] = abs(sum([
            line.amount_currency
            for line in invoice.line_ids.filtered(lambda l: l.tax_line_id.tax_group_id.l10n_pe_edi_code == 'ISC')
        ]))
        # (value1, value2) in enumerate(zip(data1, data2)):
        # raise ValidationError(str(values['tax_details_grouped']['tax_details'].values()))
        # for index, (tax_detail, invoice_line) in enumerate(zip(values['tax_details_grouped']['tax_details'], values['invoice_line_vals_list'])):
        # invoice_line = values['invoice_line_vals_list']
        # for tax_detail in values['tax_details_grouped']['tax_details']:
        #     # values['tax_details_grouped']['tax_details'][index]
        #     # raise ValidationError(str(index)+" /AAA/ "+str(tax_detail)+" /AAA/ "+str(invoice_line))
        #     # raise ValidationError(str(tax_detail))
        #     if tax_detail['l10n_pe_edi_tax_code'] == '9996':
        #         tax_detail['base_amount_currency'] = 100
        #         # invoice_line[index]['line'].quantity * invoice_line[index]['line'].price_unit
        #         tax_detail['tax_amount_currency'] = 18
                # tax_detail['base_amount_currency'] * 0.18
        
        # raise ValidationError(str(values['tax_details_grouped']['tax_details']))
        # raise ValidationError(str(values))
        return values
    # _post_invoice_edi
    def _l10n_pe_edi_sign_invoice(self, invoice):
        # OVERRIDE
        #if self.code != 'pe_ubl_2_1':
        #    return super()._l10n_pe_edi_sign_invoice(invoice)

        edi_filename = '%s-%s-%s' % (
            invoice.company_id.vat,
            invoice.l10n_latam_document_type_id.code,
            invoice.name.replace(' ', ''),
        )

        #raise ValidationError(str(self._generate_edi_invoice_bstr(invoice)))

        res = self._l10n_pe_edi_post_invoice_web_service(
            invoice,
            edi_filename,
            self._generate_edi_invoice_bstr(invoice)
        )
        #latam_invoice_type = self._get_latam_invoice_type(invoice.l10n_latam_document_type_id.code)

        #if not latam_invoice_type:
        #    return {invoice: {'error': _("Missing LATAM document code.")}}

        #edi_values = self._l10n_pe_edi_get_edi_values(invoice)
        # if invoice.l10n_latam_document_type_id.code == "01":
            # or invoice.l10n_latam_document_type_id.code == "07"
        # edi_str = self.env.ref('invoice_sunat_soltecn_v16.%s' % latam_invoice_type)._render(edi_values).encode()
        #edi_str = self.env['ir.qweb']._render('invoice_sunat_solyman_v17.%s' % latam_invoice_type, edi_values).encode()
        # else:
        #     edi_str = self.env.ref('l10n_pe_edi.%s' % latam_invoice_type)._render(edi_values).encode()
        # raise ValidationError(str(edi_str))
        #res = self._l10n_pe_edi_post_invoice_web_service(invoice, edi_filename, edi_str)

        return {invoice: res}
    
    # def _l10n_pe_edi_sign_invoices_sunat(self, invoice, edi_filename, edi_str):
    #     """This method calls _l10n_pe_edi_sign_service_sunat() to allow inherit this second from other models"""
    #     return self._l10n_pe_edi_sign_service_sunat(invoice.company_id, edi_filename, edi_str, invoice.l10n_latam_document_type_id.code, invoice=invoice)

    # def _l10n_pe_edi_sign_service_sunat(self, company, edi_filename, edi_str, latam_document_type, serie=False, invoice=False):
    #     credentials = self._l10n_pe_edi_get_sunat_credentials(company)
    #     return self._l10n_pe_edi_sign_service_sunat_digiflow_common(
    #         company, edi_filename, edi_str, credentials, latam_document_type, invoice)

    # def _l10n_pe_edi_sign_invoices_sunat_digiflow_common(self, invoice, edi_filename, edi_str, credentials):
    #     return self._l10n_pe_edi_sign_service_sunat_digiflow_common(
    #         invoice.company_id, edi_filename, edi_str, credentials, invoice.l10n_latam_document_type_id.code, invoice)

    # def _l10n_pe_edi_sign_service_sunat_digiflow_common(self, company, edi_filename, edi_str, credentials, latam_document_type, invoice=False):
    #     if not company.l10n_pe_edi_certificate_id:
    #         return {'error': _("No valid certificate found for %s company.", company.display_name)}

    #     # Sign the document.
    #     edi_tree = objectify.fromstring(edi_str)
    #     edi_tree = company.l10n_pe_edi_certificate_id.sudo()._sign(edi_tree)
    #     error = self.env['ir.attachment']._l10n_pe_edi_check_with_xsd(edi_tree, latam_document_type)
    #     if error:
    #         return {'error': _('XSD validation failed: %s', error), 'blocking_level': 'error'}
    #     edi_str = etree.tostring(edi_tree, xml_declaration=True, encoding='ISO-8859-1')

    #     zip_edi_str = self._l10n_pe_edi_zip_edi_document([('%s.xml' % edi_filename, edi_str)])
    #     transport = Transport(operation_timeout=15, timeout=15)
    #     try:
    #         settings = Settings(raw_response=True)
    #         client = Client(
    #             wsdl=credentials['wsdl'],
    #             wsse=credentials['token'],
    #             settings=settings,
    #             transport=transport,
    #         )
    #         result = client.service.sendBill('%s.zip' % edi_filename, zip_edi_str)
    #         result.raise_for_status()
    #     except ReqConnectionError:
    #         return {'error': self._l10n_pe_edi_get_general_error_messages()['L10NPE08'], 'blocking_level': 'warning'}
    #     except HTTPError:
    #         return {'error': self._l10n_pe_edi_get_general_error_messages()['L10NPE10'], 'blocking_level': 'warning'}
    #     except TypeError:
    #         return {'error': self._l10n_pe_edi_get_general_error_messages()['L10NPE11'], 'blocking_level': 'error'}
    #     except ReadTimeout:
    #         return {'error': self._l10n_pe_edi_get_general_error_messages()['L10NPE12'], 'blocking_level': 'warning'}
    #     soap_response = result.content
    #     soap_response_decoded = self._l10n_pe_edi_decode_soap_response(soap_response) if soap_response else {}

    #     if invoice:
    #         if soap_response_decoded.get('error') and soap_response_decoded.get('code') == "1033":
    #             soap_response_decoded = self._process_cdr_status_web_services(company, invoice.sequence_prefix[:-1], invoice.sequence_number, invoice.l10n_latam_document_type_id.code)

    #     if soap_response_decoded.get('error'):
    #         return {'error': soap_response_decoded['error'], 'blocking_level': 'error'}

    #     cdr = soap_response_decoded['cdr']
    #     cdr_status = self._l10n_pe_edi_extract_cdr_status(cdr)

    #     if cdr_status['code'] != '0':
    #         error_message = '%s<br/><br/><b>%s</b>' % (
    #             cdr_status['description'],
    #             _('This invoice number is now registered by SUNAT as invalid. Duplicate this invoice or create a new invoice to retry.')
    #         )
    #         return {'error': error_message, 'blocking_level': 'error'}

    #     return {'success': True, 'xml_document': edi_str, 'cdr': cdr}

    def _l10n_pe_edi_cdr_status_sunat_digiflow_common(self, company_vat, sequence_prefix, sequence_number, l10n_latam_document_type_code, credentials):
        self.ensure_one()
        transport = Transport(operation_timeout=15, timeout=15)
        try:
            settings = Settings(raw_response=True)
            client = Client(
                wsdl=credentials['wsdl'],
                wsse=credentials['token'],
                settings=settings,
                transport=transport,
            )
            result = client.service.getStatusCdr(company_vat, l10n_latam_document_type_code, sequence_prefix, sequence_number)
            result.raise_for_status()
        except Fault:
            return {'error': self._l10n_pe_edi_get_general_error_messages()['L10NPE07'], 'blocking_level': 'warning'}
        except ConnectionError:
            return {'error': self._l10n_pe_edi_get_general_error_messages()['L10NPE08'], 'blocking_level': 'warning'}
        except HTTPError:
            return {'error': self._l10n_pe_edi_get_general_error_messages()['L10NPE10'], 'blocking_level': 'warning'}
        except TypeError:
            return {'error': self._l10n_pe_edi_get_general_error_messages()['L10NPE11'], 'blocking_level': 'error'}
        except ReadTimeout:
            return {'error': self._l10n_pe_edi_get_general_error_messages()['L10NPE12'], 'blocking_level': 'warning'}
        soap_response = result.content
        return self._l10n_pe_edi_decode_soap_response(soap_response) if soap_response else {}

    def _process_cdr_status_web_services(self, company_id, sequence_prefix, sequence_number, l10n_latam_document_type_code):
        self.ensure_one()
        credentials = self._l10n_pe_edi_get_cdr_status_sunat_credentials(company_id)
        return self._l10n_pe_edi_cdr_status_sunat_digiflow_common(company_id.vat,sequence_prefix, sequence_number, l10n_latam_document_type_code, credentials)

    def _l10n_pe_edi_get_cdr_status_sunat_credentials(self, company):
        self.ensure_one()
        res = {'fault_ns': 'soap-env'}
        if company.l10n_pe_edi_test_env:
            raise ValidationError("Consulta CDR no disponible en modo Test")
        else:
            res.update({
            'wsdl': self._get_cdr_sunat_wsdl(),
            'token': UsernameToken(company.l10n_pe_edi_provider_username, company.l10n_pe_edi_provider_password),
            })
        return res
        
    def _get_cdr_sunat_wsdl(self):
        return io.BytesIO(b'''
            <definitions xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd" xmlns:wsp="http://www.w3.org/ns/ws-policy" xmlns:wsp1_2="http://schemas.xmlsoap.org/ws/2004/09/policy" xmlns:wsam="http://www.w3.org/2007/05/addressing/metadata" xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/" xmlns:tns="http://service.ws.consulta.comppago.electronico.registro.servicio2.sunat.gob.pe/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns="http://schemas.xmlsoap.org/wsdl/" targetNamespace="http://service.ws.consulta.comppago.electronico.registro.servicio2.sunat.gob.pe/" name="billConsultService">
            <import namespace="http://service.sunat.gob.pe" location="https://e-factura.sunat.gob.pe/ol-it-wsconscpegem/billConsultService?wsdl=1"/>
            <binding xmlns:ns1="http://service.sunat.gob.pe" name="BillConsultServicePortBinding" type="ns1:billService">
            <soap:binding transport="http://schemas.xmlsoap.org/soap/http" style="document"/>
            <operation name="getStatusCdr">
            <soap:operation soapAction="urn:getStatusCdr"/>
            <input>
            <soap:body use="literal"/>
            </input>
            <output>
            <soap:body use="literal"/>
            </output>
            </operation>
            <operation name="getStatus">
            <soap:operation soapAction="urn:getStatus"/>
            <input>
            <soap:body use="literal"/>
            </input>
            <output>
            <soap:body use="literal"/>
            </output>
            </operation>
            </binding>
            <service name="billConsultService">
            <port name="BillConsultServicePort" binding="tns:BillConsultServicePortBinding">
            <soap:address location="https://e-factura.sunat.gob.pe/ol-it-wsconscpegem/billConsultService"/>
            </port>
            </service>
            </definitions>''')