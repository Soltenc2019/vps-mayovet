import calendar
import datetime
import re

import pytz

from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError

MONTHS = [
    ('1', 'Enero'),
    ('2', 'Febrero'),
    ('3', 'Marzo'),
    ('4', 'Abril'),
    ('5', 'Mayo'),
    ('6', 'Junio'),
    ('7', 'Julio'),
    ('8', 'Agosto'),
    ('9', 'Setiembre'),
    ('10', 'Octubre'),
    ('11', 'Noviembre'),
    ('12', 'Diciembre'),
]


class SunatReport13(models.Model):
    """Datos del Registro de Inventario Permanente Valorizado (13.1).

    El cliente no lleva contabilidad en Odoo, asi que el libro no puede salir
    de los apuntes contables. Sale de las CAPAS DE VALORACION de inventario
    (stock.valuation.layer), que Odoo crea en cada movimiento de un producto
    almacenable con su cantidad y su costo, haya o no asientos contables.
    """
    _name = 'sunat.report.13'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = '13 - Registro de Inventario Permanente Valorizado'
    _order = 'start_date desc'

    year = fields.Integer(
        string='Año', required=True, default=lambda self: fields.Date.context_today(self).year)
    month = fields.Selection(
        MONTHS, string='Mes', required=True,
        default=lambda self: str(fields.Date.context_today(self).month))
    start_date = fields.Date(string='Fecha Inicio', compute='_compute_period_date', store=True)
    end_date = fields.Date(string='Fecha Fin', compute='_compute_period_date', store=True)
    period = fields.Char(string="Periodo", compute='_compute_period_date', store=True)

    company_id = fields.Many2one(
        'res.company', string='Compañía', required=True, default=lambda self: self.env.company)
    establishment_code = fields.Char(
        string='Código de establecimiento anexo', required=True,
        default=lambda self: self._default_establishment_code(),
        help="Campo 4 del 13.1. Código de establecimiento anexo del almacén "
             "según la Ficha RUC (0000 si es el domicilio fiscal). Si el "
             "almacén está en un local de terceros o no puede inscribirse "
             "como anexo, va 9999.")

    date_generated = fields.Datetime(string='Fecha de generación', readonly=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('generated', 'Generado'),
        ('done', 'Presentado')], default='draft', string='Estado', required=True,
        readonly=True, tracking=True)

    line_01_ids = fields.Many2many(
        'stock.valuation.layer', 'sunat_report_13_svl_rel', 'report_id', 'layer_id',
        string='Movimientos valorizados', readonly=True)
    sunat_report_13_initial_ids = fields.Many2many(
        'sunat.report.13.initial', 'sunat_report_13_initial_rel', 'report_id', 'initial_id',
        string='Saldos iniciales', readonly=True)

    @api.model
    def _default_establishment_code(self):
        # Se hereda del ultimo libro de la compania para no reescribirlo cada mes.
        last = self.search([('company_id', '=', self.env.company.id)], limit=1)
        return last.establishment_code or '9999'

    @api.depends('year', 'month')
    def _compute_period_date(self):
        for record in self:
            if record.year and record.month:
                month = int(record.month)
                last_day = calendar.monthrange(record.year, month)[1]
                record.start_date = datetime.date(record.year, month, 1)
                record.end_date = datetime.date(record.year, month, last_day)
                record.period = f"{record.year}{month:02d}00"
            else:
                record.start_date = record.end_date = record.period = False

    @api.depends('year', 'month')
    def _compute_display_name(self):
        months = dict(MONTHS)
        for record in self:
            record.display_name = f"{months.get(record.month, '')} {record.year or ''}".strip()

    @api.constrains('establishment_code')
    def _check_establishment_code(self):
        for record in self:
            if not re.fullmatch(r'\d{4,7}', record.establishment_code or ''):
                raise ValidationError(
                    "El código de establecimiento anexo debe tener de 4 a 7 dígitos "
                    "(por ejemplo 0000 o 9999).")

    def _ple_13_tz(self):
        self.ensure_one()
        return pytz.timezone(self.company_id.partner_id.tz or 'America/Lima')

    def _ple_13_utc_bounds(self):
        """Inicio y fin del periodo en UTC, que es como se guarda create_date."""
        self.ensure_one()
        tz = self._ple_13_tz()

        def to_utc(day):
            local = tz.localize(datetime.datetime.combine(day, datetime.time.min))
            return local.astimezone(pytz.utc).replace(tzinfo=None)

        return to_utc(self.start_date), to_utc(self.end_date + datetime.timedelta(days=1))

    def get_initial_valuation(self, start_utc):
        """Saldo inicial por producto: todas las capas anteriores al periodo.

        Es la misma fuente que valoriza los movimientos del periodo, asi que
        el Kardex de cada producto continua exactamente desde este saldo.
        Un producto sin unidades no abre Kardex.
        """
        self.ensure_one()
        self.env['stock.valuation.layer'].flush_model()
        self.env.cr.execute("""
            SELECT svl.product_id     AS product_id,
                   SUM(svl.quantity)  AS quantity,
                   SUM(svl.value)     AS value
              FROM stock_valuation_layer AS svl
             WHERE svl.company_id = %s
               AND svl.create_date < %s
          GROUP BY svl.product_id
            HAVING ROUND(SUM(svl.quantity)::numeric, 8) != 0
          ORDER BY svl.product_id
        """, (self.company_id.id, start_utc))

        rows = self.env.cr.dictfetchall()

        self.sunat_report_13_initial_ids.unlink()
        initials = self.env['sunat.report.13.initial'].create([{
            'product_id': row['product_id'],
            'period': self.period,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'product_cost': float(row['value'] or 0.0) / float(row['quantity']),
            'quantity_on_hand': float(row['quantity']),
            'total_value': float(row['value'] or 0.0),
        } for row in rows])
        self.sunat_report_13_initial_ids = [Command.set(initials.ids)]

    def update_report(self):
        for record in self:
            if record.state != 'draft':
                raise UserError("Solo se pueden actualizar libros en borrador.")
            start_utc, end_utc = record._ple_13_utc_bounds()
            layers = self.env['stock.valuation.layer'].sudo().search([
                ('company_id', '=', record.company_id.id),
                ('create_date', '>=', start_utc),
                ('create_date', '<', end_utc),
                '|', ('quantity', '!=', 0), ('value', '!=', 0),
            ])
            record.line_01_ids = [Command.set(layers.ids)]
            record.get_initial_valuation(start_utc)
        return True

    def generate_report(self):
        self.write({
            'date_generated': fields.Datetime.now(),
            'state': 'generated',
        })
        return True

    def action_draft(self):
        self.write({
            'state': 'draft',
            'date_generated': False,
        })

    def action_generated(self):
        self.state = 'generated'

    def action_done(self):
        self.state = 'done'

    def unlink(self):
        if any(record.state == 'done' for record in self):
            raise UserError('No se puede eliminar un libro presentado.')
        self.sunat_report_13_initial_ids.unlink()
        return super().unlink()
