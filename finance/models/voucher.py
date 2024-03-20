# Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

# 字段只读状态
READONLY_STATES = {
    'done': [('readonly', True)],
    'cancel': [('readonly', True)],
}


class Voucher(models.Model):
    '''新建凭证'''
    _name = 'voucher'
    _inherit = ['mail.thread']
    _order = 'period_id, name desc'
    _description = '会计凭证'

    @api.model
    def _default_voucher_date(self):
        return self._default_voucher_date_impl()

    @api.model
    def _default_voucher_date_impl(self):
        ''' 获得默认的凭证创建日期 '''
        voucher_setting = self.env['ir.default']._get(
            'finance.config.settings', 'defaul_voucher_date')
        now_date = fields.Date.context_today(self)
        if voucher_setting == 'last' and self.search([], limit=1):
            create_date = self.search([], limit=1).date
        else:
            create_date = now_date
        return create_date

    @api.model
    def _select_objects(self):
        models = self.env['ir.model'].search(
            [])
        return [(model.model, model.name) for model in models]

    @api.depends('date')
    def _compute_period_id(self):
        for v in self:
            v.period_id = self.env['finance.period'].get_period(v.date)

    document_word_id = fields.Many2one(
        'document.word', '凭证字', ondelete='restrict', required=True,
        default=lambda self: self.env.ref('finance.document_word_1'))
    date = fields.Date('凭证日期', required=True, default=_default_voucher_date,
                       states=READONLY_STATES,
                       tracking=True, help='本张凭证创建的时间', copy=False)
    name = fields.Char('凭证号', tracking=True, copy=False)
    att_count = fields.Integer(
        '附单据', default=1, help='原始凭证的张数', states=READONLY_STATES)
    period_id = fields.Many2one(
        'finance.period',
        '会计期间',
        compute='_compute_period_id',
        ondelete='restrict',
        store=True,
        help='本张凭证发生日期对应的，会计期间')
    line_ids = fields.One2many(
        'voucher.line',
        'voucher_id',
        '凭证明细',
        copy=True,
        states=READONLY_STATES,)
    amount_text = fields.Float('总计', compute='_compute_amount', store=True,
                               tracking=True, digits='Amount', help='凭证金额')
    state = fields.Selection([('draft', '草稿'),
                              ('done', '已确认'),
                              ('cancel', '已作废')], '状态', default='draft',
                             index=True,
                             tracking=True, help='凭证所属状态!')
    is_checkout = fields.Boolean('结账凭证', help='是否是结账凭证')
    is_init = fields.Boolean('是否初始化凭证', help='是否是初始化凭证')
    company_id = fields.Many2one(
        'res.company',
        string='公司',
        change_default=True,
        default=lambda self: self.env.company)
    ref = fields.Reference(string='前置单据',
                           selection='_select_objects')
    brief = fields.Char('摘要', related="line_ids.name", store=True)
    details = fields.Html('明细', compute='_compute_details')

    @api.depends('line_ids')
    def _compute_details(self):
        for v in self:
            vl = {'col': ['往来单位', '科目', '借方', '贷方'], 'val': []}
            for line in v.line_ids:
                vl['val'].append([line.partner_id.name or '', line.account_id.name, line.debit, line.credit])
            v.details = v.company_id._get_html_table(vl)

    def voucher_done(self):
        """
        确认 凭证按钮 所调用的方法
        :return: 主要是把 凭证的 state改变
        """
        for v in self:
            if v.state == 'done':
                raise UserError('凭证%s已经确认,请不要重复确认！' % v.name)
            if v.date < self.env.company.start_date:
                raise UserError('凭证日期不可早于启用日期')
            if v.period_id.is_closed:
                raise UserError('该会计期间已结账！不能确认')
            if not v.line_ids:
                raise ValidationError('请输入凭证行')
            for line in v.line_ids:
                if line.debit + line.credit == 0:
                    raise ValidationError(
                        '单行凭证行 %s 借和贷不能同时为0' % line.account_id.name)
                if line.debit * line.credit != 0:
                    raise ValidationError(
                        '单行凭证行不能同时输入借和贷\n 摘要为%s的凭证行 借方为:%s 贷方为:%s' %
                        (line.name, line.debit, line.credit))
            debit_sum = sum([line.debit for line in v.line_ids])
            credit_sum = sum([line.credit for line in v.line_ids])
            precision = self.env['decimal.precision'].precision_get('Amount')
            debit_sum = round(debit_sum, precision)
            credit_sum = round(credit_sum, precision)
            if debit_sum != credit_sum:
                raise ValidationError('借贷方不平，无法确认!\n 借方合计:%s 贷方合计:%s' %
                                      (debit_sum, credit_sum))

            v.state = 'done'
            if v.is_checkout:   # 月结凭证不做反转
                return True
            for line in v.line_ids:
                if line.account_id.costs_types == 'out' and line.credit:
                    # 费用类科目只能在借方记账,比如银行利息收入
                    line.debit = -line.credit
                    line.credit = 0
                if line.account_id.costs_types == 'in' and line.debit:
                    # 收入类科目只能在贷方记账,比如退款给客户的情况
                    line.credit = -line.debit
                    line.debit = 0

    def voucher_can_be_draft(self):
        for v in self:
            if v.ref:
                raise UserError('不能撤销确认由其他单据生成的凭证！')
        self.voucher_draft()

    def voucher_draft(self):
        for v in self:
            if v.state == 'draft':
                raise UserError('凭证%s已经撤销确认,请不要重复撤销！' % v.name)
            if v.period_id.is_closed:
                raise UserError('%s期 会计期间已结账！不能撤销确认' % v.period_id.name)

            v.state = 'draft'

    @api.depends('line_ids')
    def _compute_amount(self):
        for v in self:
            v.amount_text = str(sum([line.debit for line in v.line_ids]))

    # 重载write 方法
    def write(self, vals):
        for order in self:  # 还需要进一步优化
            if self.env.context.get('call_module', False) == "checkout_wizard":
                return super().write(vals)
            if order.period_id.is_closed is True:
                raise UserError('%s期 会计期间已结账，凭证不能再修改！' % order.period_id.name)
            return super().write(vals)


