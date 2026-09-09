from odoo import api, fields, models, _

class HrEmployeeCustom(models.Model):
    _inherit = "hr.employee"

    first_name = fields.Char(string='Nombres conductor')
    family_name = fields.Char(string='Apellidos conductor')
    driver_license = fields.Char(string='Licencia del conductor', help='Número de licencia del conductor', compute="_compute_driver_license", readonly=False, store=True) 
    
    vehicle_plate = fields.Char(string='Placa vehículo', help='Número de placa vehícular')
    vehicle_model = fields.Char(string='Modelo vehículo', help='Modelo de vehiculo')
    
    is_private_transportation = fields.Boolean(string="Es privado", compute="_compute_is_private_transportation")
    
    @api.depends('first_name','family_name','driver_license')
    def _compute_is_private_transportation(self):
        for employee in self:
            employee.is_private_transportation = False
            if employee.first_name or employee.family_name or employee.driver_license:
                employee.is_private_transportation = True

    @api.depends('identification_id')
    def _compute_driver_license(self):
        for employee in self:
            employee.driver_license = False
            if employee.identification_id:
                employee.driver_license = 'Q'+employee.identification_id

class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    first_name = fields.Char(related='employee_id.first_name')
    family_name = fields.Char(related='employee_id.first_name')
    driver_license = fields.Char(related='employee_id.family_name')
    
    vehicle_plate = fields.Char(related='employee_id.vehicle_plate')
    vehicle_model = fields.Char(related='employee_id.vehicle_model')