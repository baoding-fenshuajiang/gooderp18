# Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestCommonDialogWizard(TransactionCase):

    def setUp(self):
        '''准备数据'''
        super(TestCommonDialogWizard, self).setUp()
        # 公司对应的联系人记录
        self.partner = self.env.ref('base.main_partner')

    def test_do_confirm(self):
        '''弹窗确认按钮，正常情况'''
        new_mobile = '13333333333'
        self.assertNotEqual(self.partner.mobile, new_mobile)
        self.partner.open_dialog('write',
                                 {'args': [{'mobile': new_mobile}]})
        wizard = self.env['common.dialog.wizard'].with_context({
            'active_ids': self.partner.id,
            'active_model': self.partner._name,
            'func': 'write',
            'args': [{'mobile': new_mobile}],
        }).create({})
        wizard.do_confirm()
        self.assertEqual(self.partner.mobile, new_mobile)

    def test_do_confirm_no_func(self):
        '''弹窗确认按钮，不传func时应报错'''
        wizard = self.env['common.dialog.wizard'].with_context({
            'active_ids': self.partner.id,
            'active_model': self.partner._name,
            'func': '',
        }).create({})
        with self.assertRaises(ValueError):
            wizard.do_confirm()

    def test_do_confirm_no_active_ids(self):
        '''弹窗确认按钮，不传active_ids,active_model 时应报错'''
        wizard = self.env['common.dialog.wizard'].with_context({
            'active_ids': False,
            'active_model': '',
            'func': 'write',
        }).create({})
        with self.assertRaises(ValueError):
            wizard.do_confirm()
