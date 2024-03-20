# Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "警告窗口",
    "summary": "弹窗提示用户是否继续执行",
    "version": '18.0',
    "author": '上海开阖软件有限公司',
    "website": "http://www.gooderp.org",
    "category": "gooderp",
    "license": "AGPL-3",
    "description": """
odoo框架里缺失一个很重要的功能，就是警告级别的消息提示。

ERP里的逻辑处理一般可以返回三个级别的提示，成功、失败和需要确认。

针对失败的场景，odoo的raise UserError是弹窗报错，前面步骤全部回滚。

针对成功的场景，odoo支持在方法最后返回client action给一个右上角的消息框。

但是针对执行到一半需要用户确认是否继续执行的场景，odoo没有直接的实现方案。

我们这个模块就是补足odoo框架的这个不足。

我们在 BaseModel 上增加了一个 open_dialog 方法。

用于在同模型的Python方法中根据需要调用, 并根据用户在弹窗上的反馈决定是继续执行还是终止。

open_dialog(func, options=None)函数

- @func: 函数名称字符串，属于当前model的函数
- @options：一个字典，里面可以传入一些具体参数
    - @message: 向导的具体内容
    - @args：调用函数的时候传入的args参数
    - @kwargs：调用函数的时候传入的kwargs参数
    """,
    "data": [
        'wizard/common_dialog_wizard_view.xml',
        'security/ir.model.access.csv',
    ],
}
