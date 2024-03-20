# Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class BankAccount(models.Model):
    _name = 'bank.account'
    _description = '账户'

    name = fields.Char('名称', required=True)
    num = fields.Char('账号')
    balance = fields.Float('余额', readonly=True,
                           digits='Amount')
    active = fields.Boolean('启用', default=True)
    company_id = fields.Many2one(
        'res.company',
        string='公司',
        change_default=True,
        default=lambda self: self.env.company)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', '账户不能重名')
    ]
