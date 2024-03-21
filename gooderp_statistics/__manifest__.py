# Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "GoodERP Statistics",
    "version": '18.0',
    "author": '上海开阖软件有限公司',
    "website": "http://www.gooderp.org",
    "category": "gooderp",
    "license": "AGPL-3",
    "description": """
    """,
    "depends": ['web'],
    'assets': {
        'web.assets_backend': ['gooderp_statistics/static/src/js/main.js',
                               'gooderp_statistics/static/src/xml/main.xml']
    },
    'data': ['views/patch_views.xml',],
    'auto_install': True,
}
