from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = "product.product"

    message_partner_ids = fields.Many2many(groups="base.group_system")


class ProductTemplate(models.Model):
    _inherit = "product.template"

    message_partner_ids = fields.Many2many(groups="base.group_system")


