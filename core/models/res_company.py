# Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, tools
from odoo.exceptions import UserError
from odoo.tools import misc
import re
import base64

# 成本计算方法，这里选择后商品上可以不选，从这里取
CORE_COST_METHOD = [('average', '全月一次加权平均法'),
                    ('std', '定额成本'),
                    ('fifo', '个别计划法'),
                    ]


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.constrains('email')
    def _check_email(self):
        ''' 验证 email 合法性 '''
        for company in self:
            if company.email:
                res = re.match(
                    '^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$',
                    company.email)
                if not res:
                    raise UserError('请检查邮箱格式是否正确: %s' % company.email)

    start_date = fields.Date(
        '启用日期',
        required=True,
        default=lambda self: fields.Date.context_today(self))
    cost_method = fields.Selection(
        CORE_COST_METHOD,
        '存货计价方法',
        help='''GoodERP仓库模块使用个别计价规则匹配
                每次出库对应入库成本和数量，但不实时记账。
                财务月结时使用此方法相应调整发出成本''',
        default='average', required=True)
    draft_invoice = fields.Boolean(
        '根据发票确认应收应付',
        help='勾选这里，所有新建的结算单不会自动记账')
    import_tax_rate = fields.Float(string="默认进项税税率")
    output_tax_rate = fields.Float(string="默认销项税税率")
    bank_account_id = fields.Many2one('bank.account', string='开户行')
    sign = fields.Binary('签章')

    def _get_logo(self):
        return self._get_logo_impl()

    def _get_logo_impl(self):
        ''' 默认取 core/static/description 下的 logo.png 作为 logo'''
        return base64.b64encode(
            open(misc.file_open(
                'core/static/description/logo.png').name, 'rb'
            ).read())

    def _get_html_table(self, vl):
        # vl = {'col':[],'val':[[]]}
        res = "<table style='width:100%;text-align:right'><tr>"
        for th in vl['col']:
            res += "<th>%s</th>" % th
        res += "</tr>"
        for line in vl['val']:
            res += "<tr>"
            for v in line:
                res += "<td>%s</td>" % v
            res += "</tr>"
        res += "</table>"
        return res

    logo = fields.Binary(related='partner_id.image_1920',
                         default=_get_logo, attachment=True)
