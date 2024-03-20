# Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "GoodERP 核心模块",
    'author': "上海开阖软件有限公司",
    'summary': '隐藏Odoo内置技术复杂性，增加基本权限组',
    'website': "http://www.gooderp.org",
    'category': 'gooderp',
    "license": "AGPL-3",
    "description":
    '''
该模块是 gooderp 的核心模块，完成了基本表的定义和配置。

定义了基本类，如 partner,bank_account,goods,staff,uom等；
定义了基本配置： 用户、类别等；
定义了高级配置： 系统参数、定价策略。
    ''',
    'version': '18.0',
    'depends': ['web',
                'mail',
                'common_dialog',
                ],
    'excludes': ['product'],
    'demo': [
        'data/core_demo.xml',
    ],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/core_data.xml',
        'views/core_view.xml',
    ],
}
