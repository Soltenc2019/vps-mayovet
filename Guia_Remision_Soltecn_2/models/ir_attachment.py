# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import io
import logging
import zipfile
import requests
from requests.exceptions import RequestException
from lxml import etree, objectify

from odoo import _, models, tools
from odoo.tools import xml_utils
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'
    
    def _l10n_pe_edi_get_xsd_file_name(self):
        res = super(IrAttachment, self)._l10n_pe_edi_get_xsd_file_name()
        res.update({'09': 'UBL-DespatchAdvice-2.1.xsd'})
        return res
        
    # def _l10n_pe_edi_check_with_xsd(self, xml_to_validate, validation_type):
    #     """
    #     This method validates the format description of the xml files

    #     :param xml_to_validate: xml to validate
    #     :param validation_type: the type of the document
    #     :return: empty string when file not found or XSD passes
    #      or the error when the XSD validation fails
    #     """
    #     validation_types = {
    #         '01': 'UBL-Invoice-2.1.xsd',
    #         '03': 'UBL-Invoice-2.1.xsd',
    #         '07': 'UBL-CreditNote-2.1.xsd',
    #         '08': 'UBL-DebitNote-2.1.xsd',
    #         '09': 'UBL-DespatchAdvice-2.1.xsd'
    #     }
    #     xsd_fname = validation_types[validation_type]
    #     try:
    #         xml_utils._check_with_xsd(xml_to_validate, xsd_fname, self.env)
    #         return ''
    #     except FileNotFoundError:
    #         _logger.info('The XSD validation files from Sunat has not been found, please run the cron manually. ')
    #         return ''
    #     except UserError as exc:
    #         return str(exc)