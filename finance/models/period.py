# Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import calendar
from datetime import datetime

from odoo import api, fields, models
from odoo.exceptions import UserError

MONTH_SELECTION = [
    ('1', '01'),
    ('2', '02'),
    ('3', '03'),
    ('4', '04'),
    ('5', '05'),
    ('6', '06'),
    ('7', '07'),
    ('8', '08'),
    ('9', '09'),
    ('10', '10'),
    ('11', '11'),
    ('12', '12')]


class FinancePeriod(models.Model):
    '''会计期间'''
    _name = 'finance.period'
    _order = 'name desc'
    _description = '会计期间'

    name = fields.Char(
        '会计期间',
        compute='_compute_name', readonly=True, store=True)
    is_closed = fields.Boolean('已结账', help='这个字段用于标识期间是否已结账，已结账的期间不能生成会计凭证。')
    year = fields.Char('会计年度', required=True, help='会计期间对应的年份')
    month = fields.Selection(
        MONTH_SELECTION, string='会计月份', required=True, help='会计期间对应的月份')
    company_id = fields.Many2one(
        'res.company',
        string='公司',
        change_default=True,
        default=lambda self: self.env.company)

    @api.depends('year', 'month')
    def _compute_name(self):
        """
        根据填写的月份年份 设定期间的name值
        :return: None
        """
        for p in self:
            if p.year and p.month:
                p.name = '%s%s' % (p.year, str(p.month).zfill(2))

    def period_compare(self, period_id_one, period_id_two):
        """
        比较期间的大小
        :param period_id_one: 要比较的期间 1
        :param period_id_two:要比较的期间 2
        :return: 1 0 -1 分别代表 期间1 大于 等于 小于 期间2
        """
        period_one_str = "%s-%s" % (period_id_one.year,
                                    str(period_id_one.month).zfill(2))
        period_two_str = "%s-%s" % (period_id_two.year,
                                    str(period_id_two.month).zfill(2))
        if period_one_str > period_two_str:
            return 1
        elif period_one_str < period_two_str:
            return -1
        else:
            return 0

    @api.model
    def init_period(self):
        ''' 根据系统启用日期（安装core模块的日期）创建 '''
        current_date = self.env.ref('base.main_company').start_date
        period_id = self.search([
            ('year', '=', current_date.year),
            ('month', '=', current_date.month)
        ])
        if not period_id:
            return self.create({'year': current_date.year,
                                'month': str(current_date.month)})

    @api.model
    def get_init_period(self):
        '''系统启用的期间'''
        start_date = self.env.ref('base.main_company').start_date
        period_id = self.search([
            ('year', '=', start_date.year),
            ('month', '=', start_date.month)
        ])
        return period_id

    def get_date_now_period_id(self):
        """
        默认是当前会计期间
        :return: 当前会计期间的对象 如果不存在则返回 False
        """
        datetime_str = datetime.now().strftime("%Y-%m-%d")
        datetime_str_list = datetime_str.split('-')
        period_row = self.search(
            [('year', '=', datetime_str_list[0]),
             ('month', '=', str(int(datetime_str_list[1])))])
        return period_row and period_row[0]

    def get_period_month_date_range(self, period_id):
        """
        取得 period_id 期间的第一天 和最后一天
        :param period_id: 要取得一个月 最后一天和第一天的期间
        :return: 返回一个月的第一天和最后一天 （'2016-01-01','2016-01-31'）
        """
        month_day_range = calendar.monthrange(
            int(period_id.year), int(period_id.month))
        return ("%s-%s-01" % (
                    period_id.year,
                    period_id.month.zfill(2)),
                "%s-%s-%s" % (
                    period_id.year,
                    period_id.month.zfill(2),
                    str(month_day_range[1])))

    def get_year_fist_period_id(self):
        """
            获取本年创建过的第一个会计期间
            :return: 当前会计期间的对象 如果不存在则返回 False
            """
        datetime_str = datetime.now().strftime("%Y-%m-%d")
        datetime_str_list = datetime_str.split('-')
        period_row = self.search(
            [('year', '=', datetime_str_list[0])])
        period_list = sorted(map(int, [period.month for period in period_row]))
        if not period_row[0]:
            raise UserError('日期%s所在会计期间不存在！' % datetime_str)
        fist_period = self.search(
            [('year', '=', datetime_str_list[0]),
             ('month', '=', period_list[0])], order='name')
        return fist_period

    def get_period(self, date):
        """
        根据参数date 得出对应的期间
        :param date: 需要取得期间的时间
        :return: 对应的期间
        """
        if date:
            period_id = self.search([
                ('year', '=', date.year),
                ('month', '=', date.month)
            ])
            if period_id:
                if period_id.is_closed and self._context.get(
                            'module_name', False) != 'checkout_wizard':
                    raise UserError('会计期间%s已关闭' % period_id.name)
            else:
                # 会计期间不存在，创建会计期间
                period_id = self.create(
                    {'year': date.year, 'month': str(date.month)})
            return period_id

    def search_period(self, date):
        """
        根据参数date 得出对应的期间
        :param date: 需要取得期间的时间
        :return: 对应的期间
        """
        if date:
            period_id = self.search([
                ('year', '=', date.year),
                ('month', '=', date.month)
            ])
            return period_id

    _sql_constraints = [
        ('period_uniq', 'unique (year,month)', '会计期间不能重复'),
    ]
