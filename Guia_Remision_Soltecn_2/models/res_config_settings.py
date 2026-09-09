from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    specify_weight = fields.Boolean(related="company_id.specify_weight", string="Especificar peso automáticamente", help="Verdadero: El peso de los productos transportados es calculado según peso especificado de productos. Falso: El peso es especificado manualmente.", readonly=False)
    specify_weight_by_bultos_paletas = fields.Boolean(related="company_id.specify_weight_by_bultos_paletas", string="Especificar peso en bultos o paletas", help="Forzar elección de a qué paleta o bulto pertenece cada producto", readonly=False)
    # picking_type_in_package_default_id = fields.Many2one(string="Tipo picking por defecto", readonly=False)

    # @api.model
    # def get_values(self):
    #     res = super(ResConfigSettings, self).get_values()
    #     params = self.env['ir.config_parameter'].sudo()
    #     picking_type_in_package_default_id = params.get_param('picking_type_in_package_default_id', default=False)
    #     res.update(
    #         picking_type_in_package_default_id=int(picking_type_in_package_default_id),
    #     )
    #     return res
    #     # res = super(ResConfigSettings, self).get_values()
    #     # res['picking_type_in_package_default_id'] = int(self.env['ir.config_parameter'].sudo().get_param('Guia_Remision_Soltecn_2.picking_type_in_package_default_id', default=False))
    #     # return res
    # def set_values(self):
    #     # if not self.group_sale_order_template:
    #     self.env['res.company'].sudo().search([]).write({
    #         'picking_type_in_package_default_id': self.picking_type_in_package_default_id,
    #     })
    #     return super(ResConfigSettings, self).set_values()

    # @api.model
    # def set_values(self):
    #     self.env['ir.config_parameter'].sudo().set_param('picking_type_in_package_default_id', self.picking_type_in_package_default_id.id)
    #     super(ResConfigSettings, self).set_values()

    # company_po_template_id = fields.Many2one(
    #     related="company_id.purchase_order_template_id", string="Default Template", readonly=False,
    #     domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    # # module_purchase_template_builder = fields.Boolean("Purchase Builder")

    # # @api.onchange('group_purchase_order_template')
    # # def _onchange_group_sale_order_template(self):
    # #     if not self.group_purchase_order_template:
    # #         self.module_purchase_template_builder = False

    # def set_values(self):
    #     if not self.group_sale_order_template:
    #         self.company_po_template_id = None
    #         self.env['res.company'].sudo().search([]).write({
    #             'purchase_order_template_id': False,
    #         })
    #     return super(ResConfigSettings, self).set_values()