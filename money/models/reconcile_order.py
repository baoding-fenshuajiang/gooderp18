# Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError

from odoo import fields, models, api
from odoo.tools import float_compare, float_is_zero


class ReconcileOrder(models.Model):
    _name = 'reconcile.order'
    _description = '核销单'
    _inherit = ['mail.thread']

    TYPE_SELECTION = [
        ('adv_pay_to_get', '预收冲应收'),
        ('adv_get_to_pay', '预付冲应付'),
        ('get_to_pay', '应收冲应付'),
        ('get_to_get', '应收转应收'),
        ('pay_to_pay', '应付转应付'),
    ]

    state = fields.Selection([
        ('draft', '草稿'),
        ('done', '已确认'),
        ('cancel', '已作废'),
    ], string='状态', readonly=True,
        default='draft', copy=False, index=True,
        tracking=True,
        help='核销单状态标识，新建时状态为草稿;确认后状态为已确认')
    partner_id = fields.Many2one('partner', string='往来单位', required=True,
                                 ondelete='restrict',
                                 readonly="state!='draft'",
                                 help='该单据对应的业务伙伴，与业务类型一起带出待核销的明细行')
    to_partner_id = fields.Many2one('partner', string='转入往来单位',
                                    ondelete='restrict',
                                    readonly="state!='draft'",
                                    help='应收转应收、应付转应付时对应的转入业务伙伴，'
                                    '订单确认时会影响该业务伙伴的应收/应付')
    advance_payment_ids = fields.One2many(
        'advance.payment', 'pay_reconcile_id',
        string='预收/付款单行',
        readonly="state!='draft'",
        help='业务伙伴有预收/付款单，自动带出，用来与应收/应付款单核销')
    receivable_source_ids = fields.One2many(
        'source.order.line', 'receivable_reconcile_id',
        string='应收结算单行',
        readonly="state!='draft'",
        help='业务伙伴有应收结算单，自动带出，待与预收款单核销')
    payable_source_ids = fields.One2many(
        'source.order.line', 'payable_reconcile_id',
        string='应付结算单行',
        readonly="state!='draft'",
        help='业务伙伴有应付结算单，自动带出，待与预付款单核销')
    business_type = fields.Selection(TYPE_SELECTION, string='业务类型',
                                     readonly="state!='draft'",
                                     help='类型：预收冲应收,预付冲应付,应收冲应付,应收转应收,应付转应付'
                                     )
    name = fields.Char(string='单据编号', copy=False, readonly=True,
                       help='单据编号，创建时会自动生成')
    date = fields.Date(string='单据日期',
                       default=lambda self: fields.Date.context_today(self),
                       readonly="state!='draft'",
                       help='单据创建日期')
    note = fields.Text(string='备注',
                       help='可以为该单据添加一些需要的标识信息')
    company_id = fields.Many2one(
        'res.company',
        string='公司',
        change_default=True,
        default=lambda self: self.env.company)

    @api.model
    def create(self, values):
        # 创建时查找该业务伙伴是否存在 未审核 状态下的核销单
        if values.get('partner_id'):
            orders = self.env['reconcile.order'].search([
                ('partner_id', '=', values.get('partner_id')),
                ('state', '=', 'draft'),
                ('id', '!=', self.id),
                ('business_type', '=', values.get('business_type'))])
            if orders:
                raise UserError(
                    '业务伙伴(%s)、业务类型(%s)存在未审核的核销单，请先审核' % (
                                orders.partner_id.name,
                                dict(self.fields_get(
                                    allfields=['business_type']
                                    )['business_type']['selection']
                                )[orders.business_type]))
        return super(ReconcileOrder, self).create(values)

    def write(self, values):
        # 写入时查找该业务伙伴是否存在 未审核 状态下的核销单
        orders = self.env['reconcile.order'].search([
            ('partner_id', '=',
                (values.get('partner_id') or self.partner_id.id)),
            ('state', '=', 'draft'),
            ('id', '!=', self.id),
            ('business_type', '=',
                (values.get('business_type') or self.business_type))])
        if orders:
            raise UserError(
                '业务伙伴(%s)、业务类型(%s)存在未审核的核销单，请先审核' % (
                    orders.partner_id.name,
                    dict(self.fields_get(
                        allfields=['business_type'])['business_type']
                        ['selection'])[orders.business_type]))
        return super(ReconcileOrder, self).write(values)

    def _get_money_order(self, way='get'):
        """
        搜索到满足条件的预收/付款单，为one2many字段赋值构造列表
        :param way: 收/付款单的type
        :return: list
        """
        money_orders = self.env['money.order'].search(
            [('partner_id', '=', self.partner_id.id),
             ('type', '=', way),
             ('state', '=', 'done'),
             ('to_reconcile', '!=', 0)])
        result = []
        for order in money_orders:
            result.append((0, 0, {
                'name': order.id,
                'amount': order.amount,
                'date': order.date,
                'reconciled': order.reconciled,
                'to_reconcile': order.to_reconcile,
                'this_reconcile': order.to_reconcile,
            }))
        return result

    def _get_money_invoice(self, way='income'):
        """
        搜索到满足条件的money.invoice记录并且取出invoice对象 构造出one2many的

        :param way: money.invoice 中的category_id 的type
        :return:
        """
        MoneyInvoice = self.env['money.invoice'].search([
            ('category_id.type', '=', way),
            ('partner_id', '=', self.partner_id.id),
            ('state', '=', 'done'),
            ('to_reconcile', '!=', 0)])
        result = []
        for invoice in MoneyInvoice:
            result.append((0, 0, {
                'name': invoice.id,
                'category_id': invoice.category_id.id,
                'amount': invoice.amount,
                'date': invoice.date,
                'reconciled': invoice.reconciled,
                'to_reconcile': invoice.to_reconcile,
                'date_due': invoice.date_due,
                'this_reconcile': invoice.to_reconcile,
            }))
        return result

    @api.onchange('partner_id', 'to_partner_id', 'business_type')
    def onchange_partner_id(self):
        """
        onchange 类型字段 当改变 客户或者转入往来单位  业务类型 自动生成 对应的
        核销单各种明细。
        :return:
        """
        if not self.partner_id or not self.business_type:
            return {}

        # 先清空之前填充的数据
        self.advance_payment_ids = None
        self.receivable_source_ids = None
        self.payable_source_ids = None

        if self.business_type == 'adv_pay_to_get':  # 预收冲应收
            self.advance_payment_ids = self._get_money_order('get')
            self.receivable_source_ids = self._get_money_invoice('income')

        if self.business_type == 'adv_get_to_pay':  # 预付冲应付
            self.advance_payment_ids = self._get_money_order('pay')
            self.payable_source_ids = self._get_money_invoice('expense')

        if self.business_type == 'get_to_pay':  # 应收冲应付
            self.receivable_source_ids = self._get_money_invoice('income')
            self.payable_source_ids = self._get_money_invoice('expense')

        if self.business_type == 'get_to_get':  # 应收转应收
            self.receivable_source_ids = self._get_money_invoice('income')
            return {'domain':
                    {'to_partner_id': [('c_category_id', '!=', False)]}}

        if self.business_type == 'pay_to_pay':  # 应付转应付
            self.payable_source_ids = self._get_money_invoice('expense')
            return {'domain':
                    {'to_partner_id': [('s_category_id', '!=', False)]}}

    def _get_or_pay(self, line, business_type,
                    partner_id, to_partner_id, name):
        """
        核销单 核销时 对具体核销单行进行的操作
        :param line:
        :param business_type:
        :param partner_id:
        :param to_partner_id:
        :param name:
        :return:
        """
        decimal_amount = self.env.ref('core.decimal_amount')
        if float_compare(
                line.this_reconcile,
                line.to_reconcile,
                precision_digits=decimal_amount.digits) == 1:
            raise UserError('核销金额不能大于未核销金额。\n核销金额:%s 未核销金额:%s' %
                            (line.this_reconcile, line.to_reconcile))
        # 更新每一行的已核销余额、未核销余额
        line.name.to_reconcile -= line.this_reconcile
        line.name.reconciled += line.this_reconcile

        # 应收转应收、应付转应付
        if business_type in ['get_to_get', 'pay_to_pay']:
            if not float_is_zero(line.this_reconcile, 2):
                # 转入业务伙伴往来增加
                self.env['money.invoice'].create({
                    'name': name,
                    'category_id': line.category_id.id,
                    'amount': line.this_reconcile,
                    'date': self.date,
                    'reconciled': 0,  # 已核销金额
                    'to_reconcile': line.this_reconcile,  # 未核销金额
                    'date_due': line.date_due,
                    'partner_id': to_partner_id.id,
                })
                # 转出业务伙伴往来减少
                to_invoice_id = self.env['money.invoice'].create({
                    'name': name,
                    'category_id': line.category_id.id,
                    'amount': -line.this_reconcile,
                    'date': self.date,
                    'date_due': line.date_due,
                    'partner_id': partner_id.id,
                })
                # 核销 转出业务伙伴 的转出金额
                to_invoice_id.to_reconcile = 0
                to_invoice_id.reconciled = -line.this_reconcile

        # 应收冲应付，应收行、应付行分别生成负的结算单，并且核销
        if business_type in ['get_to_pay']:
            if not float_is_zero(line.this_reconcile, 2):
                invoice_id = self.env['money.invoice'].create({
                    'name': name,
                    'category_id': line.category_id.id,
                    'amount': -line.this_reconcile,
                    'date': self.date,
                    'date_due': line.date_due,
                    'partner_id': partner_id.id,
                })
                # 核销 业务伙伴 的本次核销金额
                invoice_id.to_reconcile = 0
                invoice_id.reconciled = -line.this_reconcile
        return True

    def reconcile_order_done(self):
        '''核销单的审核按钮'''
        # 核销金额不能大于未核销金额
        for order in self:
            if order.state == 'done':
                raise UserError('核销单%s已确认，不能再次确认。' % order.name)
            order_reconcile, invoice_reconcile = 0, 0
            if order.business_type in ['get_to_get', 'pay_to_pay'] \
                    and order.partner_id == order.to_partner_id:
                raise UserError(
                    '业务伙伴和转入往来单位不能相同。\n业务伙伴:%s 转入往来单位:%s'
                    % (order.partner_id.name, order.to_partner_id.name))

            # 核销预收预付
            for line in order.advance_payment_ids:
                order_reconcile += line.this_reconcile
                decimal_amount = self.env.ref('core.decimal_amount')
                if float_compare(
                        line.this_reconcile,
                        line.to_reconcile,
                        precision_digits=decimal_amount.digits) == 1:
                    raise UserError('核销金额不能大于未核销金额。\n核销金额:%s 未核销金额:%s' % (
                        line.this_reconcile, line.to_reconcile))

                # 更新每一行的已核销余额、未核销余额
                line.name.to_reconcile -= line.this_reconcile
                line.name.reconciled += line.this_reconcile

            for line in order.receivable_source_ids:
                invoice_reconcile += line.this_reconcile
                self._get_or_pay(line, order.business_type,
                                 order.partner_id,
                                 order.to_partner_id, order.name)
            for line in order.payable_source_ids:
                if self.business_type == 'adv_get_to_pay':
                    invoice_reconcile += line.this_reconcile
                else:
                    order_reconcile += line.this_reconcile
                self._get_or_pay(line, order.business_type,
                                 order.partner_id,
                                 order.to_partner_id, order.name)

            # 核销金额必须相同
            if order.business_type in ['adv_pay_to_get',
                                       'adv_get_to_pay', 'get_to_pay']:
                decimal_amount = self.env.ref('core.decimal_amount')
                if float_compare(
                        order_reconcile,
                        invoice_reconcile,
                        precision_digits=decimal_amount.digits) != 0:
                    raise UserError('核销金额必须相同, %s 不等于 %s'
                                    % (order_reconcile, invoice_reconcile))

            order.state = 'done'
        return True

    def _get_or_pay_cancel(self, line, business_type, name):
        """
        反核销时 对具体核销单行进行的操作
        """
        # 每一行的已核销金额减少、未核销金额增加
        line.name.to_reconcile += line.this_reconcile
        line.name.reconciled -= line.this_reconcile

        # 应收转应收、应付转应付、应收冲应付，找到生成的结算单反审核并删除
        if business_type in ['get_to_get', 'pay_to_pay', 'get_to_pay']:
            invoices = self.env['money.invoice'].search([('name', '=', name)])
            for inv in invoices:
                if inv.state == 'done':
                    inv.reconciled = 0.0
                    inv.money_invoice_draft()
                inv.unlink()
        return True

    def reconcile_order_draft(self):
        ''' 核销单的反审核按钮 '''
        for order in self:
            if order.state == 'draft':
                raise UserError('核销单%s已撤销，不能再次撤销。' % order.name)
            order_reconcile, invoice_reconcile = 0, 0
            if order.business_type in ['get_to_get', 'pay_to_pay'] \
                    and order.partner_id == order.to_partner_id:
                raise UserError(
                    '业务伙伴和转入往来单位不能相同。\n业务伙伴:%s 转入往来单位:%s'
                    % (order.partner_id.name, order.to_partner_id.name))

            # 反核销预收预付
            for line in order.advance_payment_ids:
                order_reconcile += line.this_reconcile
                # 每一行的已核销余额减少、未核销余额增加
                line.name.to_reconcile += line.this_reconcile
                line.name.reconciled -= line.this_reconcile
            # 反核销应收行
            for line in order.receivable_source_ids:
                invoice_reconcile += line.this_reconcile
                self._get_or_pay_cancel(line, order.business_type, order.name)
            # 反核销应付行
            for line in order.payable_source_ids:
                if order.business_type == 'adv_get_to_pay':
                    invoice_reconcile += line.this_reconcile
                else:
                    order_reconcile += line.this_reconcile
                self._get_or_pay_cancel(line, order.business_type, order.name)

            # 反核销时，金额必须相同
            if self.business_type in [
                    'adv_pay_to_get', 'adv_get_to_pay', 'get_to_pay']:
                decimal_amount = self.env.ref('core.decimal_amount')
                if float_compare(
                        order_reconcile,
                        invoice_reconcile,
                        precision_digits=decimal_amount.digits) != 0:
                    raise UserError('反核销时，金额必须相同, %s 不等于 %s'
                                    % (order_reconcile, invoice_reconcile))

            order.state = 'draft'
        return True


