from base64 import b64encode
from copy import deepcopy
from hashlib import sha1

from lxml import etree

from odoo import models


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    def _l10n_pe_sign_referral_guide(self, certificate, edi_tree):
        """Firma la guía de remisión electrónica (GRE).

        Odoo 18 eliminó el modelo `l10n_pe_edi.certificate`: los certificados
        viven ahora en `certificate.certificate` y la firma se hace desde
        `account.edi.format`. Este método replica `_l10n_pe_sign` del núcleo
        pero usando la plantilla de firma de la guía de remisión.
        """
        namespaces = {'ds': 'http://www.w3.org/2000/09/xmldsig#'}

        edi_tree_copy = deepcopy(edi_tree)
        signature_element = edi_tree_copy.xpath('.//ds:Signature', namespaces=namespaces)[0]
        signature_element.getparent().remove(signature_element)

        edi_tree_c14n_str = etree.tostring(edi_tree_copy, method='c14n', exclusive=True, with_comments=False)
        digest_b64 = b64encode(sha1(edi_tree_c14n_str).digest())
        signature_str = self.env['ir.qweb']._render(
            'Guia_Remision_Soltecn_2.pe_ubl_2_1_signature_referral_guide',
            {'digest_value': digest_b64.decode()},
        )

        # Eliminar espacios y saltos de línea no útiles del flujo.
        signature_str = signature_str.replace('\n', '').replace('  ', '')

        signature_tree = etree.fromstring(signature_str)
        signed_info_element = signature_tree.xpath('.//ds:SignedInfo', namespaces=namespaces)[0]
        signature = etree.tostring(signed_info_element, method='c14n', exclusive=True, with_comments=False)
        signature_b64_hash = certificate._sign(signature, hashing_algorithm='sha1', formatting='base64')

        signature_tree.xpath('.//ds:SignatureValue', namespaces=namespaces)[0].text = signature_b64_hash
        signature_tree.xpath('.//ds:X509Certificate', namespaces=namespaces)[0].text = \
            certificate._get_der_certificate_bytes(formatting='base64')

        signed_edi_tree = deepcopy(edi_tree)
        signature_element = signed_edi_tree.xpath('.//ds:Signature', namespaces=namespaces)[0]
        for child_element in signature_tree:
            signature_element.append(child_element)
        return signed_edi_tree
