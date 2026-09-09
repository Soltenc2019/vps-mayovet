from odoo import models, fields, api

class StockGroupPicking(models.Model):
    _name = 'stock.group.picking'
    _description = 'Stock group picking'

    stock_picking = fields.Many2one('stock.picking', string='Stock picking', index=True, required=True, readonly=True, auto_join=True, ondelete="cascade", check_company=True)
    name = fields.Char(string="Descripción", compute="_compute_group_data", store=True)
    product_id = fields.Many2one('product.product', string='Agrupado en', domain=[('type', '=', 'consu'), ('is_storable', '=', False)])
    group_uom = fields.Many2one('uom.uom', "Unidad Medida", compute="_compute_group_data", store=True)
    quantity = fields.Float(string="Cantidad", default=1)
    weight_group = fields.Float(string="Peso grupo", compute="_compute_weight_group", store=True)
    # NEW

    @api.depends('name')
    def _compute_display_name(self):
        for index, group in enumerate(self, start=1):
            group.display_name = "(%s) %s" % (index, group.name or '')

    @api.depends('stock_picking', 'stock_picking.move_ids_without_package', 'stock_picking.move_ids_without_package.product_id', 'stock_picking.move_ids_without_package.stock_group_paleta_bulto')
    def _compute_weight_group(self):
        for stock_group in self:
            move_filtered = stock_group.stock_picking.move_ids_without_package.filtered(lambda i: i.stock_group_paleta_bulto.id == stock_group.id)
            weight_group_total = 0
            for move in move_filtered:
                weight_group_total += move.product_id.weight
            stock_group.weight_group = weight_group_total + stock_group.product_id.weight

    @api.depends('product_id')
    def _compute_group_data(self):
        for stock_group in self:
            stock_group.name = False
            stock_group.group_uom = False
            if stock_group.product_id:
                stock_group.name = stock_group.product_id.name
                stock_group.group_uom = stock_group.product_id.uom_id

# access_stock_group_picking,stock.group.picking,model_stock_group_picking,stock.group_stock_user,1,1,1,1
# access_stock_group_picking_manager,stock.group.picking.manager,model_stock_group_picking,stock.group_stock_manager,1,1,1,1