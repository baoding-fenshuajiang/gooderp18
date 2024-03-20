# Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class BalanceSheet(models.Model):
    """资产负债表模板
    模板用来定义最终输出的 资产负债表的格式,
     每行的 科目的顺序 科目的大分类的所属的子科目的顺序
    -- 本模板适合中国会计使用.
    """

    _name = "balance.sheet"
    _order = "sequence,id"
    _description = '资产负债表模板'

    sequence = fields.Integer('顺序号')
    line = fields.Integer('序号', required=True, help='资产负债表的行次')
    balance = fields.Char('资产')
    line_num = fields.Char('行次', help='此处行次并不是出报表的实际的行数,只是显示用的用来符合国人习惯')
    ending_balance = fields.Float('期末数')
    balance_formula = fields.Text(
        '科目范围', help='设定本行的资产负债表的科目范围，例如1001~1012999999 结束科目尽可能大一些方便以后扩展')
    beginning_balance = fields.Float('年初数')

    balance_two = fields.Char('负债和所有者权益')
    line_num_two = fields.Char('行次 ', help='此处行次并不是出报表的实际的行数,只是显示用的用来符合国人习惯')
    ending_balance_two = fields.Float('期末数 ')
    balance_two_formula = fields.Text(
        '科目范围 ', help='设定本行的资产负债表的科目范围，例如1001~1012999999 结束科目尽可能大一些方便以后扩展')
    beginning_balance_two = fields.Float('年初数 ', help='报表行本年的年余额')
    company_id = fields.Many2one(
        'res.company',
        string='公司',
        change_default=True,
        default=lambda self: self.env.company)
