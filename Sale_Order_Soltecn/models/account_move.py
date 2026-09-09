from odoo import api, fields, models, _

class AccountMove(models.Model): 
    
    _inherit = 'account.move'  

    sell_order = fields.Char(string="Sell Order", default = False)
    referral_guide = fields.Char(string="Referral Guide", default = False)