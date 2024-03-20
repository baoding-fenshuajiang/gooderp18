# Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "GoodERP 会计模块",
    'author': "上海开阖软件有限公司",
    'website': "http://www.gooderp.org",
    'category': 'gooderp',
    "license": "AGPL-3",
    "description":
    '''
该模块实现了 GoodERP 中 会计 的功能。

可以创建新的会计凭证；
可以定义会计凭证模板；
可以进行月末结账；
可以查看月末凭证变更记录。

会计实现的报表有：
    分录查询；
    科目余额表；
    资产负债表；
    利润表；
    发出成本；
    科目明细账；
    科目总账；
    辅助核算余额表。
    ''',
    'depends': ['core'],
    'version': '18.0',
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/finance_voucher_data.xml',
        'data/finance_period_data.xml',
        'report/report_voucher.xml',
        'views/res_config_view.xml',
        'views/finance_conf.xml',
        'wizard/checkout_wizard.xml',
        'views/finance_view.xml',
        'views/voucher_template.xml',
        'views/company.xml',
        'views/trial_balance.xml',
        'views/balance_sheet.xml',
        'views/issue_cost_wizard.xml',
        'views/report_auxiliary_accounting.xml',
        'views/exchange.xml',
    ],
    'demo': [
        'data/finance_account_data.xml',
        'data/finance_demo.xml',
    ],
}
