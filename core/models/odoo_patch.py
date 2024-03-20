# Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.exceptions import UserError

'''
odoo 按日期分组的显示格式不符合中国用户习惯
按月分组显示为【十月 2022】 需改成 【2022-10】
按日期分组显示为 【15 十月 2022】需改成 【2022-10-15】
'''
models.READ_GROUP_DISPLAY_FORMAT = {
    'hour': 'hh:00 dd MM',  # 哪里有按小时分组的？
    'day': 'YYYY-MM-dd',  # 年月日
    'week': "YYYY-'第'w'周'",  # w YYYY = ISO week-year
    'month': 'YYYY-MM',
    'quarter': 'YYYY-QQQ',
    'year': 'YYYY',
}

'''
单据自动编号，避免在所有单据对象上重载create方法
只需在ir.sequence里新增一条code与当前model相同的记录即可实现自动编号
'''
create_original = models.BaseModel.create


@api.model_create_multi
@api.returns('self', lambda value: value.id)
def create(self, vals_list):
    if not self._name.split('.')[0] in ['mail', 'ir', 'res']:
        for vals in vals_list:
            if not vals.get('name'):
                next_name = self.env['ir.sequence'].next_by_code(self._name)
                if next_name:
                    vals.update({'name': next_name})
    record_ids = create_original(self, vals_list)
    return record_ids


models.BaseModel.create = create

'''
不能删除已确认的单据
避免在所有单据对象上重载unlink
删除记录要在ir.logging表里记录
'''

# 部分模型也是用了done这个状态，需要放行
BYPASS_MODELS = [
    'survey.user_input',
    'survey.user_input_line'
    ]
# 部分模型不需要记录删除时的 log
_NOLOG_MODELS = [
        'ir.logging',
        'website.page',
        'mail.message',
        'ir.model.data',
    ]

unlink_original = models.BaseModel.unlink


def unlink(self):
    IrLogging = self.env['ir.logging']
    field_list = [item[0] for item in self._fields.items()]
    for record in self:
        if record.is_transient():
            continue
        if 'state' in field_list and self._name not in BYPASS_MODELS:
            if record.state == 'done':
                raise UserError('不能删除已确认的 %s ！' % record._description)
        if self._name in _NOLOG_MODELS or not record.display_name:
            continue
        IrLogging.sudo().create({
                'name': record.display_name,
                'type': 'client',
                'dbname': self.env.cr.dbname,
                'level': 'WARN',
                'message': '%s被删除' % self._name,
                'path': self.env.user.name,
                'func': 'delete',
                'line': 1})
    unlink_original(self)


models.BaseModel.unlink = unlink

'''
在所有模型上增加了作废方法
'''


def action_cancel(self):
    for record in self:
        record.state = 'cancel'
    return True


models.BaseModel.action_cancel = action_cancel
