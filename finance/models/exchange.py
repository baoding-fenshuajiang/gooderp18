# Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class Currency(models.Model):
    _inherit = 'res.currency'

    def get_rate_silent(self, date, currency_id):
        currency = self.env['res.currency'].search([('id', '=', currency_id)])
        rate = currency.rate
        return rate


class RatePeriod(models.Model):
    """记录本月结算汇兑损益时的汇率，用于反结算后，汇兑损益正确时汇率正确"""
    _name = "rate.period"
    _description = '记录本月结算汇兑损益时的汇率'

    name = fields.Many2one('res.currency', '币别', required=True)
    account_accumulated_depreciation = fields.Many2one(
        'finance.account', '累计折旧科目', required=True)
    account_asset = fields.Many2one(
        'finance.account', '固定资产科目', required=True)
    account_depreciation = fields.Many2one(
        'finance.account', '折旧费用科目', required=True)
    company_id = fields.Many2one(
        'res.company',
        string='公司',
        change_default=True,
        default=lambda self: self.env.company)
