from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    edi_blocking_level = fields.Selection(string="Documento estado", selection_add=[('invalid', 'Inválido')])
    edi_state = fields.Selection(selection_add=[('invalid', 'Inválido')])

    # @api.depends(
    #     'edi_document_ids',
    #     'edi_document_ids.state',
    #     'edi_document_ids.blocking_level',
    #     'edi_document_ids.edi_format_id',
    #     'edi_document_ids.edi_format_id.name')
    # def _compute_edi_web_services_to_process(self):
    #     # OVERRIDE to take blocking_level into account
    #     for move in self:
    #         to_process = move.edi_document_ids.filtered(lambda d: d.state in ['to_send', 'to_cancel'] and d.blocking_level not in ('error', 'invalid'))
    #         format_web_services = to_process.edi_format_id.filtered(lambda f: f._needs_web_services())
    #         move.edi_web_services_to_process = ', '.join(f.name for f in format_web_services)

    # @api.depends('edi_document_ids.state')
    # def _compute_edi_state(self):
    #     super(AccountMove, self)._compute_edi_state()
        
    #     for move in self:
    #         all_states = set(move.edi_document_ids.filtered(lambda d: d.edi_format_id._needs_web_services()).mapped('state'))
    #         if 'invalid' in all_states:
    #             move.edi_state = 'invalid'