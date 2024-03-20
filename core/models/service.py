# Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class Service(models.Model):
    ''' 是对其他收支业务的更细分类 '''
    _name = 'service'
    _description = '收支项'

    name = fields.Char('名称', required=True)
    get_categ_id = fields.Many2one('core.category',
                                   '收入类别', ondelete='restrict',
                                   domain="[('type', '=', 'other_get')]",
                                   context={'type': 'other_get'})
    pay_categ_id = fields.Many2one('core.category',
                                   '支出类别', ondelete='restrict',
                                   domain="[('type', '=', 'other_pay')]",
                                   context={'type': 'other_pay'})
    price = fields.Float('价格', required=True)
    tax_rate = fields.Float('税率%')
    active = fields.Boolean('启用', default=True)
    company_id = fields.Many2one(
        'res.company',
        string='公司',
        change_default=True,
        default=lambda self: self.env.company)
