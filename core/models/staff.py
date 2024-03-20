# Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError


class Staff(models.Model):
    _name = 'staff'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = '员工'

    user_id = fields.Many2one('res.users', '对应用户')
    company_id = fields.Many2one(
        'res.company',
        string='公司',
        change_default=True,
        default=lambda self: self.env.company)

    @api.constrains('user_id')
    def _check_user_id(self):
        '''一个员工只能对应一个用户'''
        for staff in self:
            staffs = []
            if staff.user_id:
                staffs = self.env['staff'].search(
                    [('user_id', '=', staff.user_id.id)])
            if len(staffs) > 1:
                raise UserError('用户 %s 已有对应员工' % staff.user_id.name)
