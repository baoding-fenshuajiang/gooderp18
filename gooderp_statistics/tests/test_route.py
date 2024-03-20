# Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import HttpCase


class TestActionStatistics(HttpCase):

    def test_user_info(self):
        ''' 获取用户名字 '''
        response = self.url_open('/get_user_info')
        self.assertEqual(response.status_code, 200)
