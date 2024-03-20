# Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class ProfitStatement(models.Model):
    """利润表模板
        模板主要用来定义项目的 科目范围,
        然后根据科目的范围得到科目范围内的科目 的利润

    """
    _name = "profit.statement"
    _order = "sequence,id"
    _description = '利润表模板'

    sequence = fields.Integer('序号')

    balance = fields.Char('项目', help='报表的行次的总一个名称')
    line_num = fields.Char('行次', help='生成报表的行次')
    cumulative_occurrence_balance = fields.Float('本年累计金额', help='本年利润金额')
    occurrence_balance_formula = fields.Text(
        '科目范围', help='设定本行的利润的科目范围，例如1001~1012999999 结束科目尽可能大一些方便以后扩展')
    current_occurrence_balance = fields.Float('本月金额', help='本月的利润的金额')
    company_id = fields.Many2one(
        'res.company',
        string='公司',
        change_default=True,
        default=lambda self: self.env.company)


class Dupont(models.Model):
    _name = 'dupont'
    _description = '企业财务指标'
    _rec_name = 'period_id'
    _order = 'period_id'

    period_id = fields.Many2one('finance.period', '期间', index=True)
    kpi = fields.Char('指标')
    val = fields.Float('值', digits='Amount')

    @api.model
    def fill(self, period_id):

        if self.search([('period_id', '=', period_id.id)]):
            return True

        ta = te = income = ni = roe = roa = em = 0.0

        for b in self.env['trial.balance'].search(
                [('period_id', '=', period_id.id)]):
            if b.subject_name_id.costs_types == 'assets':
                ta += b.ending_balance_debit - b.ending_balance_credit
            if b.subject_name_id.costs_types == 'equity':
                te += b.ending_balance_credit - b.ending_balance_debit
            if b.subject_name_id.costs_types == 'in':
                income += b.current_occurrence_credit
            if b.subject_name_id == self.env.user.company_id.profit_account:
                ni = b.current_occurrence_credit

        roe = te and ni / te * 100
        roa = ta and ni / ta * 100
        em = te and ta / te * 100
        res = {'资产': ta, '权益': te, '收入': income, '净利': ni,
               '权益净利率': roe, '资产净利率': roa, '权益乘数': em}
        for k in res:
            self.create({'period_id': period_id.id, 'kpi': k, 'val': res[k]})
