from collections import defaultdict
from lxml import etree

from odoo import models, _
from odoo.tools import html2plaintext, cleanup_xml_node
from odoo.exceptions import ValidationError

FREE_AFFECTATION_REASONS = ['11', '12', '13', '14', '15', '16', '21', '31', '32', '33', '34', '35', '36']

class AccountEdiXmlUBLPE(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl_pe'

    def _export_invoice_vals(self, invoice):
        # EXTENDS account.edi.xml.ubl_pe
        vals = super()._export_invoice_vals(invoice)

        vals.update({
            'InvoiceType_template': 'invoice_sunat_soltecn_v16.ubl_pe_21_InvoiceType',
            'CreditNoteType_template': 'invoice_sunat_soltecn_v16.ubl_pe_21_CreditNoteType',
            'DebitNoteType_template': 'invoice_sunat_soltecn_v16.ubl_pe_21_DebitNoteType',
        })

        retention_vals = invoice._l10n_pe_edi_get_retention()
        if retention_vals:
            vals['vals']['retention_vals'] = retention_vals

        downpayments_vals = invoice._l10n_pe_edi_get_reference_downpayments()
        if downpayments_vals:
            vals['vals']['downpayments_vals'] = retention_vals

        taxes_vals = invoice._prepare_invoice_aggregated_taxes(
            grouping_key_generator=self._get_tax_grouping_key,
            filter_tax_values_to_apply=self._apply_invoice_tax_filter,
            filter_invl_to_apply=self._apply_invoice_line_filter,
            round_from_tax_lines=True,
        )

        # Fixed Taxes: filter them on the document level, and adapt the totals
        # Fixed taxes are not supposed to be taxes in real live. However, this is the way in Odoo to manage recupel
        # taxes in Belgium. Since only one tax is allowed, the fixed tax is removed from totals of lines but added
        # as an extra charge/allowance.
        fixed_taxes_keys = [k for k in taxes_vals['tax_details'] if k['tax_amount_type'] == 'fixed']
        for key in fixed_taxes_keys:
            fixed_tax_details = taxes_vals['tax_details'].pop(key)
            taxes_vals['tax_amount_currency'] -= fixed_tax_details['tax_amount_currency']
            taxes_vals['tax_amount'] -= fixed_tax_details['tax_amount']
            taxes_vals['base_amount_currency'] += fixed_tax_details['tax_amount_currency']
            taxes_vals['base_amount'] += fixed_tax_details['tax_amount']


        invoice_lines = invoice.invoice_line_ids.filtered(
            lambda line: line.display_type not in ('line_note', 'line_section') and line.quantity >= 0
        )

        invoice_line_vals_list = []

        for line_id, line in enumerate(invoice_lines):
            line_taxes_vals = taxes_vals['tax_details_per_record'][line]
            line_vals = self._get_invoice_line_vals(line, line_id, {**line_taxes_vals, 'invoice_line': line})
            invoice_line_vals_list.append(line_vals)

        if downpayments_vals:
            vals['vals']['downpayments_vals'] = downpayments_vals

        vals['vals']['line_vals'] = invoice_line_vals_list

        amount_to_add = 0
        amount_tax_to_fix = 0

        for line in invoice.invoice_line_ids:
            if (
                line.tax_ids and
                line.tax_ids[0].l10n_pe_edi_tax_code == '9996' and
                line.discount == 100.00 and
                line.l10n_pe_edi_affectation_reason == '37'
            ):
                amount_to_add += line.quantity * line.price_unit
                
                # Buscar el tax_total correspondiente a GRA (id: 9996)
        
        if amount_to_add != 0:
            for tax_total in vals['vals'].get('tax_total_vals', []):
                for tax_subtotal in tax_total.get('tax_subtotal_vals', []):
                    tax_category = tax_subtotal.get('tax_category_vals', {})
                    tax_scheme = tax_category.get('tax_scheme_vals', {})
                            
                    if tax_scheme.get('id') == '9996' and tax_scheme.get('name') == 'GRA':
                        # Sumar el monto al taxable_amount
                        tax_subtotal['taxable_amount'] = amount_to_add
                        if tax_subtotal['tax_amount'] != 0:
                            tax_total['tax_amount'] = tax_total['tax_amount'] - tax_subtotal['tax_amount']
                        tax_subtotal['tax_amount'] = 0

        #raise ValidationError(str(vals['vals']['tax_total_vals']))
        return vals

    # #OVERRIDE
    def _get_invoice_monetary_total_vals(self, invoice, taxes_vals, line_extension_amount, allowance_total_amount, charge_total_amount):
        """ Method used to fill the cac:{Legal,Requested}MonetaryTotal node"""

        #AQUI SE TIENE QUE MODIFICAR LA PARTE DE LegalMonetaryTotal del valor en 

        #agregado por anticipo , evita que traiga la linea de anticipo que es de cantidad -1
        # invoice_lines = invoice.invoice_line_ids.filtered(
        #     lambda line: line.display_type not in ('line_note', 'line_section') and line.quantity >= 0
        # )

        amount_untaxed_downpayments = 0
        amount_total_downpayments = 0

        if invoice.reference_downpayments_invoice:
            amount_untaxed_downpayments = sum(invoice.reference_downpayments_invoice.mapped('amount_untaxed'))
            amount_total_downpayments = sum(invoice.reference_downpayments_invoice.mapped('amount_total'))

        # new_line_extension_amount = 0

        # for line_id, line in enumerate(invoice_lines):
        #     line_taxes_vals = taxes_vals['tax_details_per_record'][line]
        #     line_vals = self._get_invoice_line_vals(line, line_id, line_taxes_vals)
        #     invoice_line_vals_list.append(line_vals)
        #     new_line_extension_amount += line_vals['line_extension_amount']

        amount_to_fix = 0

        for line in invoice.invoice_line_ids:
            if (
                line.tax_ids and
                line.tax_ids[0].l10n_pe_edi_tax_code == '9996' and
                line.discount == 100.00 and
                line.l10n_pe_edi_affectation_reason == '37'
            ):
                amount_to_fix += line.quantity * line.price_unit

        return {
            'currency': invoice.currency_id,
            'currency_dp': self._get_currency_decimal_places(invoice.currency_id),
            'line_extension_amount': line_extension_amount + amount_untaxed_downpayments - amount_to_fix,
            'tax_exclusive_amount': taxes_vals['base_amount_currency'] + amount_untaxed_downpayments,
            'tax_inclusive_amount': invoice.amount_total + amount_total_downpayments,
            'allowance_total_amount': allowance_total_amount or None,
            'charge_total_amount': charge_total_amount or None,
            'prepaid_amount': (invoice.amount_total - invoice.amount_residual) + amount_total_downpayments,
            'payable_amount': invoice.amount_total,
        }
    
    def _get_invoice_line_vals(self, line, line_id, taxes_vals):
        # EXTENDS account.edi.xml.ubl_21
        vals = super()._get_invoice_line_vals(line, line_id, taxes_vals)
        if line.tax_ids[0].l10n_pe_edi_tax_code == '9996' and line.discount == 100.00 and line.l10n_pe_edi_affectation_reason == '37':
            vals['line_extension_amount'] = line.quantity * line.price_unit
            vals['pricing_reference_vals']['alternative_condition_price_vals'][0]['price_amount'] = line.currency_id.round(line.price_unit)
        return vals
    
    # def _get_invoice_line_vals(self, line, line_id, taxes_vals):
    #     """ Method used to fill the cac:{Invoice,CreditNote,DebitNote}Line node.
    #     It provides information about the document line.

    #     :param line:    A document line.
    #     :return:        A python dictionary.
    #     """
    #     is_gra = False
    #     if line.tax_ids[0].l10n_pe_edi_tax_code == '9996':
    #         is_gra = True

    #     allowance_charge_vals_list = self._get_invoice_line_allowance_vals_list(line, tax_values_list=taxes_vals)

    #     uom = super()._get_uom_unece_code(line)
    #     total_fixed_tax_amount = sum(
    #         vals['amount']
    #         for vals in allowance_charge_vals_list
    #         if vals.get('charge_indicator') == 'true'
    #     )
    #     return {
    #         'currency': line.currency_id,
    #         'currency_dp': self._get_currency_decimal_places(line.currency_id),
    #         'id': line_id + 1,
    #         'line_quantity': line.quantity,
    #         'line_quantity_attrs': {'unitCode': uom},
    #         'line_extension_amount': (line.price_subtotal + total_fixed_tax_amount) if not is_gra else (line.quantity * line.price_unit),
    #         'allowance_charge_vals': allowance_charge_vals_list,
    #         'tax_total_vals': self._get_invoice_line_tax_totals_vals_list(line, taxes_vals),
    #         'item_vals': self._get_invoice_line_item_vals(line, taxes_vals),
    #         'price_vals': self._get_invoice_line_price_vals(line),
    #     }
    

    # def _get_invoice_line_vals(self, line, taxes_vals, idx=None):
    #     vals = super()._get_invoice_line_vals(line, taxes_vals, idx)
    #     if line.tax_ids[0].l10n_pe_edi_tax_code == '9996':
    #         vals['line_extension_amount'] = line.quantity * line.price_unit
    #     return vals
    
    def _get_invoice_line_tax_totals_vals_list(self, line, taxes_vals):
        # OVERRIDES l10n_pe_edi

        is_gra = False
        if line.tax_ids[0].l10n_pe_edi_tax_code == '9996' and line.discount == 100.00 and line.l10n_pe_edi_affectation_reason == '37':
            is_gra = True

        vals = {
            'currency': line.currency_id,
            'currency_dp': line.currency_id.decimal_places,
            'tax_amount': 0.00 if line.l10n_pe_edi_affectation_reason in FREE_AFFECTATION_REASONS else line.price_total - line.price_subtotal,
            'tax_subtotal_vals': [],
        }

        for tax_detail_vals in taxes_vals['tax_details'].values():
            tax = tax_detail_vals['taxes_data'][0]['tax']
            if tax_detail_vals['tax_amount_currency'] < 0 and line.move_id.l10n_pe_edi_legend == '1002':
                continue
            vals['tax_subtotal_vals'].append({
                'currency': line.currency_id,
                'currency_dp': line.currency_id.decimal_places,
                'taxable_amount': (tax_detail_vals['base_amount_currency'] if tax.tax_group_id.l10n_pe_edi_code != 'ICBPER' else None) if not is_gra else line.quantity * line.price_unit,
                'tax_amount': (tax_detail_vals['tax_amount_currency'] or 0.0) if not is_gra else 0, #SE MODIFICO AQUI
                'base_unit_measure_attrs': {
                    'unitCode': line.product_uom_id.l10n_pe_edi_measure_unit_code,
                },
                'base_unit_measure': int(line.quantity) if tax.tax_group_id.l10n_pe_edi_code == 'ICBPER' else None,
                'tax_category_vals': {
                    'percent': (tax.amount if tax.amount_type == 'percent' else None) if not is_gra else 18, #SE MODIFICO AQUI
                    'tax_exemption_reason_code': (
                        line.l10n_pe_edi_affectation_reason
                        if tax.tax_group_id.l10n_pe_edi_code not in ('ISC', 'ICBPER') and line.l10n_pe_edi_affectation_reason
                        else None
                    ),
                    'tier_range': tax.l10n_pe_edi_isc_type if tax.tax_group_id.l10n_pe_edi_code == 'ISC' and tax.l10n_pe_edi_isc_type else None,
                    'tax_scheme_vals': {
                        'id': tax.l10n_pe_edi_tax_code,
                        'name': tax.tax_group_id.l10n_pe_edi_code,
                        'tax_type_code': tax.l10n_pe_edi_international_code,
                    },
                },
            })
        return [vals]