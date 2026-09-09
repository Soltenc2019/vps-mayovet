from collections import Counter, defaultdict

from odoo import _, api, fields, tools, models
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import ValidationError

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def _get_aggregated_product_quantities(self, **kwargs):
        """ Returns a dictionary of products (key = id+name+description+uom) and corresponding values of interest.

        Allows aggregation of data across separate move lines for the same product. This is expected to be useful
        in things such as delivery reports. Dict key is made as a combination of values we expect to want to group
        the products by (i.e. so data is not lost). This function purposely ignores lots/SNs because these are
        expected to already be properly grouped by line.

        returns: dictionary {product_id+name+description+uom: {product, name, description, quantity, product_uom}, ...}
        """
        aggregated_move_lines = {}

        def get_aggregated_properties(move_line=False, move=False):
            move = move or move_line.move_id
            uom = move.product_uom or move_line.product_uom_id
            name = move.product_id.display_name
            description = move.description_picking
            # Add
            default_code = move_line.product_id.default_code
            product_name_only = move_line.move_id.description_picking
            # Add
            if description == name or description == move.product_id.name:
                description = False
            product = move.product_id
            weight = move.product_id.weight * move_line.quantity
            line_key = f'{product.id}_{product.display_name}_{description or ""}_{uom.id}'
            return (line_key, name, description, uom, default_code, product_name_only, weight)

        # Loops to get backorders, backorders' backorders, and so and so...
        backorders = self.env['stock.picking']
        pickings = self.picking_id
        while pickings.backorder_ids:
            backorders |= pickings.backorder_ids
            pickings = pickings.backorder_ids
        # Add 
        exist_lot_id = self.mapped('lot_id')
        # Add
        for move_line in self:
            if kwargs.get('except_package') and move_line.result_package_id:
                continue
            line_key, name, description, uom, default_code, product_name_only, weight = get_aggregated_properties(move_line=move_line)

            quantity = move_line.product_uom_id._compute_quantity(move_line.quantity, uom)
            if line_key not in aggregated_move_lines:
                qty_ordered = None
                if backorders and not kwargs.get('strict'):
                    qty_ordered = move_line.move_id.product_uom_qty
                    # Filters on the aggregation key (product, description and uom) to add the
                    # quantities delayed to backorders to retrieve the original ordered qty.
                    following_move_lines = backorders.move_line_ids.filtered(
                        lambda ml: get_aggregated_properties(move=ml.move_id)[0] == line_key
                    )
                    qty_ordered += sum(following_move_lines.move_id.mapped('product_uom_qty'))
                    # Remove the done quantities of the other move lines of the stock move
                    previous_move_lines = move_line.move_id.move_line_ids.filtered(
                        lambda ml: get_aggregated_properties(move=ml.move_id)[0] == line_key and ml.id != move_line.id
                    )
                    qty_ordered -= sum(map(lambda m: m.product_uom_id._compute_quantity(m.quantity, uom), previous_move_lines))
                aggregated_move_lines[line_key] = {'name': name,
                                                   'description': description,
                                                   'quantity': quantity,
                                                   'qty_ordered': qty_ordered or quantity,
                                                   'product_uom': uom.name,
                                                   'product_uom_rec': uom,
                                                   'product': move_line.product_id,
                                                   # Add
                                                   'default_code': default_code,
                                                   'product_name_only': product_name_only,
                                                   'lots':'',
                                                   'weight_total': 0,
                                                   # Add
                                                   }
            else:
                aggregated_move_lines[line_key]['qty_ordered'] += quantity
                aggregated_move_lines[line_key]['quantity'] += quantity
            # Add
            if exist_lot_id:
                aggregated_move_lines[line_key]['lots'] += move_line.lot_id.name +', ' if move_line.lot_id else ''
                aggregated_move_lines[line_key]['weight_total'] += weight
            # Add
        # Does the same for empty move line to retrieve the ordered qty. for partially done moves
        # (as they are splitted when the transfer is done and empty moves don't have move lines).
        if kwargs.get('strict'):
            return aggregated_move_lines
        pickings = (self.picking_id | backorders)
        for empty_move in pickings.move_ids:
            if not (empty_move.state == "cancel" and empty_move.product_uom_qty
                    and float_is_zero(empty_move.quantity, precision_rounding=empty_move.product_uom.rounding)):
                continue
            # Modified
            line_key, name, description, uom, default_code, product_name_only, weight = get_aggregated_properties(move=empty_move)
            weight_total += weight
            # Modified

            if line_key not in aggregated_move_lines:
                qty_ordered = empty_move.product_uom_qty
                aggregated_move_lines[line_key] = {
                    'name': name,
                    'description': description,
                    'quantity': False,
                    'qty_ordered': qty_ordered,
                    'product_uom': uom.name,
                    'product_uom_rec': uom,
                    'product': empty_move.product_id,
                    # Add
                    'default_code': default_code,
                    'product_name_only': product_name_only,
                    'lots':'',
                    'weight_total': 0,
                    # Add
                }
            else:
                aggregated_move_lines[line_key]['qty_ordered'] += empty_move.product_uom_qty
            # Add
            if exist_lot_id:
                aggregated_move_lines[line_key]['lots'] += move_line.lot_id.name +', ' if move_line.lot_id else ''
                aggregated_move_lines[line_key]['weight_total'] += move_line.product_id.weight * aggregated_move_lines[line_key]['qty_ordered']
            # Add
        return aggregated_move_lines