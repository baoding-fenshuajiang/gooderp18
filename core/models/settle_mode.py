# Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SettleMode(models.Model):
    '''
    用于承兑汇票等需要额外记录票号的资金收付业务
    '''
    _name = 'settle.mode'
    _description = '结算方式'

    name = fields.Char('名称', required=True)
    active = fields.Boolean('启用', default=True)
    company_id = fields.Many2one(
        'res.company',
        string='公司',
        change_default=True,
        default=lambda self: self.env.company)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', '结算方式不能重名')
    ]
