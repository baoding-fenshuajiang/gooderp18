# Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "GoodERP 出纳模块",
    'author': "上海开阖软件有限公司",
    'website': "http://www.gooderp.org",
    'category': 'gooderp',
    "description":
    '''
    该模块实现了 GoodERP 中 出纳 的功能。

    通过创建收付款单，审核后来完成预收预付的功能；如果有结算单明细行，可以完成核销的功能。
    可以查看所有结算单。
    通过创建核销单，审核后完成核销的功能，包括预收冲应收、预付冲应付、应收冲应付、应收转应收、应付转应付几种业务类型。
    通过创建其他收支出单，审核后完成其他收支的功能。
    通过创建资金转账单，审核后完成资金转账的功能。

    出纳管理的报表有：
    客户对账单；
    供应商对账单；
    现金银行报表；
    其他收支明细。
    ''',
    'version': '18.0',
    "license": "AGPL-3",
    'depends': ['finance'],
    'data': [
        'data/money_data.xml',
        'data/cash_flow_data.xml',
        'security/groups.xml',
        'views/cash_flow_view.xml',
        'views/money_order_view.xml',
        'views/other_money_order_view.xml',
        'views/money_transfer_order_view.xml',
        'views/reconcile_order_view.xml',
        'data/money_sequence.xml',
        'wizard/partner_statements_wizard_view.xml',
        'report/bank_statements_view.xml',
        'wizard/bank_statements_wizard_view.xml',
        'report/other_money_statements_view.xml',
        'wizard/other_money_statements_wizard_view.xml',
        'wizard/money_get_pay_wizard_view.xml',
        'report/money_get_pay_view.xml',
        'wizard/partner_statements_wizard_simple_view.xml',
        'wizard/cash_flow_wizard_view.xml',
        'report/customer_statements_view.xml',
        'report/supplier_statements_view.xml',
        'security/ir.model.access.csv',
        'views/partner_view.xml',
        'views/generate_accounting.xml',
        'report/report_data.xml',
        'report/print_money_order.xml',
    ],
    'demo': [
        'demo/money_demo.xml',
    ],
}
