# Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models

LINE_TYPES = [('get', '销售收款'),
              ('pay', '采购付款'),
              ('category', '其他收支'),
              ('begin', '科目期初'),
              ('end', '科目期末'),
              ('lines', '表行计算')]


class CashFlowTemplate(models.Model):
    _name = 'cash.flow.template'
    _description = '现金流量表模版'
    _order = 'sequence'

    sequence = fields.Integer('序号')
    name = fields.Char('项目')
    line_num = fields.Char('行次')
    line_type = fields.Selection(LINE_TYPES, '行类型')
    # for type sum
    category_ids = fields.Many2many(
        'core.category',
        string='收支类别',
        domain="[('type','in',['other_get','other_pay'])]")
    # for type begin
    begin_ids = fields.Many2many(
        'finance.account',
        relation='cftb',
        string='会计科目期初')
    # for type end
    end_ids = fields.Many2many(
        'finance.account',
        relation='cfte',
        string='会计科目期末')
    # for type lines
    plus_ids = fields.Many2many(
        'cash.flow.template', 'c_p', 'c_id', 'p_id', string='+表行')
    nega_ids = fields.Many2many(
        'cash.flow.template', 'c_n', 'c_id', 'n_id', string='-表行')


class CashFlowStatement(models.Model):
    _name = 'cash.flow.statement'
    _description = '现金流量表'

    name = fields.Char('项目')
    line_num = fields.Char('行次')
    amount = fields.Float('本月金额', digits='Amount')
    year_amount = fields.Float('本年累计金额', digits='Amount')


class CoreCategory(models.Model):
    _inherit = 'core.category'
    cash_flow_template_ids = fields.Many2many(
        'cash.flow.template', string='现金流量表行')
