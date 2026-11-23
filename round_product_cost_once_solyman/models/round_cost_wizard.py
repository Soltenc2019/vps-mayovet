import logging

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import float_compare, float_round

_logger = logging.getLogger(__name__)


class RoundCostWizard(models.TransientModel):
    _name = 'round.cost.wizard'
    _description = 'Redondear costos de productos (uso único)'

    decimals = fields.Integer(
        string='Decimales', default=3, required=True,
        help='Cantidad de decimales a la que se redondean los costos (half-up).')
    company_ids = fields.Many2many(
        'res.company', string='Compañías', required=True,
        default=lambda self: self.env.companies,
        help='El costo es por compañía; se redondea en cada compañía elegida.')
    include_lots = fields.Boolean(
        string='Incluir costo de lotes', default=True,
        help='Redondea también el costo de los lotes (productos con valoración por lote).')
    state = fields.Selection(
        [('draft', 'Configuración'), ('preview', 'Vista previa'), ('done', 'Aplicado')],
        default='draft', required=True)
    line_ids = fields.One2many('round.cost.wizard.line', 'wizard_id', string='Cambios')
    line_count = fields.Integer(string='Costos a modificar', compute='_compute_line_count')

    @api.constrains('decimals')
    def _check_decimals(self):
        for wiz in self:
            if not 0 <= wiz.decimals <= 8:
                raise ValidationError(_('Los decimales deben estar entre 0 y 8.'))

    @api.depends('line_ids')
    def _compute_line_count(self):
        for wiz in self:
            wiz.line_count = len(wiz.line_ids)

    # ------------------------------------------------------------------
    def _check_access(self):
        if not self.env.user.has_group('stock.group_stock_manager'):
            raise AccessError(_('Solo un responsable de Inventario puede usar esta herramienta.'))

    def _reopen(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _target_models(self):
        names = ['product.product']
        if self.include_lots and 'standard_price' in self.env['stock.lot']._fields:
            names.append('stock.lot')
        return names

    def _collect_changes(self):
        """Devuelve [(model, id, company_id, nombre, costo_actual, costo_nuevo)]
        solo para los registros cuyo costo cambia al redondear."""
        self.ensure_one()
        digits = self.decimals
        changes = []
        for company in self.company_ids:
            for model_name in self._target_models():
                Model = self.env[model_name].sudo().with_company(company).with_context(active_test=False)
                records = Model.search([])
                for rec, vals in zip(records, records.read(['standard_price', 'display_name'])):
                    old = vals['standard_price']
                    new = float_round(old, precision_digits=digits)
                    if float_compare(old, new, precision_digits=10) != 0:
                        name = vals['display_name']
                        if model_name == 'stock.lot':
                            name = _('[Lote] %s', name)
                        changes.append((model_name, rec.id, company.id, name, old, new))
        return changes

    def _fill_lines(self, changes):
        self.line_ids.unlink()
        self.env['round.cost.wizard.line'].create([{
            'wizard_id': self.id,
            'res_model': model_name,
            'res_id': res_id,
            'company_id': company_id,
            'name': name,
            'old_cost': old,
            'new_cost': new,
        } for model_name, res_id, company_id, name, old, new in changes])

    # ------------------------------------------------------------------
    def action_preview(self):
        self._check_access()
        for wiz in self:
            wiz._fill_lines(wiz._collect_changes())
            wiz.state = 'preview'
        return self._reopen()

    def action_apply(self):
        self._check_access()
        self.ensure_one()
        changes = self._collect_changes()

        # Agrupa por (modelo, compañía, costo nuevo) para escribir en bloque.
        grouped = {}
        for model_name, res_id, company_id, _name, _old, new in changes:
            grouped.setdefault((model_name, company_id, new), []).append(res_id)

        for (model_name, company_id, new), ids in grouped.items():
            # disable_auto_svl: mismo contexto que usa Odoo para actualizar el costo
            # sin crear capas de valoración ni asientos de revaluación.
            self.env[model_name].sudo().browse(ids).with_company(company_id).with_context(
                disable_auto_svl=True).write({'standard_price': new})

        for model_name, res_id, company_id, name, old, new in changes:
            _logger.info('Costo redondeado: %s id=%s compañía=%s %s -> %s',
                         model_name, res_id, company_id, old, new)
        _logger.info('round_product_cost_once_solyman: %s costos redondeados a %s decimales.',
                     len(changes), self.decimals)

        self._fill_lines(changes)
        self.state = 'done'
        return self._reopen()


class RoundCostWizardLine(models.TransientModel):
    _name = 'round.cost.wizard.line'
    _description = 'Línea de cambio de costo'
    _order = 'name, id'

    wizard_id = fields.Many2one('round.cost.wizard', required=True, ondelete='cascade')
    res_model = fields.Char(required=True)
    res_id = fields.Integer(required=True)
    company_id = fields.Many2one('res.company', string='Compañía')
    name = fields.Char(string='Producto / Lote')
    old_cost = fields.Float(string='Costo actual', digits=(16, 8))
    new_cost = fields.Float(string='Costo redondeado', digits=(16, 8))
