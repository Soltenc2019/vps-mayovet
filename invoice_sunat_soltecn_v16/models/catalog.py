from odoo import models, fields, api
from odoo.osv import expression

class CatalogTmpl(models.Model):
    _name = 'l10n_pe_edi.catalog.tmpl'
    _description = 'Catalog Template'

    active = fields.Boolean(string='Active', default=True)
    code = fields.Char(string='Code', size=4, index=True, required=True)
    name = fields.Char(string='Description', index=True, required=True)

    def name_get(self):
        result = []
        for table in self:
            result.append((table.id, "%s %s" % (table.code, table.name or '')))
        return result

    @api.model#ADD PARAMETER order=None
    def _name_search(self, name=None, args=None, operator='ilike', limit=100, name_get_uid=None,order=None):
        args = args or []
        if operator == 'ilike' and not (name or '').strip():
            domain = []
        else:
            domain = ['|', ('name', 'ilike', name), ('code', 'ilike', name)]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
        
class Catalog23(models.Model):
    _name = "l10n_pe_edi.catalog.23"
    _description = 'Codigos- Regimenes de Retencion'
    _inherit = 'l10n_pe_edi.catalog.tmpl'

    rate = fields.Float(string='Rate', default=0.0)