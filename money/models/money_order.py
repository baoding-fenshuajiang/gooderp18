# Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError, ValidationError

from odoo import fields, models, api
from odoo.tools import float_compare, float_is_zero


class MoneyOrder(models.Model):
    _name = 'money.order'
    _description = "收付款单"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    TYPE_SELECTION = [
        ('pay', '付款'),
        ('get', '收款'),
    ]

    @api.model
    def create(self, values):
        # 创建单据时，根据订单类型的不同，生成不同的单据编号
        if self.env.context.get('type') == 'pay':
            values.update(
                {'name': self.env['ir.sequence'].next_by_code('pay.order')})
        else:
            values.update(
                {'name': self.env['ir.sequence'].next_by_code('get.order')})

        # 创建时查找该业务伙伴是否存在 未审核 状态下的收付款单
        orders = self.env['money.order'].search([
            ('partner_id', '=', values.get('partner_id')),
            ('state', '=', 'draft'),
            ('source_ids', '!=', False),
            ('id', '!=', self.id)])
        if values.get('source_ids') and orders:
            raise UserError('该业务伙伴存在未确认的收/付款单，请先确认')

        return super(MoneyOrder, self).create(values)

    def write(self, values):
        # 修改时查找该业务伙伴是否存在 未审核 状态下的收付款单
        if values.get('partner_id'):
            orders = self.env['money.order'].search([
                ('partner_id', '=', values.get('partner_id')),
                ('state', '=', 'draft'),
                ('id', '!=', self.id)])
            if orders:
                raise UserError('业务伙伴(%s)存在未审核的收/付款单，请先审核' %
                                orders.partner_id.name)

        return super(MoneyOrder, self).write(values)

    @api.depends('discount_amount',
                 'line_ids.amount',
                 'source_ids.this_reconcile')
    def _compute_advance_payment(self):
        """
        计算字段advance_payment（本次预收）
        """
        for mo in self:
            amount, this_reconcile = 0.0, 0.0
            for line in mo.line_ids:
                amount += line.amount
            for line in mo.source_ids:
                this_reconcile += line.this_reconcile

            if mo.type == 'get':
                mo.advance_payment = \
                    amount - this_reconcile + mo.discount_amount
            else:
                mo.advance_payment = \
                    amount - this_reconcile - mo.discount_amount

            mo.amount = amount

    @api.depends('partner_id', 'type')
    def _compute_currency_id(self):
        """
        取出币别
        :return:
        """
        for mo in self:
            partner_currency_id = (mo.type == 'get') \
                and mo.partner_id.c_category_id.account_id.currency_id.id \
                or mo.partner_id.s_category_id.account_id.currency_id.id
            mo.currency_id = \
                partner_currency_id or mo.env.user.company_id.currency_id.id

    state = fields.Selection([
        ('draft', '草稿'),
        ('done', '已完成'),
        ('cancel', '已作废'),
    ], string='状态', readonly=True, default='draft', copy=False, index=True,
        help='收/付款单状态标识，新建时状态为草稿;确认后状态为已完成')
    partner_id = fields.Many2one('partner', string='往来单位', required=True,
                                 ondelete='restrict',
                                 readonly="state!='draft'",
                                 help='该单据对应的业务伙伴，单据确认时会影响他的应收应付余额')
    date = fields.Date(string='单据日期',
                       default=lambda self: fields.Date.context_today(self),
                       readonly="state!='draft'",
                       help='单据创建日期')
    name = fields.Char(string='单据编号', copy=False, readonly=True,
                       help='单据编号，创建时会根据类型自动生成')
    note = fields.Text(string='备注', help='可以为该单据添加一些需要的标识信息')
    currency_id = fields.Many2one(
        'res.currency',
        '币别',
        compute='_compute_currency_id',
        store=True,
        readonly=True,
        tracking=True,
        help='业务伙伴的类别科目上对应的外币币别')
    discount_amount = fields.Float(string='我方承担费用',
                                   readonly="state!='draft'",
                                   digits='Amount',
                                   help='收/付款时发生的银行手续费或给业务伙伴的现金折扣。')
    discount_account_id = fields.Many2one(
        'finance.account', '费用科目',
        domain="[('account_type','=','normal')]",
        readonly="state!='draft'",
        help='收/付款单确认生成凭证时，手续费或折扣对应的科目')
    line_ids = fields.One2many('money.order.line', 'money_id',
                               string='收/付款单行',
                               readonly="state!='draft'",
                               help='收/付款单明细行')
    source_ids = fields.One2many('source.order.line', 'money_id',
                                 string='待核销行',
                                 readonly="state!='draft'",
                                 help='收/付款单待核销行')
    type = fields.Selection(TYPE_SELECTION, string='类型',
                            default=lambda self: self.env.context.get('type'),
                            help='类型：收款单 或者 付款单')
    amount = fields.Float(string='总金额', compute='_compute_advance_payment',
                          digits='Amount',
                          store=True, readonly=True,
                          help='收/付款单行金额总和')
    advance_payment = fields.Float(
        string='本次预付',
        compute='_compute_advance_payment',
        digits='Amount',
        store=True, readonly=True,
        help='根据收/付款单行金额总和，原始单据行金额总和及折扣额计算得来的预收/预付款，值>=0')
    to_reconcile = fields.Float(string='未核销金额',
                                digits='Amount',
                                help='未核销的预收/预付款金额')
    reconciled = fields.Float(string='已核销金额',
                              digits='Amount',
                              help='已核销的预收/预付款金额')
    origin_name = fields.Char('原始单据编号',
                              help='原始单据编号')
    bank_name = fields.Char('开户行',
                            readonly="state!='draft'",
                            help='开户行取自业务伙伴，可修改')
    bank_num = fields.Char('银行账号',
                           readonly="state!='draft'",
                           help='银行账号取自业务伙伴，可修改')
    approve_uid = fields.Many2one('res.users', '确认人',
                                  copy=False, ondelete='restrict')
    approve_date = fields.Datetime('确认日期', copy=False)
    company_id = fields.Many2one(
        'res.company',
        string='公司',
        change_default=True,
        default=lambda self: self.env.company)
    voucher_id = fields.Many2one('voucher',
                                 '对应凭证',
                                 readonly=True,
                                 ondelete='restrict',
                                 copy=False,
                                 help='收/付款单确认时生成的对应凭证')

    def create_reconcile(self):
        self.ensure_one()
        if self.env['money.invoice'].search([
            ('partner_id', '=', self.partner_id.id),
            ('state', '=', 'done'),
            ('to_reconcile', '!=', 0),
        ], limit=1):
            if self.type == 'get':
                business_type = 'adv_pay_to_get'
            else:
                business_type = 'adv_get_to_pay'
            recon = self.env['reconcile.order'].create({
                'partner_id': self.partner_id.id,
                'business_type': business_type})
            recon.onchange_partner_id()
            action = {
                'name': '核销单',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'reconcile.order',
                'res_id': recon.id,
            }
            return action
        else:
            raise UserError('没有未核销结算单')

    def write_off_reset(self):
        """
        单据审核前重置计算单行上的本次核销金额
        :return:
        """
        self.ensure_one()
        if self.state != 'draft':
            raise ValueError('已确认的单据不能执行这个操作')
        for source in self.source_ids:
            source.this_reconcile = 0
        return True

    @api.onchange('date')
    def onchange_date(self):
        """
        当修改日期时，则根据context中的money的type对客户添加过滤，过滤出是供应商还是客户。
        （因为date有默认值所以这个过滤是默认触发的） 其实和date是否变化没有关系，页面加载就触发下面的逻辑
        :return:
        """
        if self.env.context.get('type') == 'get':
            return {'domain': {'partner_id': [('c_category_id', '!=', False)]}}
        else:
            return {'domain': {'partner_id': [('s_category_id', '!=', False)]}}

    def _get_source_line(self, invoice):
        """
        根据传入的invoice的对象取出对应的值 构造出 source_line的一个dict 包含source line的主要参数
        :param invoice: money_invoice对象
        :return: dict
        """

        return {
            'name': invoice.id,
            'category_id': invoice.category_id.id,
            'amount': invoice.amount,
            'date': invoice.date,
            'reconciled': invoice.reconciled,
            'to_reconcile': invoice.to_reconcile,
            'this_reconcile': invoice.to_reconcile,
            'date_due': invoice.date_due,
        }

    def _get_invoice_search_list(self):
        """
        构造出 invoice 搜索的domain
        :return:
        """
        invoice_search_list = [('partner_id', '=', self.partner_id.id),
                               ('to_reconcile', '!=', 0),
                               ('state', '=', 'done')]
        if self.env.context.get('type') == 'get':
            invoice_search_list.append(('category_id.type', '=', 'income'))
        else:  # type = 'pay':
            invoice_search_list.append(('category_id.type', '=', 'expense'))

        return invoice_search_list

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """
        对partner修改的监控当 partner 修改时，
        就对 页面相对应的字段进行修改（bank_name，bank_num，source_ids）
        """
        if not self.partner_id:
            return {}

        self.source_ids = False
        source_lines = []
        self.bank_name = self.partner_id.bank_name
        self.bank_num = self.partner_id.bank_num

        for invoice in self.env['money.invoice'].search(
                self._get_invoice_search_list()):
            source_lines.append((0, 0, self._get_source_line(invoice)))
        self.source_ids = source_lines

    def money_order_done(self):
        '''对收付款单的审核按钮'''
        for order in self:
            if order.state == 'done':
                raise UserError('请不要重复确认')
            if order.type == 'pay' and \
                    not order.partner_id.s_category_id.account_id:
                raise UserError('请输入供应商类别(%s)上的科目' %
                                order.partner_id.s_category_id.name)
            if order.type == 'get' and \
                    not order.partner_id.c_category_id.account_id:
                raise UserError('请输入客户类别(%s)上的科目' %
                                order.partner_id.c_category_id.name)
            if order.advance_payment < 0 and order.source_ids:
                raise UserError('本次核销金额不能大于付款金额。\n差额: %s' %
                                (order.advance_payment))

            total = 0
            for line in order.line_ids:
                rate_silent = self.env['res.currency'].get_rate_silent(
                    order.date, line.currency_id.id)
                if order.type == 'pay':  # 付款账号余额减少, 退款账号余额增加
                    decimal_amount = self.env.ref('core.decimal_amount')
                    balance = (
                        line.currency_id
                        != self.env.user.company_id.currency_id
                        and line.bank_id.currency_amount
                        or line.bank_id.balance)
                    if float_compare(
                            balance, line.amount,
                            precision_digits=decimal_amount.digits) == -1:
                        raise UserError('账户余额不足。\n账户余额:%s 付款行金额:%s' %
                                        (balance, line.amount))
                    if (line.currency_id
                            != self.env.user.company_id.currency_id):  # 外币
                        line.bank_id.currency_amount -= line.amount
                        line.bank_id.balance -= line.amount * rate_silent
                    else:
                        line.bank_id.balance -= line.amount
                else:  # 收款账号余额增加, 退款账号余额减少
                    if (line.currency_id
                            != self.env.user.company_id.currency_id):    # 外币
                        line.bank_id.currency_amount += line.amount
                        line.bank_id.balance += line.amount * rate_silent
                    else:
                        line.bank_id.balance += line.amount
                total += line.amount

            if order.type == 'pay':
                order.partner_id.payable -= total - order.discount_amount
            else:
                order.partner_id.receivable -= total + order.discount_amount

            # 更新结算单的未核销金额、已核销金额
            for source in order.source_ids:
                decimal_amount = self.env.ref('core.decimal_amount')
                if float_compare(
                        source.this_reconcile,
                        abs(source.to_reconcile),
                        precision_digits=decimal_amount.digits) == 1:
                    raise UserError(
                        '本次核销金额不能大于未核销金额。\n 核销金额:%s 未核销金额:%s'
                        % (abs(source.to_reconcile), source.this_reconcile))

                source.name.to_reconcile -= source.this_reconcile
                source.name.reconciled += source.this_reconcile

                if source.this_reconcile == 0:  # 如果核销行的本次付款金额为0，删除
                    source.unlink()

            # 生成凭证并审核
            if order.type == 'get':
                voucher = order.create_money_order_get_voucher(
                    order.line_ids, order.source_ids, order.partner_id,
                    order.name, order.note or '')
            else:
                voucher = order.create_money_order_pay_voucher(
                    order.line_ids, order.source_ids, order.partner_id,
                    order.name, order.note or '')
            voucher.voucher_done()

            return order.write({
                'to_reconcile': order.advance_payment,
                'reconciled': order.amount - order.advance_payment,
                'voucher_id': voucher.id,
                'approve_uid': self.env.uid,
                'approve_date': fields.Datetime.now(self),
                'state': 'done',
            })

    def money_order_draft(self):
        """
        收付款单反审核方法
        """
        for order in self:
            if order.state == 'draft':
                raise UserError('请不要重复撤销 %s' % self._description)

            # 收/付款单 存在已审核金额不为0的核销单
            total_current_reconciled = order.amount - order.advance_payment
            decimal_amount = self.env.ref('core.decimal_amount')
            if float_compare(order.reconciled,
                             total_current_reconciled,
                             precision_digits=decimal_amount.digits) != 0:
                raise UserError('单据已核销金额不为0，不能反审核！请检查核销单!')

            total = 0
            for line in order.line_ids:
                rate_silent = self.env['res.currency'].get_rate_silent(
                    order.date, line.currency_id.id)
                if order.type == 'pay':  # 反审核：付款账号余额增加
                    if (line.currency_id
                            != self.env.user.company_id.currency_id):  # 外币
                        line.bank_id.currency_amount += line.amount
                        line.bank_id.balance += line.amount * rate_silent
                    else:
                        line.bank_id.balance += line.amount
                else:  # 反审核：收款账号余额减少
                    balance = (
                        line.currency_id
                        != self.env.user.company_id.currency_id
                        and line.bank_id.currency_amount
                        or line.bank_id.balance)
                    decimal_amount = self.env.ref('core.decimal_amount')
                    if float_compare(
                            balance,
                            line.amount,
                            precision_digits=decimal_amount.digits) == -1:
                        raise UserError('账户余额不足。\n 账户余额:%s 收款行金额:%s' %
                                        (balance, line.amount))
                    if (line.currency_id
                            != self.env.user.company_id.currency_id):  # 外币
                        line.bank_id.currency_amount -= line.amount
                        line.bank_id.balance -= line.amount * rate_silent
                    else:
                        line.bank_id.balance -= line.amount
                total += line.amount

            if order.type == 'pay':
                order.partner_id.payable += total - order.discount_amount
            else:
                order.partner_id.receivable += total + order.discount_amount

            for source in order.source_ids:
                source.name.to_reconcile += source.this_reconcile
                source.name.reconciled -= source.this_reconcile

            voucher = order.voucher_id
            order.write({
                'to_reconcile': 0,
                'reconciled': 0,
                'voucher_id': False,
                'approve_uid': False,
                'approve_date': False,
                'state': 'draft',
            })
            # 反审核凭证并删除
            if voucher.state == 'done':
                voucher.voucher_draft()
            voucher.unlink()
        return True

    def _prepare_vouch_line_data(self, line, name, account_id, debit, credit,
                                 voucher_id, partner_id, currency_id):
        rate_silent = currency_amount = 0
        if currency_id:
            rate_silent = self.env['res.currency'].get_rate_silent(
                self.date, currency_id)
            currency_amount = debit or credit
            debit = debit * (rate_silent or 1)
            credit = credit * (rate_silent or 1)
        return {
            'name': name,
            'account_id': account_id,
            'debit': debit,
            'credit': credit,
            'voucher_id': voucher_id,
            'partner_id': partner_id,
            'currency_id': currency_id,
            'currency_amount': currency_amount,
            'rate_silent': rate_silent or ''
        }

    def _create_voucher_line(self, line, name, account_id, debit, credit,
                             voucher_id, partner_id, currency_id):
        line_data = self._prepare_vouch_line_data(
            line, name, account_id, debit, credit,
            voucher_id, partner_id, currency_id)
        voucher_line = self.env['voucher.line'].create(line_data)
        return voucher_line

    def create_money_order_get_voucher(self, line_ids, source_ids,
                                       partner, name, note):
        """
        为收款单创建凭证
        :param line_ids: 收款单明细
        :param source_ids: 没用到
        :param partner: 客户
        :param name: 收款单名称
        :return: 创建的凭证
        """
        vouch_obj = self.env['voucher'].create(
            {'date': self.date, 'ref': '%s,%s' % (self._name, self.id)})
        # self.write({'voucher_id': vouch_obj.id})
        amount_all = 0.0
        line_data = False
        for line in line_ids:
            line_data = line
            if not line.bank_id.account_id:
                raise UserError('请配置%s的会计科目' % (line.bank_id.name))
            # 生成借方明细行
            if line.amount:       # 可能输入金额为0的收款单用于核销尾差
                self._create_voucher_line(line,
                                          "%s %s" % (name, note),
                                          line.bank_id.account_id.id,
                                          line.amount,
                                          0,
                                          vouch_obj.id,
                                          '',
                                          line.currency_id.id
                                          )

            amount_all += line.amount
        if self.discount_amount != 0:
            # 生成借方明细行
            self._create_voucher_line(
                False,
                "%s 现金折扣 %s" % (name, note),
                self.discount_account_id.id,
                self.discount_amount,
                0,
                vouch_obj.id,
                self.partner_id.id,
                line_data and line_data.currency_id.id or self.currency_id.id
            )

        if partner.c_category_id:
            partner_account_id = partner.c_category_id.account_id.id

        # 生成贷方明细行
        if amount_all + self.discount_amount:
            self._create_voucher_line(
                '',
                "%s %s" % (name, note),
                partner_account_id,
                0,
                amount_all + self.discount_amount,
                vouch_obj.id,
                self.partner_id.id,
                line_data and line.currency_id.id or self.currency_id.id
            )
        return vouch_obj

    def create_money_order_pay_voucher(self, line_ids, source_ids,
                                       partner, name, note):
        """
        为付款单创建凭证
        :param line_ids: 付款单明细
        :param source_ids: 没用到
        :param partner: 供应商
        :param name: 付款单名称
        :return: 创建的凭证
        """
        vouch_obj = self.env['voucher'].create(
            {'date': self.date, 'ref': '%s,%s' % (self._name, self.id)})
        # self.write({'voucher_id': vouch_obj.id})

        amount_all = 0.0
        line_data = False
        for line in line_ids:
            line_data = line
            if not line.bank_id.account_id:
                raise UserError('请配置%s的会计科目' % (line.bank_id.name))
            # 生成贷方明细行 credit
            if line.amount:   # 支持金额为0的付款用于核销尾差
                self._create_voucher_line(line,
                                          "%s %s" % (name, note),
                                          line.bank_id.account_id.id,
                                          0,
                                          line.amount,
                                          vouch_obj.id,
                                          '',
                                          line.currency_id.id
                                          )
            amount_all += line.amount
        partner_account_id = partner.s_category_id.account_id.id

        # 生成借方明细行 debit
        if amount_all - self.discount_amount:
            self._create_voucher_line(
                '',
                "%s %s" % (name, note),
                partner_account_id,
                amount_all - self.discount_amount,
                0,
                vouch_obj.id,
                self.partner_id.id,
                line_data and line.currency_id.id or self.currency_id.id
            )

        if self.discount_amount != 0:
            # 生成借方明细行 debit
            self._create_voucher_line(
                line_data and line_data or False,
                "%s 手续费 %s" % (name, note),
                self.discount_account_id.id,
                self.discount_amount,
                0,
                vouch_obj.id,
                self.partner_id.id,
                line_data and line.currency_id.id or self.currency_id.id
            )
        return vouch_obj