class SourceOrderLine(models.Model):
    _name = 'source.order.line'
    _description = '待核销行'

    money_id = fields.Many2one('money.order', string='收付款单',
                               ondelete='cascade',
                               help='待核销行对应的收付款单')  # 收付款单上的待核销行
    receivable_reconcile_id = fields.Many2one(
        'reconcile.order',
        string='应收核销单', ondelete='cascade',
        help='核销单上的应收结算单明细')  # 核销单上的应收结算单明细
    payable_reconcile_id = fields.Many2one('reconcile.order',
                                           string='应付核销单', ondelete='cascade',
                                           help='核销单上的应付结算单明细')  # 核销单上的应付结算单明细
    name = fields.Many2one('money.invoice', string='发票号',
                           copy=False, required=True,
                           ondelete='cascade',
                           help='待核销行对应的结算单')
    category_id = fields.Many2one('core.category', string='类别',
                                  required=True, ondelete='restrict',
                                  help='待核销行类别：采购 或者 销售等')
    date = fields.Date(string='单据日期',
                       help='单据创建日期')
    amount = fields.Float(string='单据金额',
                          digits='Amount',
                          help='待核销行对应金额')
    reconciled = fields.Float(string='已核销金额',
                              digits='Amount',
                              help='待核销行已核销掉的金额')
    to_reconcile = fields.Float(string='未核销金额',
                                digits='Amount',
                                help='待核销行未核销掉的金额')
    this_reconcile = fields.Float(string='本次核销金额',
                                  digits='Amount',
                                  help='本次要核销掉的金额')
    invoice_date = fields.Date(string='开票日期',
                               help='待核销行开票日期',
                               related='name.invoice_date')
    date_due = fields.Date(string='到期日',
                           help='待核销行的到期日')
    company_id = fields.Many2one(
        'res.company',
        string='公司',
        change_default=True,
        default=lambda self: self.env.company)


class AdvancePayment(models.Model):
    _name = 'advance.payment'
    _description = '核销单预收付款行'

    pay_reconcile_id = fields.Many2one('reconcile.order',
                                       string='核销单', ondelete='cascade',
                                       help='核销单预收付款行对应的核销单')
    name = fields.Many2one('money.order', string='预收/付款单',
                           copy=False, required=True, ondelete='cascade',
                           help='核销单预收/付款行对应的预收/付款单')
    note = fields.Text('备注', related='name.note')
    date = fields.Date(string='单据日期',
                       help='单据创建日期')
    amount = fields.Float(string='单据金额',
                          digits='Amount',
                          help='预收/付款单的预收/付金额')
    reconciled = fields.Float(string='已核销金额',
                              digits='Amount',
                              help='已核销的预收/预付款金额')
    to_reconcile = fields.Float(string='未核销金额',
                                digits='Amount',
                                help='未核销的预收/预付款金额')
    this_reconcile = fields.Float(string='本次核销金额',
                                  digits='Amount',
                                  help='本次核销的预收/预付款金额')
    company_id = fields.Many2one(
        'res.company',
        string='公司',
        change_default=True,
        default=lambda self: self.env.company)
