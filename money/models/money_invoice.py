# Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo import fields, models, api


class MoneyInvoice(models.Model):
    _name = 'money.invoice'
    _description = '结算单'
    _order = 'date DESC'

    @api.model
    def _get_category_id(self):
        cate_type = self.env.context.get('type')
        if cate_type:
            return self.env['core.category'].search(
                [('type', '=', cate_type)])[0]
        return False

    def name_get(self):
        '''在many2one字段里有order则显示单号否则显示名称_票号'''
        res = []

        for invoice in self:
            if self.env.context.get('order'):
                res.append((invoice.id, invoice.name))
            else:
                res.append(
                    (invoice.id, invoice.bill_number
                     and invoice.bill_number or invoice.name))
        return res

    @api.depends('date_due', 'to_reconcile')
    def compute_overdue(self):
        """
        计算逾期天数： 当前日期 - 到期日，< 0则显示为0；如果逾期金额为0则逾期天数也为0
        计算逾期金额： 逾期时等于未核销金额，否则为0
        :return: 逾期天数
        """
        for s in self:
            # 只计算未核销的
            s.overdue_days = 0
            s.overdue_amount = 0
            if s.to_reconcile and s.state == 'done':
                d1 = fields.Date.context_today(s)
                d2 = s.date_due or d1
                day = (d1 - d2).days
                if day > 0:
                    s.overdue_days = day
                    s.overdue_amount = s.to_reconcile

    @api.depends('reconciled')
    def _get_sell_amount_state(self):
        for mi in self:
            if mi.reconciled:
                mi.get_amount_date = mi.write_date

    state = fields.Selection([
        ('draft', '草稿'),
        ('done', '完成')
    ], string='状态',
        default='draft', copy=False, index=True,
        help='结算单状态标识，新建时状态为草稿;确认后状态为完成')
    partner_id = fields.Many2one('partner', string='往来单位',
                                 required=True,
                                 ondelete='restrict',
                                 help='该单据对应的业务伙伴')
    name = fields.Char(string='前置单据编号', copy=False,
                       readonly=True, required=True,
                       help='该结算单编号，取自生成结算单的采购入库单和销售入库单')
    category_id = fields.Many2one(
        'core.category',
        string='类别',
        domain="[('type', 'in', ('income','expense'))]",
        ondelete='restrict',
        default=_get_category_id,
        help='结算单类别：采购 或者 销售等')
    date = fields.Date(string='日期', required=True,
                       default=lambda self: fields.Date.context_today(self),
                       help='单据创建日期')
    amount = fields.Float(string='金额（含税）',
                          digits='Amount',
                          help='原始单据对应金额')
    reconciled = fields.Float(string='已核销金额', readonly=True,
                              digits='Amount',
                              help='原始单据已核销掉的金额')
    to_reconcile = fields.Float(string='未核销金额', readonly=True,
                                digits='Amount',
                                help='原始单据未核销掉的金额')
    tax_amount = fields.Float('税额',
                              digits='Amount',
                              help='对应税额')
    get_amount_date = fields.Date('最后收款日期', compute=_get_sell_amount_state,
                                  store=True, copy=False)

    auxiliary_id = fields.Many2one('auxiliary.financing', '辅助核算',
                                   help='辅助核算')
    pay_method = fields.Many2one('pay.method',
                                 string='付款方式',
                                 ondelete='restrict')
    date_due = fields.Date(string='到期日',
                           help='结算单的到期日')
    currency_id = fields.Many2one('res.currency', '外币币别',
                                  help='原始单据对应的外币币别')
    bill_number = fields.Char('纸质发票号',
                              help='纸质发票号')
    invoice_date = fields.Date('开票日期')
    is_init = fields.Boolean('是否初始化单')
    company_id = fields.Many2one(
        'res.company',
        string='公司',
        change_default=True,
        default=lambda self: self.env.company)
    overdue_days = fields.Float('逾期天数', readonly=True,
                                compute='compute_overdue',
                                help='当前日期 - 到期日')
    overdue_amount = fields.Float('逾期金额', readonly=True,
                                  compute='compute_overdue',
                                  help='超过到期日后仍未核销的金额')
    note = fields.Char('备注',
                       help='可填入到期日计算的依据')
    handwork = fields.Boolean('手工结算')

    def money_invoice_done(self):
        """
        结算单审核方法
        """
        for inv in self:
            if inv.state == 'done':
                raise UserError('请不要重复确认')
            inv.reconciled = 0.0
            inv.to_reconcile = inv.amount
            inv.state = 'done'
            if inv.pay_method:
                inv.date_due = inv.pay_method.get_due_date(inv.invoice_date)
            else:
                inv.date_due = inv.partner_id.pay_method.get_due_date(
                    inv.invoice_date)
            if inv.category_id.type == 'income':
                inv.partner_id.receivable += inv.amount
            if inv.category_id.type == 'expense':
                inv.partner_id.payable += inv.amount
            if inv.handwork:
                # 手工结算单开票日期
                inv.invoice_date = inv.date
            if inv.is_init:
                inv.bill_number = '期初余额'
                inv.invoice_date = inv.date
        return True

    def money_invoice_draft(self):
        """
        结算单反审核方法
        :return:
        """
        for inv in self:
            if inv.state == 'draft':
                raise UserError('请不要重复撤销 %s' % self._description)
            if inv.reconciled != 0.0:
                raise UserError('已核销的结算单不允许撤销')
            # 查找发票相关的收款单
            source_line = self.env['source.order.line'].search(
                        [('name', '=', inv.id)])
            for line in source_line:
                ref_name = False
                if line.money_id:
                    ref_name = source_line.money_id.name
                if line.payable_reconcile_id:
                    ref_name = line.payable_reconcile_id.name
                if line.receivable_reconcile_id:
                    ref_name = line.receivable_reconcile_id.name
                if ref_name:
                    raise UserError('发票已被单据 %s 引用，无法撤销' % ref_name)
            inv.reconciled = 0.0
            inv.to_reconcile = 0.0
            inv.state = 'draft'
            if inv.category_id.type == 'income':
                inv.partner_id.receivable -= inv.amount
            if inv.category_id.type == 'expense':
                inv.partner_id.payable -= inv.amount

    @api.model
    def create(self, values):
        """
        创建结算单时，如果公司上的‘根据发票确认应收应付’字段没有勾上，则直接审核结算单，否则不审核。
        """
        new_id = super(MoneyInvoice, self).create(values)
        if not self.env.user.company_id.draft_invoice:
            new_id.money_invoice_done()
        return new_id

    def write(self, values):
        """
        当更新结算单到期日时，纸质发票号 相同的结算单到期日一起更新
        """
        if values.get('date_due') and self.bill_number \
                and not self.env.context.get('other_invoice_date_due'):
            invoices = self.search([('bill_number', '=', self.bill_number)])
            for inv in invoices:
                inv.with_context({'other_invoice_date_due': True}).write(
                    {'date_due': values.get('date_due')})
        return super(MoneyInvoice, self).write(values)

    def unlink(self):
        """
        只允许删除未确认的单据
        """
        for invoice in self:
            if invoice.name == '.' and invoice.reconciled == 0.0:
                self.money_invoice_draft()
                continue

        return super(MoneyInvoice, self).unlink()

    def find_source_order(self):
        '''
        查看原始单据，有以下情况：销售发货单、销售退货单、采购退货单、采购入库单、
        项目、委外加工单、核销单、采购订单、固定资产、固定资产变更以及期初应收应付。
        '''
        self.ensure_one()
        code = False
        res_models = [
            'reconcile.order',
        ]
        views = [
            'money.reconcile_order_form',
        ]
        # 判断当前数据库中否存在该 model
        if self.env.get('sell.delivery') is not None:
            res_models += ['sell.delivery']
            views += ['sell.sell_delivery_form']
        if self.env.get('outsource') is not None:
            res_models += ['outsource']
            views += ['warehouse.outsource_form']
        if self.env.get('buy.order') is not None:
            res_models += ['buy.order']
            views += ['buy.buy_order_form']
        if self.env.get('buy.receipt') is not None:
            res_models += ['buy.receipt']
            views += ['buy.buy_receipt_form']
        if self.env.get('project') is not None:
            res_models += ['project']
            views += ['task.project_form']
        if self.env.get('asset') is not None:
            res_models += ['asset']
            views += ['asset.asset_form']
        if self.env.get('cost.order') is not None:
            res_models += ['cost.order']
            views += ['account_cost.cost_order_form']
        if self.env.get('hr.expense') is not None:
            res_models += ['hr.expense']
            views += ['staff_expense.hr_expense_form']
        if '固定资产变更' in self.name:
            code = self.name.replace('固定资产变更', '')
        elif '固定资产' in self.name:
            code = self.name.replace('固定资产', '')
        domain = code and [('code', '=', code)] or [('name', '=', self.name)]

        for i in range(len(res_models)):
            # 若code存在说明 model为asset，view为固定资产form视图。
            res_model = code and 'asset' or res_models[i]
            view = code and self.env.ref(
                'asset.asset_form') or self.env.ref(views[i])
            res = self.env[res_model].search(domain)
            if res:  # 如果找到res_id,则退出for循环。
                break

        if not res:
            raise UserError('没有原始单据可供查看。')

        if res_model == 'sell.delivery' and res.is_return:
            view = self.env.ref('sell.sell_return_form')
        elif res_model == 'buy.receipt' and res.is_return:
            view = self.env.ref('buy.buy_return_form')
        return {
            'view_mode': 'form',
            'view_id': False,
            'views': [(view.id, 'form')],
            'res_model': res_model,
            'type': 'ir.actions.act_window',
            'res_id': res.id,
        }
