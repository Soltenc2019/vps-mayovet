import hashlib
import ssl
from base64 import b64decode, b64encode
from copy import deepcopy
from lxml import etree
from pytz import timezone
from datetime import datetime
from OpenSSL import crypto

from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError

class Certificate(models.Model):
    _inherit = 'l10n_pe_edi.certificate'

    def _sign_referral_guide_xml(self, edi_tree):
        self.ensure_one()
        pem_certificate, pem_private_key, certificate = self._decode_certificate()
        namespaces = {'ds': 'http://www.w3.org/2000/09/xmldsig#'}
        edi_tree_copy = deepcopy(edi_tree)
        signature_element = edi_tree_copy.xpath('.//ds:Signature', namespaces=namespaces)[0]
        signature_element.getparent().remove(signature_element)

        edi_tree_c14n_str = etree.tostring(edi_tree_copy, method='c14n', exclusive=True, with_comments=False)
        digest_b64 = b64encode(hashlib.new('sha1', edi_tree_c14n_str).digest())
        signature_str = self.env['ir.qweb']._render('Guia_Remision_Soltecn_2.pe_ubl_2_1_signature_referral_guide', {'digest_value': digest_b64.decode()})
        # signature_str = self.env.ref('Guia_Remision_Soltecn_2.pe_ubl_2_1_signature_referral_guide')._render({'digest_value': digest_b64.decode()})
        # Eliminate all non useful spaces and new lines in the stream
        signature_str = signature_str.replace('\n', '').replace('  ', '')
        signature_tree = etree.fromstring(signature_str)
        signed_info_element = signature_tree.xpath('.//ds:SignedInfo', namespaces=namespaces)[0]
        signature = etree.tostring(signed_info_element, method='c14n', exclusive=True, with_comments=False)
        private_pem_key = crypto.load_privatekey(crypto.FILETYPE_PEM, pem_private_key)
        signature_b64_hash = b64encode(crypto.sign(private_pem_key, signature, 'sha1'))

        signature_tree.xpath('.//ds:SignatureValue', namespaces=namespaces)[0].text = signature_b64_hash
        signature_tree.xpath('.//ds:X509Certificate', namespaces=namespaces)[0].text = pem_certificate
        signed_edi_tree = deepcopy(edi_tree)
        signature_element = signed_edi_tree.xpath('.//ds:Signature', namespaces=namespaces)[0]
        for child_element in signature_tree:
            signature_element.append(child_element)
        return signed_edi_tree