# Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import http
from json import dumps
from datetime import datetime


class ActionStatistics(http.Controller):
    '''用于统计用户点击次数并记录在www.gooderp.org'''

    @http.route('/get_user_info', auth='public')
    def get_user_info(self):
        '''获取当前用户名称等信息'''
        user = http.request.env.user

        return dumps({
            'user': user.name,
            'login': user.login,
            'company': user.company_id.name,
            'company_phone': user.company_id.phone,
            'company_start_date': '2018-08-18',
            'company_slistt': user.company_id.slistt
        })
