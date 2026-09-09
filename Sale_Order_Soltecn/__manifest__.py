{
    'name': 'Sale Order Soltecn',
    'version': '17.0',
    'summary': 'Custom sale order',
    'category': 'Invoice',
    'author': 'Soltecn',
    'maintainer': 'Soltecn',
    'company': 'Soltecn',
    'website': 'https://www.Soltecn.com',
    'depends': ['base','sale','sale_margin','res_partner_field'],
    'qweb': [],
    'data': [
        'views/ir_actions_report_templates.xml',
        'views/sale_order_views.xml',
        #'views/res_partner_views.xml'
        ],
    'installable': True,
    'license': 'AGPL-3',
}