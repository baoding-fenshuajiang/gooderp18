# Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models
from odoo.tools import date_utils
import logging

_logger = logging.getLogger(__name__)


class PayMethod(models.Model):
    _name = 'pay.method'
    _description = '付款条件'

    name = fields.Char('名称')
    add_months = fields.Integer(
        string='月数',
    )
    add_days = fields.Integer(
        string='天数',
    )

    def get_due_date(self, key_date=None):
        # 先加月数算到月底，再加天数
        if not key_date:
            key_date = fields.Date.context_today(self)
        due_date = key_date
        if self.add_months:
            due_date = date_utils.add(due_date, months=self.add_months)
            due_date = date_utils.end_of(due_date, 'month')
        if self.add_days:
            due_date = date_utils.add(due_date, days=self.add_days)
        _logger.info('%s的单据%s的到期日为%s' % (key_date, self.name, due_date))
        return due_date
