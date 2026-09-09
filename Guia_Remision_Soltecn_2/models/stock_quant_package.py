from odoo import models, fields, api

class StockQuantPackage(models.Model):
    _inherit = "stock.quant.package"

    def _default_package_type_id(self):
        package_type_id = self.env['stock.package.type'].search([('package_type_default', '=', True)], limit=1)
        return package_type_id

    total_package_items_weight = fields.Float(string="Peso total items", compute="_compute_total_package_items_weight", store=True)
    package_type_id = fields.Many2one(default=_default_package_type_id)
    # total_weight = fields.Float(string="Peso total")

    @api.depends('package_type_id', 'quant_ids', 'quant_ids.product_id')
    def _compute_total_package_items_weight(self):
        for quant in self:
            total_package_items_weight = 0
            for product in quant.quant_ids:
                total_package_items_weight+=product.product_id.weight * product.quantity
            quant.total_package_items_weight = total_package_items_weight
    
    # @api.depends('package_type_id', 'quant_ids', 'quant_ids.product_id')
    # def total_total_weight(self):
    #     for quant in self:
    #         total_package_items_weight = 0
    #         for product in quant.quant_ids:
    #             total_package_items_weight+=product.product_id.weight
    #         quant.total_package_items_weight = total_package_items_weight
            