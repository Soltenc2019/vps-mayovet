import base64
import zipfile
import io
import logging
from requests.exceptions import ConnectionError, HTTPError, InvalidSchema, InvalidURL, ReadTimeout
from zeep.wsse.username import UsernameToken
from zeep import Client, Settings
from zeep.exceptions import Fault
from zeep.transports import Transport
from lxml import etree
from lxml.objectify import fromstring
from copy import deepcopy

from odoo import models, fields, api, _, _lt
from odoo.addons.iap.tools.iap_tools import iap_jsonrpc
from odoo.exceptions import AccessError
from odoo.tools import html_escape
from odoo.exceptions import ValidationError

import requests
from hashlib import sha256
import json

_logger = logging.getLogger(__name__)

DEFAULT_IAP_ENDPOINT = 'https://iap-pe-edi.odoo.com'
DEFAULT_IAP_TEST_ENDPOINT = 'https://l10n-pe-edi-proxy-demo.odoo.com'

class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    def _post_reference_guide_edi(self, reference_guides, test_mode=False):

        reference_guide = reference_guides # Batching is disabled for this EDI.
        provider = reference_guide.company_id.l10n_pe_edi_provider

        edi_filename = '%s-%s-%s-%s' % (
            reference_guide.company_id.vat,
            '09',
            reference_guide.sequence_serial_guide[:4],
            str(reference_guide.sequence_number_guide),
        )
        latam_reference_guide_type = 'pe_ubl_2_1_despatch_advice'
        edi_values = self._l10n_pe_edi_get_gre_values(reference_guide)
        edi_str = self.env['ir.qweb']._render('Guia_Remision_Soltecn_2.%s' % latam_reference_guide_type, edi_values).encode()
        # raise ValidationError(str(edi_str))
        res = getattr(self, '_l10n_pe_edi_sign_referral_guide_%s' % provider)(reference_guide, edi_filename, edi_str)

        if res.get('error'):
            return {reference_guide: res}
        return {reference_guide: res}

    def _post_check_ticket_reference_guide_edi(self, reference_guides, test_mode=False):
        reference_guide = reference_guides # Batching is disabled for this EDI.
        provider = reference_guide.company_id.l10n_pe_edi_provider
        edi_filename = '%s-%s-%s-%s' % (
            reference_guide.company_id.vat,
            '09',
            reference_guide.sequence_serial_guide[:4],
            str(reference_guide.sequence_number_guide),
        )

        res = getattr(self, '_l10n_pe_edi_check_ticket_referral_guide_%s' % provider)(reference_guide)
        # Chatter.
        documents = []
        if res.get('cdr'):
            documents.append(('CDR-%s.xml' % edi_filename, res['cdr']))
        if documents:
            zip_edi_str = self._l10n_pe_edi_zip_edi_document(documents)
            res['attachment'] = self.env['ir.attachment'].create({
                'res_model': reference_guide._name,
                'res_id': reference_guide.id,
                'type': 'binary',
                'name': '%s.zip' % edi_filename,
                'datas': base64.encodebytes(zip_edi_str),
                'mimetype': 'application/zip',
            })
            message = _("El documento de guía de remisión peruano fue creado y firmado correctamente por la SUNAT.")
            reference_guide.with_context(no_new_reference_guide=True).message_post(
                body=message,
                attachment_ids=res['attachment'].ids,
            )
        return {reference_guide: res}

    def _l10n_pe_edi_get_gre_values(self, reference_guide):
        self.ensure_one()
        # specify_weight = reference_guide.company_id.specify_weight
        # if specify_weight:
        #     if any(map(lambda x: not x.weight, reference_guide.move_ids_without_package.filtered(lambda ml: ml.quantity_done > 0).product_id)):
        #         raise ValidationError("Es necesario ingresar el peso de todos los productos transportados.")
        def format_float(amount, precision=3):
            ''' Helper to format monetary amount as a string with 2 decimal places. '''
            if amount is None or amount is False:
                return None
            return '%.*f' % (precision, amount)

        certificate_date = self.env['l10n_pe_edi.certificate']._get_pe_current_datetime()
        values = {
            'record': reference_guide,
            'line_vals': [],
            'grossWeightMeasure': format_float(float(reference_guide.gross_weight_measure)),
            'netWeightMeasure': format_float(float(reference_guide.net_weight_measure)),
            'certificate_date': certificate_date.date(),
            'certificate_hour': certificate_date.strftime("%H:%M:%S"),
            'type_aero_port_location': dict(reference_guide.SELECTION_AERO_PORT_LOCATION)[reference_guide.type_aero_port_location] if reference_guide.type_aero_port_location else False,
        }

        # reference_guide_lines = reference_guide.move_ids_without_package.filtered(lambda ml: ml.quantity_done > 0)
        reference_guide_lines = reference_guide.move_line_ids.filtered(lambda d: not d.result_package_id).mapped('move_id')
        # .sale_id.order_line
        # if reference_guide.transportation_reason in ('08','09') and reference_guide.total_transport_handling_unit_quantity not in ('',False):
        # # if reference_guide.indicador_traslado_total_damods:reference_guide
        #     for i, line in enumerate(reference_guide.stock_group, start=1):
        #         values["line_vals"].append({
        #             "id": i,
        #             "product_uom":line.group_uom.l10n_pe_edi_measure_unit_code,
        #             "product_uom_dam_ds":line.group_uom.measure_unit_code_dam_ds,
        #             "product_uom_qty":line.quantity,
        #             "name":line.name,
        #             "product_id":line.id,
        #             'damds_number': False,
        #             'damds_serie': False,
        #             'unspsc_code_id': False,
        #         })
        # else:
        index_guide_lines = 1
        for line in reference_guide_lines:
            values["line_vals"].append({
                "id": index_guide_lines,
                "product_uom":line.product_uom.l10n_pe_edi_measure_unit_code,
                "product_uom_dam_ds":line.product_uom.measure_unit_code_dam_ds,
                "product_uom_qty":line.quantity,
                "name":line.name,
                "product_id":line.product_id.id,
                'damds_number': line.damds_number,
                'damds_serie': line.damds_serie,
                'unspsc_code_id': line.product_id.unspsc_code_id,
            })
            index_guide_lines+=1
        if reference_guide.has_packages:
            for package in reference_guide.move_line_ids.mapped('result_package_id'):
                values["line_vals"].append({
                "id": index_guide_lines,
                "product_uom": package.package_type_id.package_type_uom.l10n_pe_edi_measure_unit_code,
                "product_uom_dam_ds": package.package_type_id.package_type_uom.measure_unit_code_dam_ds,
                "product_uom_qty": 1,
                "name": package.package_type_id.name,
                "product_id": package.id,
                'damds_number': False,
                'damds_serie': False,
                'unspsc_code_id': False,
                })
                index_guide_lines+=1
            # values["grossWeightMeasure"] = format_float(float(values["grossWeightMeasure"])+line.product_id.weight)
        if values["grossWeightMeasure"] == "0.000":
            values["grossWeightMeasure"] = format_float(0.001)
        return values
    

    def _l10n_pe_edi_sign_referral_guide_sunat(self, referral_guide, edi_filename, edi_str):
        return self._l10n_pe_edi_sign_referral_guide_sunat_digiflow_common_rest(referral_guide, edi_filename, edi_str)
    
    def _l10n_pe_edi_check_ticket_referral_guide_sunat(self, referral_guide):
        return self._l10n_pe_edi_check_ticket_referral_guide_sunat_digiflow_common_rest(referral_guide)

    def _l10n_pe_edi_sign_referral_guide_sunat_digiflow_common_rest(self, referral_guide, edi_filename, edi_str):
        self.ensure_one()
        if not referral_guide.company_id.access_token:
            return self._l10n_pe_edi_update_token_gre_api_rest(referral_guide)
        url = f"https://api-cpe.sunat.gob.pe/v1/contribuyente/gem/comprobantes/{referral_guide.company_id.vat}-09-{referral_guide.sequence_serial_guide[:4]}-{int(referral_guide.sequence_number_guide)}"
        headers = {
            "Authorization": "Bearer "+referral_guide.company_id.access_token,
            'Content-type': 'application/json',
        }

        edi_tree = fromstring(edi_str)
        edi_tree = referral_guide.company_id.l10n_pe_edi_certificate_id.sudo()._sign_referral_guide_xml(edi_tree)
        error = self.env['ir.attachment']._l10n_pe_edi_check_with_xsd(edi_tree, '09')
        if error:
            return {'error': _('XSD validation failed: %s', error), 'blocking_level': 'error'}
        edi_str = etree.tostring(edi_tree, xml_declaration=True, encoding='UTF-8')
        zip_edi_str = self._l10n_pe_edi_zip_edi_document([('%s.xml' % edi_filename, edi_str)])
        hash_zip_edi_str = self._l10n_pe_edi_hash_sha256_edi_document(zip_edi_str)

        params = {
            "archivo":{
                "nomArchivo": edi_filename+".zip",
                "arcGreZip": base64.encodebytes(zip_edi_str).decode('utf-8').replace("\n",""),
                "hashZip": hash_zip_edi_str,
            }
        }

        response = requests.post(url, data=json.dumps(params), headers=headers)

        tipo_error = ""
        description = ""
        response_num_ticket = ""
        fec_recepcion = ""
        if response.status_code == 401:
            return self._l10n_pe_edi_update_token_gre_api_rest(referral_guide)
        elif response.status_code == 200:
            resultado_json = response.json()
            response_num_ticket = resultado_json.get('numTicket')
            fec_recepcion = resultado_json.get('fecRecepcion')
            return {'response_num_ticket': response_num_ticket, 'fec_recepcion': fec_recepcion}
        elif response.status_code == 422:
            resultado_json = response.json()
            tipo_error = str(resultado_json.get('cod'))
            description = resultado_json.get('msg')
            for error in resultado_json.get('errors'):
                description = description + " / ("+ str(error.get('cod'))+") "+error.get('msg')
            return {'error': description, 'blocking_level': tipo_error}
        elif response.status_code == 204:
            return {'error': "(Api) Sin contenido de error", 'blocking_level': "204"}
        else:
            resultado_json = response.json()
            tipo_error = resultado_json.get('cod')
            description = resultado_json.get('msg')
            return {'error': description, 'blocking_level': tipo_error}
    
    def _l10n_pe_edi_sign_referral_guide_sunat_digiflow_common_rest(self, referral_guide, edi_filename, edi_str):
        self.ensure_one()
        if not referral_guide.company_id.access_token:
            return self._l10n_pe_edi_update_token_gre_api_rest(referral_guide)

        url = f"https://api-cpe.sunat.gob.pe/v1/contribuyente/gem/comprobantes/{referral_guide.company_id.vat}-09-{referral_guide.sequence_serial_guide[:4]}-{int(referral_guide.sequence_number_guide)}"
        headers = {
            "Authorization": "Bearer " + referral_guide.company_id.access_token,
            "Content-type": "application/json",
        }

        edi_tree = fromstring(edi_str)
        edi_tree = referral_guide.company_id.l10n_pe_edi_certificate_id.sudo()._sign_referral_guide_xml(edi_tree)
        error = self.env["ir.attachment"]._l10n_pe_edi_check_with_xsd(edi_tree, "09")
        if error:
            return {"error": _("XSD validation failed: %s", error), "blocking_level": "error"}

        edi_str = etree.tostring(edi_tree, xml_declaration=True, encoding="UTF-8")
        zip_edi_str = self._l10n_pe_edi_zip_edi_document([(f"{edi_filename}.xml", edi_str)])
        hash_zip_edi_str = self._l10n_pe_edi_hash_sha256_edi_document(zip_edi_str)

        params = {
            "archivo": {
                "nomArchivo": edi_filename + ".zip",
                "arcGreZip": base64.encodebytes(zip_edi_str).decode("utf-8").replace("\n", ""),
                "hashZip": hash_zip_edi_str,
            }
        }

        response = requests.post(url, data=json.dumps(params), headers=headers)

        tipo_error = ""
        description = ""
        response_num_ticket = ""
        fec_recepcion = ""

        # Caso: Token expirado
        if response.status_code == 401:
            return self._l10n_pe_edi_update_token_gre_api_rest(referral_guide)

        # Intentar leer el JSON de manera segura
        try:
            resultado_json = response.json()
        except ValueError:
            _logger.error("Error al decodificar respuesta JSON de SUNAT/Digiflow.")
            _logger.error("Código HTTP: %s", response.status_code)
            _logger.error("Respuesta completa: %s", response.text)
            return {
                "error": f"No se pudo interpretar la respuesta del servicio. Código HTTP {response.status_code}",
                "blocking_level": "critical",
            }

        # Procesar respuestas válidas
        if response.status_code == 200:
            response_num_ticket = resultado_json.get("numTicket")
            fec_recepcion = resultado_json.get("fecRecepcion")
            return {"response_num_ticket": response_num_ticket, "fec_recepcion": fec_recepcion}

        elif response.status_code == 422:
            tipo_error = str(resultado_json.get("cod"))
            description = resultado_json.get("msg")
            for error in resultado_json.get("errors", []):
                description += f" / ({error.get('cod')}) {error.get('msg')}"
            return {"error": description, "blocking_level": tipo_error}

        elif response.status_code == 204:
            return {"error": "(Api) Sin contenido de error", "blocking_level": "204"}

        else:
            tipo_error = resultado_json.get("cod")
            description = resultado_json.get("msg")
            return {"error": description, "blocking_level": tipo_error}

    def _l10n_pe_edi_check_ticket_referral_guide_sunat_digiflow_common_rest(self, referral_guide):
        self.ensure_one()
        if not referral_guide.company_id.access_token:
            return self._l10n_pe_edi_update_token_gre_api_rest(referral_guide)
        url = f"https://api-cpe.sunat.gob.pe/v1/contribuyente/gem/comprobantes/envios/{referral_guide.response_num_ticket}"
        # raise ValidationError(str(url))
        headers = {
            "Authorization": "Bearer "+referral_guide.company_id.access_token,
        }
        response = requests.get(url, headers=headers)
        tipo_error = ""
        description = ""
        response_num_ticket = ""
        fec_recepcion = ""
        if response.status_code == 401:
            return self._l10n_pe_edi_update_token_gre_api_rest(referral_guide)
        elif response.status_code == 200:
            resultado_json = response.json()
            if resultado_json.get('codRespuesta') == "0":
                if resultado_json.get('arcCdr'):
                    cdr_api_rest_decoded = self._l10n_pe_edi_decode_cd_api_rest(resultado_json.get('arcCdr'))
                    referral_guide_QR = False
                    cdr_content_str = cdr_api_rest_decoded.get('cdr_content_zip')
                    nota_cdr_warning = False
                    try:
                        cdr_tree = etree.fromstring(cdr_content_str)
                        url_qr_hash = cdr_tree.find('.//{*}DocumentReference//{*}DocumentDescription')
                        nota_cdr_warning_cdr = cdr_tree.find('.//{*}Note')
                        if nota_cdr_warning_cdr is not None:
                            nota_cdr_warning = nota_cdr_warning_cdr.text
                        if url_qr_hash is not None:
                            referral_guide_QR = url_qr_hash.text
                    except Exception:
                        referral_guide_QR = False
                    return {'cdr': cdr_api_rest_decoded.get('cdr_content_zip'), 'referral_guide_QR': referral_guide_QR, 'blocking_level': "(Warning)" + nota_cdr_warning}
                else:
                    return {'error': "No se genera CDR", 'blocking_level': "0"}
            elif resultado_json.get('codRespuesta') == "98":
                return {'blocking_level': "98 - Envio en proceso"}
            elif resultado_json.get('codRespuesta') == "99":
                error_with_cdr = ""
                if resultado_json.get('error'):
                    error_with_cdr_inside = resultado_json.get('error')
                    error_with_cdr = error_with_cdr + " / ("+error_with_cdr_inside.get('numError')+") "+error_with_cdr_inside.get('desError')
                if resultado_json.get('arcCdr'):
                    return {'error': "Envio con error, con generacion de CDR"+error_with_cdr, 'blocking_level': "99"}
                return {'error': "Envio con error, no genera CDR"+ error_with_cdr, 'blocking_level': "99"}
        elif response.status_code == 422:
            resultado_json = response.json()
            tipo_error = str(resultado_json.get('cod'))
            description = resultado_json.get('msg')
            for error in resultado_json.get('errors'):
                description = description + " / ("+ str(error.get('cod'))+") "+error.get('msg')
            return {'error': description, 'blocking_level': tipo_error}
        elif response.status_code == 204:
            return {'blocking_level': "(Api) Sin contenido de error - 204"}
        else:
            resultado_json = response.json()
            tipo_error = resultado_json.get('cod')
            description = resultado_json.get('msg')
            return {'error': description, 'blocking_level': tipo_error}

    # def _l10n_pe_edi_check_ticket_referral_guide_sunat_digiflow_common_rest(self, referral_guide):
    #     self.ensure_one()
    #     if not referral_guide.company_id.access_token:
    #         return self._l10n_pe_edi_update_token_gre_api_rest(referral_guide)
    #     url = f"https://api-cpe.sunat.gob.pe/v1/contribuyente/gem/comprobantes/envios/{referral_guide.response_num_ticket}"
    #     # raise ValidationError(str(url))
    #     headers = {
    #         "Authorization": "Bearer "+referral_guide.company_id.access_token,
    #     }
    #     response = requests.get(url, headers=headers)
    #     tipo_error = ""
    #     description = ""
    #     response_num_ticket = ""
    #     fec_recepcion = ""
    #     if response.status_code == 401:
    #         return self._l10n_pe_edi_update_token_gre_api_rest(referral_guide)
    #     elif response.status_code == 200:
    #         resultado_json = response.json()
    #         if resultado_json.get('codRespuesta') == "0":
    #             if resultado_json.get('arcCdr'):
    #                 cdr_api_rest_decoded = self._l10n_pe_edi_decode_cd_api_rest(resultado_json.get('arcCdr'))
    #                 referral_guide_QR = False
    #                 cdr_content_str = cdr_api_rest_decoded.get('cdr_content_zip')
    #                 nota_cdr_warning = False
    #                 nota_cdr_warning_str = ""
    #                 try:
    #                     cdr_tree = etree.fromstring(cdr_content_str)
    #                     url_qr_hash = cdr_tree.find('.//{*}DocumentReference//{*}DocumentDescription')
    #                     nota_cdr_warning_cdr = cdr_tree.find('.//{*}Note')
    #                     if nota_cdr_warning_cdr is not None:
    #                         nota_cdr_warning = nota_cdr_warning_cdr.text
    #                     if url_qr_hash is not None:
    #                         referral_guide_QR = url_qr_hash.text
    #                 except Exception:
    #                     referral_guide_QR = False
    #                     nota_cdr_warning_str = str(nota_cdr_warning)  if isinstance(nota_cdr_warning, bool) else ""
    #                 return {'cdr': cdr_api_rest_decoded.get('cdr_content_zip'), 'referral_guide_QR': referral_guide_QR, 'blocking_level': "(Warning)" + nota_cdr_warning_str}
    #             else:
    #                 return {'error': "No se genera CDR", 'blocking_level': "0"}
    #         elif resultado_json.get('codRespuesta') == "98":
    #             return {'blocking_level': "98 - Envio en proceso"}
    #         elif resultado_json.get('codRespuesta') == "99":
    #             error_with_cdr = ""
    #             if resultado_json.get('error'):
    #                 error_with_cdr_inside = resultado_json.get('error')
    #                 error_with_cdr = error_with_cdr + " / ("+error_with_cdr_inside.get('numError')+") "+error_with_cdr_inside.get('desError')
    #             if resultado_json.get('arcCdr'):
    #                 return {'error': "Envío con error, con generación de CDR"+error_with_cdr, 'blocking_level': "99"}
    #             return {'error': "Envio con error, no genera CDR"+ error_with_cdr, 'blocking_level': "99"}
    #     elif response.status_code == 422:
    #         resultado_json = response.json()
    #         tipo_error = str(resultado_json.get('cod'))
    #         description = resultado_json.get('msg')
    #         for error in resultado_json.get('errors'):
    #             description = description + " / ("+ str(error.get('cod'))+") "+error.get('msg')
    #         return {'error': description, 'blocking_level': tipo_error}
    #     elif response.status_code == 204:
    #         return {'blocking_level': "(Api) Sin contenido de error - 204"}
    #     else:
    #         resultado_json = response.json()
    #         tipo_error = resultado_json.get('cod')
    #         description = resultado_json.get('msg')
    #         return {'error': description, 'blocking_level': tipo_error}

    def _l10n_pe_edi_update_token_gre_api_rest(self, referral_guide):
        self.ensure_one()
        if not referral_guide.company_id.client_id or not referral_guide.company_id.client_secret or not referral_guide.company_id.usuario_sol or not referral_guide.company_id.contrasenia_sol:
            raise ValidationError("Datos insuficientes para conexión api rest SUNAT - comunicarse al contacto de soporte")
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": referral_guide.company_id.grant_type,
            "scope": referral_guide.company_id.scope,
            "client_id": referral_guide.company_id.client_id,
            "client_secret": referral_guide.company_id.client_secret,
            "username": referral_guide.company_id.usuario_sol,
            "password": referral_guide.company_id.contrasenia_sol,
        }
        url = f"https://api-seguridad.sunat.gob.pe/v1/clientessol/{referral_guide.company_id.client_id}/oauth2/token/"
        response = requests.post(url, data=data, headers=headers)

        tipo_error = ""
        description = ""
        response_num_ticket = ""
        fec_recepcion = ""
        
        if response.status_code == 200:
            resultado_json = response.json()
            access_token = resultado_json.get('access_token')
            company_id = self.env["res.company"].search([("id", "=", referral_guide.company_id.id)], limit=1)
            values = {
                "access_token": access_token
            }
            company_id.write(values)
            return {'error': "(Api) Token nuevo generado - Vuelva a enviar el documento", 'blocking_level': "401", 'api': True}
        elif response.status_code == 422:
            resultado_json = response.json()
            tipo_error = str(resultado_json.get('cod'))
            description = resultado_json.get('msg')
            for error in resultado_json.get('errors'):
                description = description + " / ("+ str(error.get('cod'))+") "+error.get('msg')
            return {'error': "(Api)"+ description, 'blocking_level': tipo_error, 'api': True}
        elif response.status_code == 204:
            return {'error': "(Api) Sin contenido de error", 'blocking_level': "204", 'api': True}
        else:
            resultado_json = response.json()
            tipo_error = resultado_json.get('cod')
            description = resultado_json.get('msg')
            return {'error': "(Api)" + description, 'blocking_level': tipo_error, 'api': True}

    @api.model
    def _l10n_pe_edi_decode_cd_api_rest(self, cdr_str):
        self.ensure_one()
        cdr_content_str = self._l10n_pe_edi_unzip_edi_document_cdr(base64.b64decode(cdr_str))
        return {'cdr_content_zip': cdr_content_str}

    @api.model
    def _l10n_pe_edi_hash_sha256_edi_document(self, zip_edi_str):
        hash_string = sha256(zip_edi_str)
        return hash_string.hexdigest()
    
    @api.model
    def _l10n_pe_edi_unzip_edi_document_cdr(self, zip_str):
        buffer = io.BytesIO(zip_str)
        zipfile_obj = zipfile.ZipFile(buffer)
        filename = ""
        for name in zipfile_obj.namelist():
            if "R" in name:
                filename = name
                break
        # filename = zipfile_obj.namelist()[1]
        content = zipfile_obj.read(filename)
        buffer.close()
        return content