class MoneyOrderLine(models.Model):
    _name = 'money.order.line'
    _description = '收付款单明细'

    @api.depends('bank_id')
    def _compute_currency_id(self):
        """
        获取币别
        """
        for mol in self:
            mol.currency_id = mol.bank_id.account_id.currency_id.id \
                or mol.env.user.company_id.currency_id.id
            if mol.bank_id and mol.currency_id != mol.money_id.currency_id:
                raise ValidationError(
                    '结算帐户与业务伙伴币别不一致。\n 结算账户币别:%s 业务伙伴币别:%s'
                    % (mol.currency_id.name, mol.money_id.currency_id.name))

    money_id = fields.Many2one('money.order', string='收付款单',
                               ondelete='cascade',
                               help='订单行对应的收付款单')
    bank_id = fields.Many2one('bank.account', string='结算账户',
                              required=True, ondelete='restrict',
                              help='本次收款/付款所用的计算账户，确认收付款单会修改对应账户的金额')
    amount = fields.Float(string='金额',
                          digits='Amount',
                          help='本次结算金额')
    mode_id = fields.Many2one('settle.mode', string='结算方式',
                              ondelete='restrict',
                              help='结算方式：支票、信用卡等')
    currency_id = fields.Many2one(
        'res.currency', '币别',
        compute='_compute_currency_id',
        store=True, readonly=True,
        help='结算账户对应的外币币别')
    number = fields.Char(string='结算号',
                         help='本次结算号')
    note = fields.Char(string='备注',
                       help='可以为本次结算添加一些需要的标识信息')
    company_id = fields.Many2one(
        'res.company',
        string='公司',
        change_default=True,
        default=lambda self: self.env.company)
