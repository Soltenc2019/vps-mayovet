from odoo import models, fields, api

class CatalogTmpl(models.Model):
    _name = 'l10n_pe_edi.catalog.tmpl'
    _description = 'Catalog Template'
    # Odoo 18: reemplaza el antiguo override de _name_search
    _rec_names_search = ['name', 'code']

    active = fields.Boolean(string='Active', default=True)
    code = fields.Char(string='Code', size=4, index=True, required=True)
    name = fields.Char(string='Description', index=True, required=True)

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for table in self:
            table.display_name = "%s %s" % (table.code, table.name or '')

class Catalog23(models.Model):
    _name = "l10n_pe_edi.catalog.23"
    _description = 'Codigos- Regimenes de Retencion'
    _inherit = 'l10n_pe_edi.catalog.tmpl'

    rate = fields.Float(string='Rate', default=0.0)
