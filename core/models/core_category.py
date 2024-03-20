# Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models
from odoo.exceptions import UserError

# 分类的类别
CORE_CATEGORY_TYPE = [('customer', '客户'),
                      ('supplier', '供应商'),
                      ('goods', '商品'),
                      ('expense', '采购'),
                      ('income', '收入'),
                      ('other_pay', '其他支出'),
                      ('other_get', '其他收入'),
                      ('attribute', '商品属性'),  # 非会计相关
                      ('finance', '核算')]


class CoreCategory(models.Model):
    ''' GoodERP实现自动生成会计凭证的核心对象 '''
    _name = 'core.category'
    _description = '类别'
    _order = 'type, name'

    name = fields.Char('名称', required=True)
    type = fields.Selection(CORE_CATEGORY_TYPE, '类型',
                            required=True,
                            default=lambda self: self._context.get('type'))
    note = fields.Text('备注')
    active = fields.Boolean('启用', default=True)
    company_id = fields.Many2one(
        'res.company',
        string='公司',
        change_default=True,
        default=lambda self: self.env.company)

    _sql_constraints = [
        ('name_uniq', 'unique(type, name)', '同类型的类别不能重名')
    ]

    def unlink(self):
        for record in self:
            if record.note:
                raise UserError('不能删除系统创建的类别')

        return super(CoreCategory, self).unlink()
