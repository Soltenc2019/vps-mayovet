# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

from psycopg2 import OperationalError
import base64
import logging

_logger = logging.getLogger(__name__)

DEFAULT_BLOCKING_LEVEL = 'error'


class AccountEdiDocument(models.Model):
    _inherit = 'account.edi.document'

    blocking_level = fields.Selection(selection_add=[('invalid', 'Inválido')])
    state = fields.Selection(selection_add=[('invalid', 'Inválido')])
    
    # @api.model
    # def _prepare_jobs(self):
    #     res = super()._prepare_jobs()
    #     # Modify res or add your custom logic here
    #     filtered_res = [r for r in res if r.get('documents', {}).blocking_level not in ('error', 'invalid')]
    #     return filtered_res

    # @api.model
    # def _process_job(self, job):
    #     """Post or cancel move_id (invoice or payment) by calling the related methods on edi_format_id.
    #     Invoices are processed before payments.

    #     :param job:  {
    #         'documents': account.edi.document,
    #         'method_to_call': str,
    #     }
    #     """
    #     def _postprocess_post_edi_results(documents, edi_result):
    #         attachments_to_unlink = self.env['ir.attachment']
    #         for document in documents:
    #             move = document.move_id
    #             move_result = edi_result.get(move, {})
    #             if move_result.get('attachment'):
    #                 old_attachment = document.sudo().attachment_id
    #                 document.sudo().attachment_id = move_result['attachment']
    #                 if not old_attachment.res_model or not old_attachment.res_id:
    #                     attachments_to_unlink |= old_attachment
    #             if move_result.get('success') is True:
    #                 document.write({
    #                     'state': 'sent',
    #                     'error': False,
    #                     'blocking_level': False,
    #                 })
    #             else:
    #                 if move_result.get('blocking_level', False) == 'invalid':
    #                     document.write({'state': 'invalid'})
    #                 document.write({
    #                     'error': move_result.get('error', False),
    #                     'blocking_level': move_result.get('blocking_level', DEFAULT_BLOCKING_LEVEL) if 'error' in move_result else False,
    #                 })

    #         # Attachments that are not explicitly linked to a business model could be removed because they are not
    #         # supposed to have any traceability from the user.
    #         attachments_to_unlink.unlink()

    #     def _postprocess_cancel_edi_results(documents, edi_result):
    #         move_ids_to_cancel = set()  # Avoid duplicates
    #         attachments_to_unlink = self.env['ir.attachment']
    #         for document in documents:
    #             move = document.move_id
    #             move_result = edi_result.get(move, {})
    #             if move_result.get('success') is True:
    #                 old_attachment = document.sudo().attachment_id
    #                 document.sudo().write({
    #                     'state': 'cancelled',
    #                     'error': False,
    #                     'attachment_id': False,
    #                     'blocking_level': False,
    #                 })

    #                 if move.state == 'posted':
    #                     # The user requested a cancellation of the EDI and it has been approved. Then, the invoice
    #                     # can be safely cancelled.
    #                     move_ids_to_cancel.add(move.id)

    #                 if not old_attachment.res_model or not old_attachment.res_id:
    #                     attachments_to_unlink |= old_attachment

    #             else:
    #                 document.write({
    #                     'error': move_result.get('error', False),
    #                     'blocking_level': move_result.get('blocking_level', DEFAULT_BLOCKING_LEVEL) if move_result.get('error') else False,
    #                 })

    #         if move_ids_to_cancel:
    #             invoices = self.env['account.move'].browse(list(move_ids_to_cancel))
    #             invoices.button_draft()
    #             invoices.button_cancel()

    #         # Attachments that are not explicitly linked to a business model could be removed because they are not
    #         # supposed to have any traceability from the user.
    #         attachments_to_unlink.sudo().unlink()

    #     documents = job['documents']
    #     if job['method_to_call']:
    #         method_to_call = job['method_to_call']
    #     else:
    #         method_to_call = lambda moves: {move: {'success': True} for move in moves}
    #     documents.edi_format_id.ensure_one()  # All account.edi.document of a job should have the same edi_format_id
    #     documents.move_id.company_id.ensure_one()  # All account.edi.document of a job should be from the same company
    #     if len(set(doc.state for doc in documents)) != 1:
    #         raise ValueError('All account.edi.document of a job should have the same state')

    #     state = documents[0].state
    #     documents.move_id.line_ids.flush_recordset()  # manual flush for tax details
    #     moves = documents.move_id
    #     if state == 'to_send':
    #         if all(move.is_invoice(include_receipts=True) for move in moves):
    #             with moves._send_only_when_ready():
    #                 edi_result = method_to_call(moves)
    #         else:
    #             edi_result = method_to_call(moves)
    #         _postprocess_post_edi_results(documents, edi_result)
    #     elif state == 'to_cancel':
    #         edi_result = method_to_call(moves)
    #         _postprocess_cancel_edi_results(documents, edi_result)

    # def _prepare_jobs(self):
    #     to_process = {}
    #     for state, edi_flow in (('to_send', 'post'), ('to_cancel', 'cancel')):
    #         documents = self.filtered(lambda d: d.state == state and d.blocking_level not in ('error', 'invalid'))
    #         for edi_doc in documents:
    #             edi_format = edi_doc.edi_format_id
    #             move = edi_doc.move_id
    #             move_applicability = edi_doc.edi_format_id._get_move_applicability(move) or {}

    #             batching_key = [edi_format, state, move.company_id]
    #             custom_batching_key = f'{edi_flow}_batching'
    #             if move_applicability.get(custom_batching_key):
    #                 batching_key += list(move_applicability[custom_batching_key](move))
    #             else:
    #                 batching_key.append(move.id)

    #             batch = to_process.setdefault(tuple(batching_key), {
    #                 'documents': self.env['account.edi.document'],
    #                 'method_to_call': move_applicability.get(edi_flow),
    #             })
    #             batch['documents'] |= edi_doc

    #     return list(to_process.values())