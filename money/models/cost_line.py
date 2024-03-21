# Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api


class CostLine(models.Model):
    _name = 'cost.line'
    _description = "采购销售费用"

    @api.depends('amount', 'tax_rate')
    def _compute_tax(self):
        """
        计算字段根据 amount 和 tax_rate 是否变化进行判定tax 是否需要重新计算
        :return:
        """
        for s in self:
            s.tax = s.amount * s.tax_rate * 0.01

    partner_id = fields.Many2one('partner', '供应商', ondelete='restrict',
                                 required=True,
                                 help='采购/销售费用对应的业务伙伴')
    category_id = fields.Many2one('core.category', '类别',
                                  required=True,
                                  ondelete='restrict',
                                  help='分类：其他支出')
    amount = fields.Float('金额',
                          required=True,
                          digits='Amount',
                          help='采购/销售费用金额')
    tax_rate = fields.Float(
        '税率(%)',
        default=lambda self: self.env.user.company_id.import_tax_rate,
        help='默认值取公司进项税率')
    tax = fields.Float('税额',
                       digits='Amount',
                       compute=_compute_tax,
                       help='采购/销售费用税额')
    note = fields.Char('备注',
                       help='该采购/销售费用添加的一些标识信息')
    company_id = fields.Many2one(
        'res.company',
        string='公司',
        change_default=True,
        default=lambda self: self.env.company)
