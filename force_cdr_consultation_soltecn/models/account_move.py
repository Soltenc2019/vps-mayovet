from odoo import api, fields, models, _
from odoo.exceptions import UserError,ValidationError

class AccountMove(models.Model):
    _inherit = 'account.move'

    def check_document_pe_edi_soltecn(self):
        docs = self.edi_document_ids.filtered(lambda d: d.state in ('to_send', 'to_cancel'))
        if docs:
            docs[0].edi_format_id._l10n_pe_edi_decode_cdr_2_soltecn_check(self)