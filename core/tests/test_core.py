# Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta
from odoo.tests.common import TransactionCase
from psycopg2 import IntegrityError
from odoo.exceptions import UserError
from odoo.tools import mute_logger
from odoo import fields


class TestCore(TransactionCase):

    def test_partner(self):
        ''' 测试删除已有客户的分类报错 '''
        with mute_logger('odoo.sql_db'):
            with self.assertRaises(IntegrityError):
                self.env.ref('core.customer_category_1').unlink()

    def test_partner_name_search(self):
        """
        partner在many2one字段中支持按编号搜索
        """
        partner = self.env.ref('core.jd')
        # 使用 name 来搜索京东
        result = self.env['partner'].name_search('京东')
        real_result = [(partner.id, partner.name)]
        self.assertEqual(result, real_result)
        # 使用 code 来搜索京东
        res = self.env['partner'].name_search('jd')
        self.assertEqual(res, real_result)

        # 编号 ilike
        partner.code = '京东'
        res = self.env['partner'].name_search('京')
        self.assertEqual(res, real_result)

    def test_partner_write(self):
        ''' 测试 业务伙伴应收/应付余额不为0时，不允许取消对应的客户/供应商身份 '''
        partner = self.env.ref('core.jd')
        partner.receivable = 100
        with self.assertRaises(UserError):
            partner.c_category_id = False

        partner = self.env.ref('core.lenovo')
        partner.payable = 100
        with self.assertRaises(UserError):
            partner.s_category_id = False
        partner.copy()

    def test_res_currency(self):
        """测试阿拉伯数字转换成中文大写数字的方法"""
        self.env['res.currency'].rmb_upper(10000100.3)
        # 测试输入value为负时的货币大写问题
        self.assertTrue(
            self.env['res.currency'].rmb_upper(-10000100.3) == '负壹仟万零壹佰元叁角整')

    def test_compute_days_qualify(self):
        """计算资质到期天数。"""
        partner = self.env.ref('core.jd')
        partner.date_qualify = fields.Date.today() + relativedelta(
                days=1)
        self.assertEqual(partner.days_qualify, 1)

    def test_check_category_exists(self):
        ''' test_check_category_exists '''
        partner = self.env.ref('core.jd')
        with self.assertRaises(UserError):
            partner.c_category_id = False

    def test_unlink_category_with_note(self):
        ''' 系统创建的类别不可以删除 '''
        cate = self.env.ref('core.cat_donate')
        cate.note = 'A'
        with self.assertRaises(UserError):
            cate.unlink()

    def test_name_for_create(self):
        self.env['ir.sequence'].create({
            'name': 'number for bank account',
            'code': 'bank.account'})
        self.env['bank.account'].create({})

    def test_pay_mathod(self):
        self.env.ref('core.main_pay_method').get_due_date()


class TestGoods(TransactionCase):

    def test_create(self):
        g = self.env['goods'].create({
            'name': 'test',
            'code': 'cod',
            'category_id': self.env.ref('core.goods_category_1').id,
            'uom_id': self.env.ref('core.uom_pc').id,
        })
        self.env['goods'].name_search('cod')
        self.env['goods'].name_search('co')
        n = g.copy()
        self.assertEqual(n.name, g.name + ' (copy)')


class TestResUsers(TransactionCase):

    def test_write(self):
        '''修改管理员权限'''
        user_demo = self.env.ref('base.user_demo')
        user_demo.groups_id = [(4, self.env.ref('base.group_erp_manager').id)]
        user_admin = self.env.ref('base.user_admin').with_user(user_demo)
        with self.assertRaises(UserError):
            user_admin.name = 'adsf'
        with self.assertRaises(UserError):
            user_admin.groups_id = [
                (3, self.env.ref('base.group_erp_manager').id)]
        # 新建用户邮箱填成 @
        tuser = self.env['res.users'].create({
            'name': 'test_email',
            'login': 'test_email',
        })
        # 同时创建两个员工指向相同用户报错
        self.env['staff'].create({'user_id': tuser.id})
        with self.assertRaises(UserError):
            self.env['staff'].create({'user_id': tuser.id})


class TestResCompany(TransactionCase):
    def test_get_logo(self):
        ''' 取默认logo '''
        self.env['res.company'].create({
            'name': 'demo company',
            'partner_id': self.env.ref('core.zt').id
        })

    def test_check_email(self):
        ''' test check email '''
        company = self.env['res.company'].create({
            'name': 'demo company',
            'partner_id': self.env.ref('core.zt').id
        })
        # 邮箱格式正确
        company.email = 'gooderp@osbzr.com'

        # 邮箱格式不正确，报错
        with self.assertRaises(UserError):
            company.email = 'gooderp'

    def test_get_html_table(self):
        self.env.company._get_html_table({
            'col': ['name'],
            'val': [['jeff']]})


class TestWarehouse(TransactionCase):
    def test_search(self):
        self.env['warehouse'].name_search('General')
        self.env['warehouse'].name_search('')
        # 错误的仓库类型报错
        with self.assertRaises(UserError):
            self.env['warehouse'].get_warehouse_by_type('wrong_type')
        # 没有客户类型的仓库
        with self.assertRaises(UserError):
            self.env['warehouse'].get_warehouse_by_type('customer')
        self.env['warehouse'].get_warehouse_by_type('stock')
