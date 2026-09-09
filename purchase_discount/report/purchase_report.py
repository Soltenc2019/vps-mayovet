# Copyright 2017 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# Copyright 2017-2019 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models
from odoo.tools import SQL


class PurchaseReport(models.Model):
    _inherit = "purchase.report"

    discount = fields.Float(string="Discount (%)", digits="Discount", aggregator="avg")

    def _select(self) -> SQL:
        # Odoo 18: _select() devuelve un objeto SQL en lugar de un string.
        res = super()._select()
        code = res.code.replace("l.price_unit", self._get_discounted_price_unit_exp())
        return SQL("%s, l.discount AS discount", SQL(code, *res.params))

    def _group_by(self) -> SQL:
        return SQL("%s, l.discount", super()._group_by())

    def _get_discounted_price_unit_exp(self):
        """Inheritable method for getting the SQL expression used for
        calculating the unit price with discount(s).

        :rtype: str
        :return: SQL expression for discounted unit price.
        """
        return "(1.0 - COALESCE(l.discount, 0.0) / 100.0) * l.price_unit"
