# © 2016 Elico Corp (www.elico-corp.com).
# Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
# © 2019 信莱德软件 (www.zhsunlight.cn).
# © 2023 JET (www.snowrise.cn).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Report Docx",
    "version": '18.1.0.0',
    "category": "Report",
    "website": "",
    "author": "Elico Corp, Odoo Community Association (OCA), "
            "开阖软件, "
            "信莱德软件"
            "JET<1150252397@qq.com>"
            "保定-粉刷匠<992102498@qq.com>"
    ,
    'description':
    '''
word模板报表引擎
===========================================================
* 扩展报表数据源，增加支持dict、models.TransientModel作为数据源
* dict 格式数据源同样支持"."操作，与models 获取属性的方式保持一致
* 该模块为 odoo 增加一个新的报表生成引擎
* 使用 word 编写报表 加载图片例：{{p line.goods_id.image | picture(width=’6cm’)}}
* 使用 jinja2 语法，语法参考： http://docs.jinkan.org/docs/jinja2/templates.html
* 支持docx报表、PDF报表直接预览、打印等功能
    ''',
    "depends": [
        "base", "web"
    ],
    'external_dependencies': {
        'python': [
            'docxtpl',
            'docx2pdf',
        ],
    },
    "data": [
        'views/ir_actions.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'demo/report.xml',
    ],
    'assets': {
        'web.assets_backend_lazy': [
            'report_docx/static/src/js/tools.esm.js',
            'report_docx/static/src/js/report.esm.js',
            'report_docx/static/src/js/actionmanager.js',
        ]
    },
    "license": "AGPL-3",
}

