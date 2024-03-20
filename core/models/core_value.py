# Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class CoreValue(models.Model):
    '''
    当客户要求下拉字段可编辑，可使用此表存储可选值
    按type分类，在字段上用domain和context筛选
    '''
    _name = 'core.value'
    _description = '可选值'

    name = fields.Char('名称', required=True)
    type = fields.Char('类型', required=True,
                       default=lambda self: self._context.get('type'))
    note = fields.Text(
        string='备注',
        help='此字段用于详细描述该可选值的意义，或者使用一些特殊字符作为程序控制的标识'
    )
    parent_id = fields.Many2one('core.value', '上级')
    color = fields.Integer('Color Index')
    active = fields.Boolean('启用', default=True)
    company_id = fields.Many2one(
        'res.company',
        string='公司',
        change_default=True,
        default=lambda self: self.env.company)

    _sql_constraints = [
        ('name_uniq', 'unique(type,name)', '同类可选值不能重名')
    ]
