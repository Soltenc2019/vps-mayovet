from odoo import api, fields, models, _, Command
from odoo.osv import expression
from odoo.tools.float_utils import float_round as round
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import formatLang
from odoo.tools import frozendict

from collections import defaultdict
import math
import re

class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.model
    def _compute_taxes_for_single_line(self, base_line, handle_price_include=True, include_caba_tags=False, early_pay_discount_computation=None, early_pay_discount_percentage=None):
        # if base_line['taxes'].l10n_pe_edi_tax_code == '9996':
        #     orig_price_unit_after_discount = base_line['price_unit'] / 1.18
        # else:
        #     orig_price_unit_after_discount = base_line['price_unit'] * (1 - (base_line['discount'] / 100.0))
        # raise ValidationError(str(base_line['taxes'].l10n_pe_edi_tax_code))
        orig_price_unit_after_discount = base_line['price_unit'] * (1 - (base_line['discount'] / 100.0))
        price_unit_after_discount = orig_price_unit_after_discount
        taxes = base_line['taxes']._origin
        currency = base_line['currency'] or self.env.company.currency_id
        rate = base_line['rate']
        # ADD BONIFICACION
        tax_boni_id = self.env['account.tax'].search([('l10n_pe_edi_tax_code', '=', '9996')], limit=1).id
        # ADD
        if early_pay_discount_computation in ('included', 'excluded'):
            remaining_part_to_consider = (100 - early_pay_discount_percentage) / 100.0
            price_unit_after_discount = remaining_part_to_consider * price_unit_after_discount

        if taxes:

            if handle_price_include is None:
                manage_price_include = bool(base_line['handle_price_include'])
            else:
                manage_price_include = handle_price_include

            taxes_res = taxes.with_context(**base_line['extra_context']).compute_all(
                price_unit_after_discount,
                currency=currency,
                quantity=base_line['quantity'],
                product=base_line['product'],
                partner=base_line['partner'],
                is_refund=base_line['is_refund'],
                handle_price_include=manage_price_include,
                include_caba_tags=include_caba_tags,
            )

            to_update_vals = {
                'tax_tag_ids': [Command.set(taxes_res['base_tags'])],
                'price_subtotal': taxes_res['total_excluded'],
                'price_total': taxes_res['total_included'],
            }

            if early_pay_discount_computation == 'excluded':
                new_taxes_res = taxes.with_context(**base_line['extra_context']).compute_all(
                    orig_price_unit_after_discount,
                    currency=currency,
                    quantity=base_line['quantity'],
                    product=base_line['product'],
                    partner=base_line['partner'],
                    is_refund=base_line['is_refund'],
                    handle_price_include=manage_price_include,
                    include_caba_tags=include_caba_tags,
                )
                for tax_res, new_taxes_res in zip(taxes_res['taxes'], new_taxes_res['taxes']):
                    delta_tax = new_taxes_res['amount'] - tax_res['amount']
                    tax_res['amount'] += delta_tax
                    to_update_vals['price_total'] += delta_tax

            tax_values_list = []
            # raise ValidationError(str(base_line))
            # raise ValidationError(str(taxes_res['taxes']))
            for tax_res in taxes_res['taxes']:
                tax_amount = tax_res['amount'] / rate
                if self.company_id.tax_calculation_rounding_method == 'round_per_line':
                    tax_amount = currency.round(tax_amount)
                tax_rep = self.env['account.tax.repartition.line'].browse(tax_res['tax_repartition_line_id'])
                if tax_res['id']==tax_boni_id:
                    tax_values_list.append({
                        **tax_res,
                        'tax_repartition_line': tax_rep,
                        'base_amount_currency': base_line['quantity'] * base_line['price_unit'],
                        'base_amount': currency.round(tax_res['base'] / rate),
                        'tax_amount_currency': base_line['quantity'] * base_line['price_unit'] * 0.18,
                        'tax_amount': tax_amount,
                    })
                else:
                    tax_values_list.append({
                        **tax_res,
                        'tax_repartition_line': tax_rep,
                        'base_amount_currency': tax_res['base'],
                        'base_amount': currency.round(tax_res['base'] / rate),
                        'tax_amount_currency': tax_res['amount'],
                        'tax_amount': tax_amount,
                    })

        else:
            price_subtotal = currency.round(price_unit_after_discount * base_line['quantity'])
            to_update_vals = {
                'tax_tag_ids': [Command.clear()],
                'price_subtotal': price_subtotal,
                'price_total': price_subtotal,
            }
            tax_values_list = []

        return to_update_vals, tax_values_list


    @api.model
    def _prepare_tax_totals(self, base_lines, currency, tax_lines=None,is_company_currency_requested=False):
        #CHANGE
        tax_boni_id = self.env['account.tax'].search([('l10n_pe_edi_tax_code', '=', '9996')], limit=1).id
        to_process = []
        for base_line in base_lines:
            to_update_vals, tax_values_list = self._compute_taxes_for_single_line(base_line)
            to_process.append((base_line, to_update_vals, tax_values_list))

        def grouping_key_generator(base_line, tax_values):
            source_tax = tax_values['tax_repartition_line'].tax_id
            return {'tax_group': source_tax.tax_group_id}

        global_tax_details = self._aggregate_taxes(to_process, grouping_key_generator=grouping_key_generator)

        tax_group_vals_list = []
        # raise ValidationError(str(global_tax_details['tax_details'].values()))
        # raise ValidationError(str(to_process))
        for tax_detail in global_tax_details['tax_details'].values():
            # raise ValidationError(str(tax_detail['group_tax_details'][0]['id']))
            #CHANGE
            if tax_detail['group_tax_details'][0]['id']==tax_boni_id:
                tax_group_vals = {
                    'tax_group': tax_detail['tax_group'],
                    'base_amount': 0,
                    'tax_amount': 0,
                    'hide_base_amount': all(x['tax_repartition_line'].tax_id.amount_type == 'fixed' for x in tax_detail['group_tax_details']),
                }
            else:
                tax_group_vals = {
                    'tax_group': tax_detail['tax_group'],
                    'base_amount': tax_detail['base_amount_currency'],
                    'tax_amount': tax_detail['tax_amount_currency'],
                    'hide_base_amount': all(x['tax_repartition_line'].tax_id.amount_type == 'fixed' for x in tax_detail['group_tax_details']),
                }

            if is_company_currency_requested:
                tax_group_vals['base_amount_company_currency'] = tax_detail['base_amount']
                tax_group_vals['tax_amount_company_currency'] = tax_detail['tax_amount']
            
            # Handle a manual edition of tax lines.
            #CHANGE
            if tax_lines is not None:
                matched_tax_lines = [
                    x
                    for x in tax_lines
                    if (x['group_tax'] or x['tax_repartition_line'].tax_id).tax_group_id == tax_detail['tax_group']
                ]
                if matched_tax_lines:
                    tax_group_vals['tax_amount'] = sum(x['tax_amount'] for x in matched_tax_lines)

            tax_group_vals_list.append(tax_group_vals)

        tax_group_vals_list = sorted(tax_group_vals_list, key=lambda x: (x['tax_group'].sequence, x['tax_group'].id))

        # ==== Partition the tax group values by subtotals ====

        amount_untaxed = global_tax_details['base_amount_currency']
        amount_tax = 0.0

        amount_untaxed_company_currency = global_tax_details['base_amount']
        amount_tax_company_currency = 0.0

        subtotal_order = {}
        groups_by_subtotal = defaultdict(list)
        for tax_group_vals in tax_group_vals_list:
            tax_group = tax_group_vals['tax_group']

            subtotal_title = tax_group.preceding_subtotal or _("Importe libre de impuestos")
            sequence = tax_group.sequence

            subtotal_order[subtotal_title] = min(subtotal_order.get(subtotal_title, float('inf')), sequence)
            groups_by_subtotal[subtotal_title].append({
                'group_key': tax_group.id,
                'tax_group_id': tax_group.id,
                'tax_group_name': tax_group.name,
                'tax_group_amount': tax_group_vals['tax_amount'],
                'tax_group_base_amount': tax_group_vals['base_amount'],
                'formatted_tax_group_amount': formatLang(self.env, tax_group_vals['tax_amount'], currency_obj=currency),
                'formatted_tax_group_base_amount': formatLang(self.env, tax_group_vals['base_amount'], currency_obj=currency),
                'hide_base_amount': tax_group_vals['hide_base_amount'],
            })

            if is_company_currency_requested:
                groups_by_subtotal[subtotal_title][-1]['tax_group_amount_company_currency'] = tax_group_vals['tax_amount_company_currency']
                groups_by_subtotal[subtotal_title][-1]['tax_group_base_amount_company_currency'] = tax_group_vals['base_amount_company_currency']

        # ==== Build the final result ====

        subtotals = []
        for subtotal_title in sorted(subtotal_order.keys(), key=lambda k: subtotal_order[k]):
            amount_total = amount_untaxed + amount_tax
            subtotals.append({
                'name': subtotal_title,
                'amount': amount_total,
                'formatted_amount': formatLang(self.env, amount_total, currency_obj=currency),
            })
            if is_company_currency_requested:
                subtotals[-1]['amount_company_currency'] = amount_untaxed_company_currency + amount_tax_company_currency
                amount_tax_company_currency += sum(x['tax_group_amount_company_currency'] for x in groups_by_subtotal[subtotal_title])

            amount_tax += sum(x['tax_group_amount'] for x in groups_by_subtotal[subtotal_title])

        amount_total = amount_untaxed + amount_tax
        amount_total_company_currency = amount_untaxed_company_currency + amount_tax_company_currency

        #CHANGE
        display_tax_base = (len(global_tax_details['tax_details']) == 1 and tax_group_vals_list[0]['base_amount'] != amount_untaxed) \
            or len(global_tax_details['tax_details']) > 1

        result = {
            'amount_untaxed': currency.round(amount_untaxed) if currency else amount_untaxed,
            'amount_total': currency.round(amount_total) if currency else amount_total,
            'formatted_amount_total': formatLang(self.env, amount_total, currency_obj=currency),
            'formatted_amount_untaxed': formatLang(self.env, amount_untaxed, currency_obj=currency),
            'groups_by_subtotal': groups_by_subtotal,
            'subtotals': subtotals,
            'subtotals_order': sorted(subtotal_order.keys(), key=lambda k: subtotal_order[k]),
            'display_tax_base': display_tax_base
        }
        if is_company_currency_requested:
            comp_currency = self.env.company.currency_id
            result['amount_total_company_currency'] = comp_currency.round(amount_total_company_currency)

        return result
    
    @api.model
    def _prepare_tax_totals_copy(self, base_lines, currency, tax_lines=None):
        #CHANGE
        tax_boni_id = self.env['account.tax'].search([('l10n_pe_edi_tax_code', '=', '9996')], limit=1).id
        to_process = []
        for base_line in base_lines:
            to_update_vals, tax_values_list = self._compute_taxes_for_single_line(base_line)
            to_process.append((base_line, to_update_vals, tax_values_list))

        def grouping_key_generator(base_line, tax_values):
            source_tax = tax_values['tax_repartition_line'].tax_id
            return {'tax_group': source_tax.tax_group_id}

        global_tax_details = self._aggregate_taxes(to_process, grouping_key_generator=grouping_key_generator)

        tax_group_vals_list = []
        # raise ValidationError(str(global_tax_details['tax_details'].values()))
        # raise ValidationError(str(to_process))
        for tax_detail in global_tax_details['tax_details'].values():
            # raise ValidationError(str(tax_detail['group_tax_details'][0]['id']))
            #CHANGE
            if tax_detail['group_tax_details'][0]['id']==tax_boni_id:
                tax_group_vals = {
                    'tax_group': tax_detail['tax_group'],
                    'base_amount': 0,
                    'tax_amount': 0,
                }
            else:
                tax_group_vals = {
                    'tax_group': tax_detail['tax_group'],
                    'base_amount': tax_detail['base_amount_currency'],
                    'tax_amount': tax_detail['tax_amount_currency'],
                }
            # Handle a manual edition of tax lines.
            #CHANGE
            if tax_lines is not None:
                matched_tax_lines = [
                    x
                    for x in tax_lines
                    if (x['group_tax'] or x['tax_repartition_line'].tax_id).tax_group_id == tax_detail['tax_group']
                ]
                if matched_tax_lines:
                    tax_group_vals['tax_amount'] = sum(x['tax_amount'] for x in matched_tax_lines)

            tax_group_vals_list.append(tax_group_vals)

        tax_group_vals_list = sorted(tax_group_vals_list, key=lambda x: (x['tax_group'].sequence, x['tax_group'].id))

        # ==== Partition the tax group values by subtotals ====

        amount_untaxed = global_tax_details['base_amount_currency']
        amount_tax = 0.0

        subtotal_order = {}
        groups_by_subtotal = defaultdict(list)
        for tax_group_vals in tax_group_vals_list:
            tax_group = tax_group_vals['tax_group']

            subtotal_title = tax_group.preceding_subtotal or _("Importe libre de impuestos")
            sequence = tax_group.sequence

            subtotal_order[subtotal_title] = min(subtotal_order.get(subtotal_title, float('inf')), sequence)
            groups_by_subtotal[subtotal_title].append({
                'group_key': tax_group.id,
                'tax_group_id': tax_group.id,
                'tax_group_name': tax_group.name,
                'tax_group_amount': tax_group_vals['tax_amount'],
                'tax_group_base_amount': tax_group_vals['base_amount'],
                'formatted_tax_group_amount': formatLang(self.env, tax_group_vals['tax_amount'], currency_obj=currency),
                'formatted_tax_group_base_amount': formatLang(self.env, tax_group_vals['base_amount'], currency_obj=currency),
            })

        # ==== Build the final result ====

        subtotals = []
        for subtotal_title in sorted(subtotal_order.keys(), key=lambda k: subtotal_order[k]):
            amount_total = amount_untaxed + amount_tax
            subtotals.append({
                'name': subtotal_title,
                'amount': amount_total,
                'formatted_amount': formatLang(self.env, amount_total, currency_obj=currency),
            })
            amount_tax += sum(x['tax_group_amount'] for x in groups_by_subtotal[subtotal_title])

        amount_total = amount_untaxed + amount_tax

        #CHANGE
        display_tax_base = (len(global_tax_details['tax_details']) == 1 and tax_group_vals_list[0]['base_amount'] != amount_untaxed) \
            or len(global_tax_details['tax_details']) > 1

        return {
            'amount_untaxed': currency.round(amount_untaxed) if currency else amount_untaxed,
            'amount_total': currency.round(amount_total) if currency else amount_total,
            'formatted_amount_total': formatLang(self.env, amount_total, currency_obj=currency),
            'formatted_amount_untaxed': formatLang(self.env, amount_untaxed, currency_obj=currency),
            'groups_by_subtotal': groups_by_subtotal,
            'subtotals': subtotals,
            'subtotals_order': sorted(subtotal_order.keys(), key=lambda k: subtotal_order[k]),
            'display_tax_base': display_tax_base
        }