# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2019-TODAY OPeru.
#    Author      :  Grupo Odoo S.A.C. (<http://www.operu.pe>)
#
#    This program is copyright property of the author mentioned above.
#    You can`t redistribute it and/or modify it.
#
###############################################################################

from odoo import fields, models, api

class L10nPeResCityDistrict(models.Model):
    _inherit = 'l10n_pe.res.city.district'

    @api.depends('name', 'city_id.name')
    def _compute_display_name(self):
        for district in self:
            if district.city_id:
                district.display_name = '%s (%s)' % (district.name, district.city_id.name)
            else:
                district.display_name = district.name
