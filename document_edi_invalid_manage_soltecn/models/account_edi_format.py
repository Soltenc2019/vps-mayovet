# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import zipfile
import io
from requests.exceptions import ConnectionError as ReqConnectionError, HTTPError, InvalidSchema, InvalidURL, ReadTimeout
from zeep.wsse.username import UsernameToken
from zeep import Client, Settings
from zeep.transports import Transport
from lxml import etree
from lxml import objectify
from copy import deepcopy

from odoo import models, api, _, _lt
from odoo.addons.iap.tools.iap_tools import iap_jsonrpc
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import float_round, html_escape

DEFAULT_IAP_ENDPOINT = 'https://iap-pe-edi.odoo.com'
DEFAULT_IAP_TEST_ENDPOINT = 'https://l10n-pe-edi-proxy-demo.odoo.com'


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    # def _l10n_pe_edi_post_invoice_web_service(self, invoice, edi_filename, edi_str):
    #     res =  super()._l10n_pe_edi_post_invoice_web_service(invoice, edi_filename, edi_str)
    #     # raise ValidationError(str(res))
    #     # CDR error codes 2000 and 3999 mean that the invoice is invalid in SUNAT.
    #     if res.get('error') and res.get('code') and res.get('code').isdigit() and int(res.get('code')) in range(2000, 4000):
    #         res.update({
    #             'error': '%s<br/>%s<br/>%s' % (res['error'], 'Código: '+ res.get('code'), 'Comprobante marcado como invalido, debe ser enviado con una nueva serie, con su respectiva corrección a error mencionado.'),
    #             'blocking_level': 'invalid',
    #             })
    #     # raise ValidationError(str(res) + " / FFFFF" )
    #     return res
    
    # def _l10n_pe_edi_sign_service_sunat_digiflow_common(self, company, edi_filename, edi_str, credentials, latam_document_type):
    #     if not company.l10n_pe_edi_certificate_id:
    #         return {'error': _("No valid certificate found for %s company.", company.display_name)}

    #     # Sign the document.
    #     edi_tree = objectify.fromstring(edi_str)
    #     edi_tree = company.l10n_pe_edi_certificate_id.sudo()._sign(edi_tree)
    #     error = self.env['ir.attachment']._l10n_pe_edi_check_with_xsd(edi_tree, latam_document_type)
    #     if error:
    #         return {'error': _('XSD validation failed: %s', error), 'blocking_level': 'error'}
    #     edi_str = etree.tostring(edi_tree, xml_declaration=True, encoding='ISO-8859-1')

    #     # zip_edi_str = self._l10n_pe_edi_zip_edi_document([('%s.xml' % edi_filename, edi_str)])
    #     # transport = Transport(operation_timeout=15, timeout=15)
    #     # try:
    #     #     settings = Settings(raw_response=True)
    #     #     client = Client(
    #     #         wsdl=credentials['wsdl'],
    #     #         wsse=credentials['token'],
    #     #         settings=settings,
    #     #         transport=transport,
    #     #     )
    #     #     result = client.service.sendBill('%s.zip' % edi_filename, zip_edi_str)
    #     #     result.raise_for_status()
    #     # except ReqConnectionError:
    #     #     return {'error': self._l10n_pe_edi_get_general_error_messages()['L10NPE08'], 'blocking_level': 'warning'}
    #     # except HTTPError:
    #     #     return {'error': self._l10n_pe_edi_get_general_error_messages()['L10NPE10'], 'blocking_level': 'warning'}
    #     # except TypeError:
    #     #     return {'error': self._l10n_pe_edi_get_general_error_messages()['L10NPE11'], 'blocking_level': 'error'}
    #     # except ReadTimeout:
    #     #     return {'error': self._l10n_pe_edi_get_general_error_messages()['L10NPE12'], 'blocking_level': 'warning'}
    #     # soap_response = result.content
    #     # soap_response_decoded = self._l10n_pe_edi_decode_soap_response(soap_response) if soap_response else {}

    #     soap_response_decoded = {
    #         'code': '1999',
    #         'error': 'El dato ingresado en el tipo de documento de identidad del receptor no esta permitido. - Detalle: xxx.xxx.xxx value=\'ticket: 1623742208882 error: INFO : 1999',
    #     }

    #     if soap_response_decoded.get('error'):
    #         return {'error': soap_response_decoded['error'], 'blocking_level': 'error',
    #                 'code': soap_response_decoded.get('code'), 'xml_document': edi_str}

    #     cdr = soap_response_decoded['cdr']
    #     cdr_status = self._l10n_pe_edi_extract_cdr_status(cdr)

    #     if cdr_status['code'] != '0':
    #         error_message = '%s<br/><br/><b>%s</b>' % (
    #             cdr_status['description'],
    #             _('This document number is now registered by SUNAT as invalid.')
    #         )
    #         return {'error': error_message, 'blocking_level': 'error',
    #                 'code': cdr_status['code'], 'xml_document': edi_str}

    #     return {'success': True, 'xml_document': edi_str, 'cdr': cdr}