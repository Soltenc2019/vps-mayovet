from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError
from odoo.tools.misc import formatLang, get_lang
from collections import defaultdict

class SaleOrder(models.Model):
    _inherit = "sale.order"

    referral_guide = fields.Char(string="Guia Remisión", default = False)
    sell_order = fields.Char(string="Orden Compra", default = False)
    taxes_id = fields.Many2many('account.tax', 'tax_id', help="Impuesto por defecto para los productos agregados", string='Impuesto por defecto',
        domain=[('type_tax_use', '=', 'sale')], default=False)

    def _prepare_invoice(self):
        vals = super(SaleOrder, self)._prepare_invoice()
        vals.update({
        'referral_guide': self.referral_guide,
        'sell_order': self.sell_order
        })
        return vals
    
class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.depends('price_subtotal', 'product_uom_qty', 'purchase_price')
    def _compute_margin(self):
        for line in self:
            if line.price_subtotal == 0:
                line.margin = 0
                line.margin_percent = 100
            else:
                line.margin = line.price_subtotal - (line.purchase_price * line.product_uom_qty)
                line.margin_percent = line.price_subtotal and line.margin/line.price_subtotal
    
    @api.depends('product_id')
    def _compute_tax_id(self):
        taxes_by_product_company = defaultdict(lambda: self.env['account.tax'])
        lines_by_company = defaultdict(lambda: self.env['sale.order.line'])
        cached_taxes = {}
        for line in self:
            lines_by_company[line.company_id] += line
        for product in self.product_id:
            for tax in product.taxes_id:
                taxes_by_product_company[(product, tax.company_id)] += tax
        for company, lines in lines_by_company.items():
            for line in lines.with_company(company):
                taxes = taxes_by_product_company[(line.product_id, company)]
                if not line.product_id or not taxes:
                    # Nothing to map
                    line.tax_id = False
                    continue
                fiscal_position = line.order_id.fiscal_position_id
                cache_key = (fiscal_position.id, company.id, tuple(taxes.ids))
                if cache_key in cached_taxes:
                    result = cached_taxes[cache_key]
                else:
                    result = fiscal_position.map_tax(taxes)
                    cached_taxes[cache_key] = result
                # If company_id is set, always filter taxes by the company
                if self.order_id.taxes_id:
                    line.tax_id = self.order_id.taxes_id
                else:
                    line.tax_id = result


    # def _compute_tax_id(self):
    #     for line in self:
    #         line = line.with_company(line.company_id)
    #         fpos = line.order_id.fiscal_position_id or line.order_id.fiscal_position_id.get_fiscal_position(line.order_partner_id.id)
    #         # If company_id is set, always filter taxes by the company
    #         taxes = line.product_id.taxes_id.filtered(lambda t: t.company_id == line.env.company)
    #         if self.order_id.taxes_id:
    #             line.tax_id = self.order_id.taxes_id
    #         else:
    #             line.tax_id = fpos.map_tax(taxes, line.product_id, line.order_id.partner_shipping_id)

    # @api.onchange('product_id')
    # def product_id_change(self):
    #     if not self.product_id:
    #         return
    #     valid_values = self.product_id.product_tmpl_id.valid_product_template_attribute_line_ids.product_template_value_ids
    #     # remove the is_custom values that don't belong to this template
    #     for pacv in self.product_custom_attribute_value_ids:
    #         if pacv.custom_product_template_attribute_value_id not in valid_values:
    #             self.product_custom_attribute_value_ids -= pacv

    #     # remove the no_variant attributes that don't belong to this template
    #     for ptav in self.product_no_variant_attribute_value_ids:
    #         if ptav._origin not in valid_values:
    #             self.product_no_variant_attribute_value_ids -= ptav

    #     vals = {}
    #     if not self.product_uom or (self.product_id.uom_id.id != self.product_uom.id):
    #         vals['product_uom'] = self.product_id.uom_id
    #         vals['product_uom_qty'] = self.product_uom_qty or 1.0

    #     product = self.product_id.with_context(
    #         lang=get_lang(self.env, self.order_id.partner_id.lang).code,
    #         partner=self.order_id.partner_id,
    #         quantity=vals.get('product_uom_qty') or self.product_uom_qty,
    #         date=self.order_id.date_order,
    #         pricelist=self.order_id.pricelist_id.id,
    #         uom=self.product_uom.id
    #     )

    #     vals.update(name=self.get_sale_order_line_multiline_description_sale(product))

    #     self._compute_tax_id()

    #     if self.order_id.pricelist_id and self.order_id.partner_id:
    #         if self.order_id.taxes_id:
    #             vals['price_unit'] = self._get_display_price(product)
    #         else:
    #             vals['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(self._get_display_price(product), product.taxes_id, self.tax_id, self.company_id)
    #     self.update(vals)

    #     title = False
    #     message = False
    #     result = {}
    #     warning = {}
    #     if product.sale_line_warn != 'no-message':
    #         title = _("Warning for %s", product.name)
    #         message = product.sale_line_warn_msg
    #         warning['title'] = title
    #         warning['message'] = message
    #         result = {'warning': warning}
    #         if product.sale_line_warn == 'block':
    #             self.product_id = False

    #     return result

    # @api.onchange('product_uom', 'product_uom_qty')
    # def product_uom_change(self):
    #     if not self.product_uom or not self.product_id:
    #         self.price_unit = 0.0
    #         return
    #     if self.order_id.pricelist_id and self.order_id.partner_id:
    #         product = self.product_id.with_context(
    #             lang=self.order_id.partner_id.lang,
    #             partner=self.order_id.partner_id,
    #             quantity=self.product_uom_qty,
    #             date=self.order_id.date_order,
    #             pricelist=self.order_id.pricelist_id.id,
    #             uom=self.product_uom.id,
    #             fiscal_position=self.env.context.get('fiscal_position')
    #         )
    #         if self.order_id.taxes_id:
    #             self.price_unit = self._get_display_price(product)
    #         else:
    #             self.price_unit = self.env['account.tax']._fix_tax_included_price_company(self._get_display_price(product), product.taxes_id, self.tax_id, self.company_id)

    # @api.onchange('product_id')
    # def product_id_change(self):
    #     if not self.product_id:
    #         return
    #     valid_values = self.product_id.product_tmpl_id.valid_product_template_attribute_line_ids.product_template_value_ids
    #     # remove the is_custom values that don't belong to this template
    #     for pacv in self.product_custom_attribute_value_ids:
    #         if pacv.custom_product_template_attribute_value_id not in valid_values:
    #             self.product_custom_attribute_value_ids -= pacv

    #     # remove the no_variant attributes that don't belong to this template
    #     for ptav in self.product_no_variant_attribute_value_ids:
    #         if ptav._origin not in valid_values:
    #             self.product_no_variant_attribute_value_ids -= ptav

    #     vals = {}
    #     if not self.product_uom or (self.product_id.uom_id.id != self.product_uom.id):
    #         vals['product_uom'] = self.product_id.uom_id
    #         vals['product_uom_qty'] = self.product_uom_qty or 1.0

    #     product = self.product_id.with_context(
    #         lang=get_lang(self.env, self.order_id.partner_id.lang).code,
    #         partner=self.order_id.partner_id,
    #         quantity=vals.get('product_uom_qty') or self.product_uom_qty,
    #         date=self.order_id.date_order,
    #         pricelist=self.order_id.pricelist_id.id,
    #         uom=self.product_uom.id
    #     )
    #     vals.update(name=self.get_sale_order_line_multiline_description_sale(product))

    #     self._compute_tax_id()

    #     if self.order_id.pricelist_id and self.order_id.partner_id:
    #         vals['price_unit'] = self._get_default_price_unit_from_product(product)
    #     if self.order_id.taxes_id:
    #         vals['tax_id'] = self.order_id.taxes_id
    #     # raise ValidationError(vals['product_uom'])
    #     self.update(vals)
        
    #     title = False
    #     message = False
    #     result = {}
    #     warning = {}
    #     if product.sale_line_warn != 'no-message':
    #         title = _("Warning for %s", product.name)
    #         message = product.sale_line_warn_msg
    #         warning['title'] = title
    #         warning['message'] = message
    #         result = {'warning': warning}
    #         if product.sale_line_warn == 'block':
    #             self.product_id = False
    #     return result

    # def _get_default_price_unit_from_product(self, product):
    #     self.ensure_one()

    #     currency = self.order_id.currency_id
    #     fiscal_position = self.order_id.fiscal_position_id or self.order_id.partner_id.property_account_position_id
    #     product_taxes = self.product_id.taxes_id.filtered(lambda r: r.company_id == self.order_id.company_id)
    #     product_taxes_after_fp = fiscal_position.map_tax(product_taxes, partner=self.order_id.partner_id)
    #     price_unit = self._get_display_price(product)

    #     if set(product_taxes.ids) != set(product_taxes_after_fp.ids):
    #         flattened_taxes = product_taxes._origin.flatten_taxes_hierarchy()
    #         if any(tax.price_include for tax in flattened_taxes):
    #             taxes_res = flattened_taxes.compute_all(
    #                 price_unit,
    #                 quantity=self.product_uom_qty,
    #                 currency=currency,
    #                 product=self.product_id,
    #                 partner=self.order_id.partner_id,
    #             )
    #             price_unit = currency.round(taxes_res['total_excluded'])

    #         flattened_taxes = product_taxes_after_fp._origin.flatten_taxes_hierarchy()
    #         if any(tax.price_include for tax in flattened_taxes):
    #             taxes_res = flattened_taxes.compute_all(
    #                 price_unit,
    #                 quantity=self.product_uom_qty,
    #                 currency=currency,
    #                 product=self.product_id,
    #                 partner=self.order_id.partner_id,
    #                 handle_price_include=False,
    #             )
    #             for tax_res in taxes_res['taxes']:
    #                 tax = self.env['account.tax'].browse(tax_res['id'])
    #                 if tax.price_include:
    #                     price_unit += tax_res['amount']
    #     return price_unit