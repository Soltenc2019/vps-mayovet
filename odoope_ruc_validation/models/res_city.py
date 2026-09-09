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

class City(models.Model):
    _inherit = "res.city"

    @api.depends('name', 'state_id.name')
    def _compute_display_name(self):
        for city in self:
            if city.state_id:
                city.display_name = '%s (%s)' % (city.name, city.state_id.name)
            else:
                city.display_name = city.name