class VoucherLine(models.Model):
    '''凭证明细'''
    _name = 'voucher.line'
    _description = '会计凭证明细'

    @api.model
    def _default_get(self, data):
        ''' 给明细行摘要、借方金额、贷方金额字段赋默认值 '''
        move_obj = self.env['voucher']
        total = 0.0
        context = self._context
        # odoo16没这个函数
        # if context.get('line_ids'):
        # for move_line_dict in move_obj.resolve_2many_commands(
        #     'line_ids', context.get('line_ids')):
        #     data['name'] = data.get('name') or move_line_dict.get('name')
        #     total += move_line_dict.get('debit', 0.0) - \
        #         move_line_dict.get('credit', 0.0)
        # data['debit'] = total < 0 and -total or 0.0
        # data['credit'] = total > 0 and total or 0.0
        return data

    @api.model
    def default_get(self, fields):
        ''' 创建记录时，根据字段的 default 值和该方法给字段的赋值 来给 记录上的字段赋默认值 '''
        fields_data = super(VoucherLine, self).default_get(fields)
        data = self._default_get(fields_data)
        # 判断 data key是否在 fields 里，如果不在则删除该 key。程序员开发用
        for f in list(data.keys()):
            if f not in fields:
                del data[f]
        return data

    voucher_id = fields.Many2one('voucher', '对应凭证', ondelete='cascade')
    name = fields.Char('摘要', required=True, help='描述本条凭证行的缘由')
    account_id = fields.Many2one(
        'finance.account', '会计科目',
        ondelete='restrict',
        required=True,
        domain="[('account_type','=','normal')]")

    debit = fields.Float('借方金额', digits='Amount',
                         help='每条凭证行中只能记录借方金额或者贷方金额中的一个，\
                               一张凭证中所有的凭证行的借方余额，必须等于贷方余额。')
    credit = fields.Float('贷方金额', digits='Amount',
                          help='每条凭证行中只能记录借方金额或者贷方金额中的一个，\
                                一张凭证中所有的凭证行的借方余额，必须等于贷方余额。')
    partner_id = fields.Many2one(
        'partner', '往来单位', ondelete='restrict', help='凭证行的对应的往来单位')

    currency_amount = fields.Float('外币金额', digits='Amount')
    currency_id = fields.Many2one('res.currency', '外币币别', ondelete='restrict')
    rate_silent = fields.Float('汇率', digits=0)
    period_id = fields.Many2one(
        related='voucher_id.period_id', string='凭证期间', store=True)
    goods_qty = fields.Float('数量',
                             digits='Quantity')
    goods_id = fields.Many2one('goods', '商品', ondelete='restrict')
    auxiliary_id = fields.Many2one(
        'auxiliary.financing', '辅助核算', help='辅助核算是对账务处理的一种补充,即实现更广泛的账务处理,\
        以适应企业管理和决策的需要.辅助核算一般通过核算项目来实现', ondelete='restrict')
    date = fields.Date(compute='_compute_voucher_date',
                       store=True, string='凭证日期')
    state = fields.Selection(
        [('draft', '草稿'), ('done', '已确认'), ('cancel', '已作废')],
        compute='_compute_voucher_state',
        index=True,
        store=True, string='状态')
    init_obj = fields.Char('初始化对象', help='描述本条凭证行由哪个单证生成而来')
    company_id = fields.Many2one(
        'res.company',
        string='公司',
        change_default=True,
        default=lambda self: self.env.company)

    @api.depends('voucher_id.date')
    def _compute_voucher_date(self):
        for vl in self:
            vl.date = vl.voucher_id.date

    @api.depends('voucher_id.state')
    def _compute_voucher_state(self):
        for vl in self:
            vl.state = vl.voucher_id.state

    @api.onchange('account_id')
    def onchange_account_id(self):
        self.currency_id = self.account_id.currency_id
        self.rate_silent = self.account_id.currency_id.rate
        res = {
            'domain': {
                'partner_id': [('name', '=', False)],
                'goods_id': [('name', '=', False)],
                'auxiliary_id': [('name', '=', False)]}}
        if not self.account_id or not self.account_id.auxiliary_financing:
            return res
        if self.account_id.auxiliary_financing == 'customer':
            res['domain']['partner_id'] = [('c_category_id', '!=', False)]
        elif self.account_id.auxiliary_financing == 'supplier':
            res['domain']['partner_id'] = [('s_category_id', '!=', False)]
        elif self.account_id.auxiliary_financing == 'goods':
            res['domain']['goods_id'] = []
        else:
            res['domain']['auxiliary_id'] = [
                ('type', '=', self.account_id.auxiliary_financing)]
        return res

    def view_document(self):
        self.ensure_one()
        return {
            'name': '凭证',
            'view_mode': 'form',
            'res_model': 'voucher',
            'res_id': self.voucher_id.id,
            'type': 'ir.actions.act_window',
        }

    @api.constrains('account_id')
    def _check_account_id(self):
        for record in self:
            if record.account_id.account_type == 'view':
                raise UserError('只能往下级科目记账!')

    def check_restricted_account(self):
        prohibit_account_debit_ids = self.env['finance.account'].search(
            [('restricted_debit', '=', True)])
        prohibit_account_credit_ids = self.env['finance.account'].search(
            [('restricted_credit', '=', True)])

        account_ids = []

        account = self.account_id
        account_ids.append(account)
        while account.parent_id:
            account_ids.append(account.parent_id)
            account = account.parent_id

        inner_account_debit = [
            acc for acc in account_ids if acc in prohibit_account_debit_ids]

        inner_account_credit = [
            acc for acc in account_ids if acc in prohibit_account_credit_ids]

        if self.debit and not self.credit and inner_account_debit:
            raise UserError(
                '借方禁止科目: %s-%s \n\n 提示：%s ' % (
                    self.account_id.code,
                    self.account_id.name,
                    inner_account_debit[0].restricted_debit_msg))

        if not self.debit and self.credit and inner_account_credit:
            raise UserError(
                '贷方禁止科目: %s-%s \n\n 提示：%s ' % (
                    self.account_id.code,
                    self.account_id.name,
                    inner_account_credit[0].restrict_credit_msg))

    @api.model_create_multi
    def create(self, values):
        """
            Create a new record for a model VoucherLine
            @param values: provides a data for new record

            @return: returns a id of new record
        """

        result = super(VoucherLine, self).create(values)

        if not self.env.context.get('entry_manual', False):
            return result

        for r in result:
            r.check_restricted_account()

        return result

    def write(self, values):
        """
            Update all record(s) in recordset, with new value comes as {values}
            return True on success, False otherwise

            @param values: dict of new values to be set

            @return: True on success, False otherwise
        """

        result = super(VoucherLine, self).write(values)

        if not self.env.context.get('entry_manual', False):
            return result

        for record in self:
            record.check_restricted_account()

        return result


class DocumentWord(models.Model):
    '''凭证字'''
    _name = 'document.word'
    _description = '凭证字'

    name = fields.Char('凭证字')
    print_title = fields.Char('打印标题', help='凭证在打印时的显示的标题')
    company_id = fields.Many2one(
        'res.company',
        string='公司',
        change_default=True,
        default=lambda self: self.env.company)


class ChangeVoucherName(models.Model):
    ''' 修改凭证编号 '''
    _name = 'change.voucher.name'
    _description = '月末凭证变更记录'

    period_id = fields.Many2one('finance.period', '会计期间')
    before_voucher_name = fields.Char('以前凭证号')
    after_voucher_name = fields.Char('更新后凭证号')
    company_id = fields.Many2one(
        'res.company',
        string='公司',
        change_default=True,
        default=lambda self: self.env.company)
