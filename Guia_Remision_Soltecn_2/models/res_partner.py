from odoo import api, fields, models

class ResPartnerCustom(models.Model):
    _inherit = 'res.partner'
    
    contact_address = fields.Char(compute='_compute_complete_address', store=True)
    property_code = fields.Char(string="Código de establecimiento")

    @api.depends('street', 'zip', 'city', 'country_id','l10n_pe_district')
    def _compute_complete_address(self):
        for record in self:
            record.contact_address = ''
            if record.street:
                record.contact_address += record.street
            if record.street2:
                record.contact_address += ' '+record.street2
            # if record.l10n_pe_district:
            #     record.contact_address += ', '+record.l10n_pe_district.name + ', '
            # if record.state_id:
            #     record.contact_address += record.state_id.name + ', '
            # if record.country_id:
            #     record.contact_address += record.country_id.name
            record.contact_address = record.contact_address.strip().strip(',')