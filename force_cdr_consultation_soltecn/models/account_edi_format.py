import base64
import zipfile
import io
from requests.exceptions import ConnectionError, HTTPError, InvalidSchema, InvalidURL, ReadTimeout
from zeep.wsse.username import UsernameToken
from zeep import Client, Settings
from zeep.exceptions import Fault
from zeep.transports import Transport
from lxml import etree
from lxml import objectify
from lxml.objectify import fromstring
from copy import deepcopy
from datetime import date, datetime
from odoo import models, fields, api, _, _lt
from odoo.addons.iap.tools.iap_tools import iap_jsonrpc
from odoo.exceptions import AccessError
from odoo.tools import html_escape
from odoo.exceptions import ValidationError

DEFAULT_BLOCKING_LEVEL = 'error'

class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'
    
    @api.model
    def _l10n_pe_edi_decode_cdr_2_soltecn_check(self, invoice):
        # raise ValidationError(invoice.name)

        edi_filename = '%s-%s-%s' % (
            invoice.company_id.vat,
            invoice.l10n_latam_document_type_id.code,
            invoice.name.replace(' ', ''),
        )

        def _postprocess_post_edi_results(move, edi_result):
            attachments_to_unlink = self.env['ir.attachment']
            # for document in documents:
            #     move = document.move_id
            document = False
            move_result = edi_result.get(move, {})
            document = move.edi_document_ids[0]
            if move_result.get('attachment'):
                if document:
                    old_attachment = document.attachment_id
                    values = {
                        'attachment_id': move_result['attachment'].id,
                        'error': move_result.get('error', False),
                        'blocking_level': move_result.get('blocking_level', DEFAULT_BLOCKING_LEVEL) if 'error' in move_result else False,
                    }
                    if not values.get('error'):
                        values.update({'state': 'sent'})
                    document.write(values)
                    if not old_attachment.res_model or not old_attachment.res_id:
                        attachments_to_unlink |= old_attachment
            else:
                if document:
                    document.write({
                        'error': move_result.get('error', False),
                        'blocking_level': move_result.get('blocking_level', DEFAULT_BLOCKING_LEVEL) if 'error' in move_result else False,
                    })

        latam_invoice_type = self._get_latam_invoice_type(invoice.l10n_latam_document_type_id.code)

        if not latam_invoice_type:
            return {invoice: {'error': _("Missing LATAM document code.")}}

        edi_str = self._generate_edi_invoice_bstr(invoice)

        edi_tree = objectify.fromstring(edi_str)
        edi_tree = invoice.company_id.l10n_pe_edi_certificate_id.sudo()._sign(edi_tree)
        error = self.env['ir.attachment']._l10n_pe_edi_check_with_xsd(edi_tree, invoice.l10n_latam_document_type_id.code)
        if error:
            return {'error': _('XSD validation failed: %s', error), 'blocking_level': 'error'}
        edi_str = etree.tostring(edi_tree, xml_declaration=True, encoding='ISO-8859-1')

        cdr_res = self._process_cdr_status_web_services(invoice.company_id, invoice.sequence_prefix[:-1], invoice.sequence_number, invoice.l10n_latam_document_type_id.code)
        # raise ValidationError(str(cdr_res))
        cdr_decoded_custom = {}
        res = cdr_res
        cdr_str = False
        cdr_decoded = {}

        # if cdr_res.get('cdr'):
        #     cdr_decoded_custom = {'cdr_content_zip': cdr_res['cdr']}       
        # else:
        #     cdr_decoded_custom = cdr_res

        # if cdr_decoded_custom.get('cdr_content_zip'):
        #     cdr_str = cdr_decoded_custom['cdr_content_zip']

        #     if cdr_str:
        #         cdr_decoded = self._l10n_pe_edi_decode_cdr(cdr_str)
        #     if cdr_decoded.get('error'):
        #         res = {'error': cdr_decoded['error'], 'blocking_level': 'error'}
        #     else:
        #         res = {'xml_document': edi_str, 'cdr': cdr_str}
        # else:
        #     if cdr_decoded_custom.get('error'):
        #         res = {'error': cdr_decoded_custom.get('error'), 'blocking_level': 'error'}
        #     else:
        #         res = {'error': "No se pudo procesar solicitud", 'blocking_level': 'error'}

        # # raise ValidationError(str(res))
        result_invoice =  {}
        if res.get('error'):
            result_invoice = {invoice: res}
            # raise ValidationError(str(result_invoice))
            _postprocess_post_edi_results(invoice, result_invoice)

        # Chatter.
        documents = []
        # if res.get('xml_document'):
        #     documents.append(('%s.xml' % edi_filename, res['xml_document']))
        if edi_str:
            documents.append(('%s.xml' % edi_filename, edi_str))
        if res.get('cdr'):
            documents.append(('CDR-%s.xml' % edi_filename, res['cdr']))
        if documents:
            zip_edi_str = self._l10n_pe_edi_zip_edi_document(documents)
            res['attachment'] = self.env['ir.attachment'].create({
                'res_model': invoice._name,
                'res_id': invoice.id,
                'type': 'binary',
                'name': '%s.zip' % edi_filename,
                'datas': base64.encodebytes(zip_edi_str),
                'mimetype': 'application/zip',
            })
            message = _("The EDI document was successfully created and signed by the government.")
            invoice.with_context(no_new_invoice=True).message_post(
                body=message,
                attachment_ids=res['attachment'].ids,
            )

        result_invoice = {invoice: res}

        _postprocess_post_edi_results(invoice, result_invoice)

    # def _l10n_pe_edi_decode_soap_response(self, soap_response):
    #     """
    #     Parse the SOAP response returned by any of the endpoints (IAP, Digiflow or SUNAT)
    #     for any of the SOAP operations (sendBill, getStatus, sendSummary, getStatusCdr),
    #     and extract, if they exist, the error, the response code, the CDR, etc.

    #     Returns a dict which can contain the following fields:
    #     'error': Description of the error (string with HTML format), if the response was a SOAP fault.
    #     'code': Response code (a string), if one was provided.
    #     'message': Description of the response status (a string), if one was provided.
    #     'number': Ticket number (a string) returned by the getSummary endpoint.
    #     'cdr': the CDR (bytes with XML format), if it was provided.
    #     """
    #     # raise ValidationError("texto")
    #     response_tree = etree.fromstring(soap_response)
    #     # raise ValidationError(str(soap_response))
    #     if response_tree.find('.//{*}Fault') is not None:
    #         if response_tree.find('.//{*}message') is not None:  # It comes from Digiflow
    #             message_element, code = self._l10n_pe_edi_response_code_digiflow(response_tree)
    #         else:  # It comes from SUNAT
    #             message_element, code = self._l10n_pe_edi_response_code_sunat(response_tree)
    #         message = message_element.text
    #         error_messages_map = self._l10n_pe_edi_get_cdr_error_messages()
    #         error_message = '%s<br/><br/><b>%s</b><br/>%s|%s' % (
    #             error_messages_map.get(code, _("We got an error response from the OSE. ")),
    #             _('Original message:'),
    #             html_escape(code),
    #             html_escape(message),
    #         )
    #         return {'error': error_message, 'code': code, 'message': message}
    #     if response_tree.find('.//{*}sendBillResponse') is not None:
    #         cdr_b64 = response_tree.find('.//{*}applicationResponse').text
    #         cdr = self._l10n_pe_edi_unzip_edi_document(base64.b64decode(cdr_b64))
    #         return {'cdr': cdr}
    #     if response_tree.find('.//{*}getStatusResponse') is not None:
    #         code = response_tree.find('.//{*}statusCode').text
    #         if response_tree.find('.//{*}content') is not None:
    #             cdr_b64 = response_tree.find('.//{*}content').text
    #             cdr = self._l10n_pe_edi_unzip_edi_document(base64.b64decode(cdr_b64))
    #         else:
    #             cdr = None
    #         return {'code': code, 'cdr': cdr}
    #     if response_tree.find('.//{*}sendSummaryResponse') is not None:
    #         ticket = response_tree.find('.//{*}ticket').text
    #         return {'number': ticket}
    #     if response_tree.find('.//{*}getStatusCdrResponse') is not None:
    #         code = response_tree.find('.//{*}statusCode').text
    #         message = response_tree.find('.//{*}statusMessage').text
    #         # raise ValidationError(str(code) + " / "+ str(message))
    #         if response_tree.find('.//{*}content') is not None:
    #             cdr_b64 = response_tree.find('.//{*}content').text
    #             cdr = self._l10n_pe_edi_unzip_edi_document(base64.b64decode(cdr_b64))
    #             resp =  {'code': code, 'message': message, 'cdr': cdr}
    #             raise ValidationError(str())
    #             return resp
    #         else:
    #             error_messages_map = self._l10n_pe_edi_get_cdr_error_messages()
    #             error_message = '%s<br/><br/><b>%s</b><br/>%s|%s' % (
    #                 error_messages_map.get(code, _("We got an error response from the OSE. ")),
    #                 _('Original message:'),
    #                 html_escape(code),
    #                 html_escape(message),
    #             )
    #             return {'error': error_message, 'code': code, 'message': message}
    #     raise ValidationError(str("TEXT"))
    #     # if response_tree.find('.//{*}statusCdr') is not None:
    #     #     code = response_tree.find('.//{*}statusCode').text
    #     #     if response_tree.find('.//{*}content') is not None:
    #     #         cdr_b64 = response_tree.find('.//{*}content').text
    #     #         cdr = self._l10n_pe_edi_unzip_edi_document(base64.b64decode(cdr_b64))
    #     #     else:
    #     #         cdr = None
    #     #     return {'code': code, 'cdr': cdr}
    #     return {}