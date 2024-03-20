# Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError

BALANCE_DIRECTIONS_TYPE = [
    ('in', '借'),
    ('out', '贷')]


class FinanceAccountType(models.Model):
    """ 会计要素
    """
    _name = 'finance.account.type'
    _description = '会计要素'

    _rec_name = 'name'
    _order = 'name ASC'

    name = fields.Char('名称', required="1")
    active = fields.Boolean(string='启用', default="True")
    costs_types = fields.Selection([
        ('assets', '资产'),
        ('debt', '负债'),
        ('equity', '所有者权益'),
        ('in', '收入类'),
        ('out', '费用类'),
        ('cost', '成本类'),
    ], '类型', required="1", help='用于会计报表的生成。')


class FinanceAccount(models.Model):
    '''科目'''
    _name = 'finance.account'
    _order = "code"
    _description = '会计科目'
    _parent_store = True

    @api.depends('parent_id')
    def _compute_level(self):
        for record in self:
            level = 1
            parent = record.parent_id
            while parent:
                level = level + 1
                parent = parent.parent_id

            record.level = level

    @api.depends('child_ids', 'voucher_line_ids', 'account_type')
    def compute_balance(self):
        """
        计算会计科目的当前余额
        :return:
        """
        for record in self:
            # 上级科目按下级科目汇总
            if record.account_type == 'view':
                lines = self.env['voucher.line'].search(
                    [('account_id', 'child_of', record.id),
                     ('voucher_id.state', '=', 'done')])
                record.debit = sum((line.debit) for line in lines)
                record.credit = sum((line.credit) for line in lines)
                record.balance = record.debit - record.credit

            # 下级科目按记账凭证计算
            else:
                record.debit = sum(record.voucher_line_ids.filtered(
                    lambda self: self.state == 'done').mapped('debit'))
                record.credit = sum(record.voucher_line_ids.filtered(
                    lambda self: self.state == 'done').mapped('credit'))
                record.balance = record.debit - record.credit

    def get_balance(self, period_id=False):
        ''' 科目当前或某期间的借方、贷方、差额 '''
        self.ensure_one()
        domain = []
        data = {}
        period = self.env['finance.period']
        if period_id:
            domain.append(('period_id', '=', period_id))

        if self.account_type == 'view':
            domain.extend([
                ('account_id', 'child_of', self.id),
                ('voucher_id.state', '=', 'done')])
            lines = self.env['voucher.line'].search(domain)

            debit = sum((line.debit) for line in lines)
            credit = sum((line.credit) for line in lines)
            balance = self.debit - self.credit

            data.update({'debit': debit, 'credit': credit, 'balance': balance})

        # 下级科目按记账凭证计算
        else:
            if period_id:
                period = self.env['finance.period'].browse(period_id)

            if period:
                debit = sum(self.voucher_line_ids.filtered(
                    lambda self: self.period_id == period
                    and self.state == 'done'
                    ).mapped('debit'))
                credit = sum(self.voucher_line_ids.filtered(
                    lambda self: self.period_id == period
                    and self.state == 'done'
                    ).mapped('credit'))
                balance = self.debit - self.credit
            else:
                debit = sum(self.voucher_line_ids.filtered(
                    lambda self: self.state == 'done').mapped('debit'))
                credit = sum(self.voucher_line_ids.filtered(
                    lambda self: self.state == 'done').mapped('credit'))
                balance = self.debit - self.credit

            data.update({'debit': debit, 'credit': credit, 'balance': balance})

        return data

    name = fields.Char('名称', required="1")
    code = fields.Char('编码', required="1")
    balance_directions = fields.Selection(
        BALANCE_DIRECTIONS_TYPE, '余额方向', required="1",
        help='根据科目的类型，判断余额方向是借方或者贷方！')
    auxiliary_financing = fields.Selection(
        [('customer', '客户'),
         ('supplier', '供应商'),
         ('member', '个人'),
         ('project', '项目'),
         ('department', '部门'),
         ('goods', '存货'),
         ],
        '辅助核算',
        help='辅助核算是对账务处理的一种补充,即实现更广泛的账务处理,\n\
            以适应企业管理和决策的需要.辅助核算一般通过核算项目来实现')
    costs_types = fields.Selection(related='user_type.costs_types')
    account_type = fields.Selection(
        string='科目类型',
        selection=[('view', 'View'), ('normal', 'Normal')],
        default='normal')
    user_type = fields.Many2one(
        string='会计要素',
        comodel_name='finance.account.type',
        ondelete='restrict',
        required=True,
        default=lambda s: s.env.get(
            'finance.account.type').search([], limit=1).id)
    parent_left = fields.Integer('Left Parent', index=1)
    parent_right = fields.Integer('Right Parent', index=1)
    parent_id = fields.Many2one(
        string='上级科目',
        comodel_name='finance.account',
        ondelete='restrict',
        domain="[('account_type','=','view')]")
    parent_path = fields.Char(index=True, unaccent=False)
    child_ids = fields.One2many(
        string='下级科目',
        comodel_name='finance.account',
        inverse_name='parent_id', )
    level = fields.Integer(string='科目级次', compute='_compute_level')
    currency_id = fields.Many2one('res.currency', '外币币别')
    exchange = fields.Boolean('是否期末调汇')
    active = fields.Boolean('启用', default=True)
    company_id = fields.Many2one(
        'res.company',
        string='公司',
        change_default=True,
        default=lambda self: self.env.company)
    voucher_line_ids = fields.One2many(
        string='Voucher Lines',
        comodel_name='voucher.line',
        inverse_name='account_id', )
    debit = fields.Float(
        string='借方',
        compute='compute_balance',
        store=False,
        digits='Amount')
    credit = fields.Float(
        string='贷方',
        compute='compute_balance',
        store=False,
        digits='Amount')
    balance = fields.Float('当前余额',
                           compute='compute_balance',
                           store=False,
                           digits='Amount',
                           help='科目的当前余额',
                           )
    restricted_debit = fields.Boolean(
        string='借方限制使用',
        help='手工凭证时， 借方限制使用'
    )
    restricted_debit_msg = fields.Char(
        string='借方限制提示消息',
    )
    restricted_credit = fields.Boolean(
        string='贷方限制使用',
        help='手工凭证时， 贷方限制使用'
    )
    restrict_credit_msg = fields.Char(
        string='贷方限制提示消息',
    )
    source = fields.Selection(
        string='创建来源',
        selection=[('init', '初始化'), ('manual', '手工创建')], default='manual'
    )

    _sql_constraints = [
        ('name_uniq', 'unique(name)', '科目名称必须唯一。'),
        ('code', 'unique(code)', '科目编码必须唯一。'),
    ]

    @api.depends('name', 'code')
    def name_get(self):
        """
        在其他model中用到account时在页面显示 code name balance如：2202 应付账款 当前余额（更有利于会计记账）
        :return:
        """
        result = []
        for line in self:
            account_name = line.code + ' ' + line.name
            if line.env.context.get('show_balance'):
                account_name += ' ' + str(line.balance)
            result.append((line.id, account_name))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        '''会计科目按名字和编号搜索'''
        args = args or []
        domain = []
        if name:
            res_id = self.search([('code', '=', name)]+args)
            if res_id:
                return res_id.name_get()
            domain = ['|', ('code', '=ilike', name + '%'),
                      ('name', operator, name)]
        accounts = self.search(domain + args, limit=limit)
        return accounts.name_get()

    def get_smallest_code_account(self):
        """
        取得最小的code对应的account对象
        :return: 最小的code 对应的对象
        """
        finance_account_row = self.search([], order='code')
        return finance_account_row and finance_account_row[0]

    def get_max_code_account(self):
        """
        取得最大的code对应的account对象
        :return: 最大的code 对应的对象
        """
        finance_account_row = self.search([], order='code desc')
        return finance_account_row and finance_account_row[0]

    def write(self, values):
        """
        限制科目修改条件
        """
        for record in self:
            if record.source == 'init' and record.env.context.get(
                    'modify_from_webclient', False):
                raise UserError('不能修改预设会计科目!')

            if record.voucher_line_ids and record.env.context.get(
                    'modify_from_webclient', False):
                raise UserError('不能修改有记账凭证的会计科目!')

        return super(FinanceAccount, self).write(values)

    def unlink(self):
        """
        限制科目删除条件
        """
        parent_ids = []
        for record in self:
            if record.parent_id not in parent_ids:
                parent_ids.append(record.parent_id)

            if record.source == 'init' and record.env.context.get(
                    'modify_from_webclient', False):
                raise UserError('不能删除预设会计科目!')

            if record.voucher_line_ids:
                raise UserError('不能删除有记账凭证的会计科目!')

            if len(record.child_ids) != 0:
                raise UserError('不能删除有下级科目的会计科目!')

            '''
此处 https://github.com/osbzr/gooderp_addons/
commit/a4c3f2725ba602854149001563002dcedaa89e3d
导致代码xml中删除数据时发生混乱，暂时拿掉
ir_record = self.env['ir.model.data'].search(
    [('model','=','finance.account'),('res_id','=', record.id)])
if ir_record:
    ir_record.res_id = record.parent_id.id
            '''

        result = super(FinanceAccount, self).unlink()

        # 如果 下级科目全删除了，则将 上级科目设置为 普通科目
        for parent_id in parent_ids:
            if len(parent_id.child_ids.ids) == 0:
                parent_id.with_context(
                    modify_from_webclient=False).account_type = 'normal'

        return result

    def button_add_child(self):
        self.ensure_one()

        view = self.env.ref('finance.view_wizard_account_add_child_form')

        return {
            'name': '增加下级科目',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'wizard.account.add.child',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': dict(
                self.env.context, active_id=self.id,
                active_ids=[self.id],
                modify_from_webclient=False),
        }


class WizardAccountAddChild(models.TransientModel):
    """ 向导，用于新增下级科目.

    """

    _name = 'wizard.account.add.child'
    _description = 'Wizard Account Add Child'

    parent_id = fields.Many2one(
        string='上级科目',
        comodel_name='finance.account',
        ondelete='set null',
    )
    parent_path = fields.Char(index=True)

    parent_name = fields.Char(
        string='上级科目名称',
        related='parent_id.name',
        readonly=True,
    )

    parent_code = fields.Char(
        string='上级科目编码',
        related='parent_id.code',
        readonly=True,
    )

    account_code = fields.Char(
        string='新增编码', required=True
    )

    currency_id = fields.Many2one(
        'res.currency', '外币币别')

    full_account_code = fields.Char(
        string='完整科目编码',
    )

    account_name = fields.Char(
        string='科目名称', required=True
    )

    account_type = fields.Selection(
        string='Account Type',
        related='parent_id.account_type'
    )

    has_journal_items = fields.Boolean(
        string='Has Journal Items',
    )

    @api.model
    def default_get(self, fields):
        if len(self.env.context.get('active_ids', list())) > 1:
            raise UserError("一次只能为一个科目增加下级科目!")

        account_id = self.env.context.get('active_id')
        account = self.env['finance.account'].browse(account_id)
        has_journal_items = False
        if account.voucher_line_ids:
            has_journal_items = True
        if account.level >= int(self.env['ir.default']._get(
                'finance.config.settings', 'defaul_account_hierarchy_level')):
            raise UserError(
                '选择的科目层级是%s级，已经是最低层级科目了，不能建立在它下面建立下级科目！'
                % account.level)

        res = super(WizardAccountAddChild, self).default_get(fields)

        res.update({
            'parent_id': account_id,
            'has_journal_items': has_journal_items
            })

        return res

    def create_account(self):
        self.ensure_one()
        account_type = self.parent_id.account_type
        new_account = False
        full_account_code = '%s%s' % (self.parent_code, self.account_code)
        if account_type == 'normal':
            # 挂账科目，需要对现有凭证进行科目转换
            # step1, 建新科目
            new_account = self.parent_id.copy(
                {
                    'code': full_account_code,
                    'name': self.account_name,
                    'account_type': 'normal',
                    'source': 'manual',
                    'currency_id': self.currency_id.id,
                    'parent_id': self.parent_id.id
                }
            )
            # step2, 将关联凭证改到新科目
            self.env['voucher.line'].search(
                [('account_id', '=', self.parent_id.id)]).write(
                    {'account_id': new_account.id})
            # step3, 老科目改为 视图
            self.parent_id.write({
                'account_type': 'view',
            })

        elif account_type == 'view':
            # 直接新增下级科目，无需转换科目
            new_account = self.parent_id.copy(
                {
                    'code': full_account_code,
                    'name': self.account_name,
                    'account_type': 'normal',
                    'source': 'manual',
                    'currency_id': self.currency_id.id,
                    'parent_id': self.parent_id.id
                }
            )

        if not new_account:  # pragma: no cover
            raise UserError('新科目创建失败！')

        view = self.env.ref('finance.finance_account_tree')

        return {
            'name': '科目',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'res_model': 'finance.account',
            'views': [(view.id, 'tree')],
            'view_id': view.id,
            'target': 'current',
            'context': dict(
                self.env.context,
                hide_button=False,
                modify_from_webclient=True)
        }

    @api.onchange('account_code')
    def _onchange_account_code(self):

        def is_number(chars):
            try:
                int(chars)
                return True
            except ValueError:
                return False

        if self.account_code and not is_number(self.account_code):
            self.account_code = '01'
            return {
                'warning': {
                    'title': '错误',
                    'message': '科目代码必须是数字'
                }
            }

        default_child_step = self.env['ir.default']._get(
            'finance.config.settings', 'defaul_child_step')
        if self.account_code:
            self.full_account_code = "%s%s" % (
                self.parent_code, self.account_code)

        if self.account_code and len(
                self.account_code) != int(default_child_step):
            self.account_code = '01'
            self.full_account_code = self.parent_code
            return {
                'warning': {
                    'title': '错误',
                    'message': '下级科目编码长度与"下级科目编码递增长度"规则不符合！'
                }
            }


class AuxiliaryFinancing(models.Model):
    '''辅助核算'''
    _name = 'auxiliary.financing'
    _description = '辅助核算'

    code = fields.Char('编码')
    name = fields.Char('名称')
    type = fields.Selection([
        ('member', '个人'),
        ('project', '项目'),
        ('department', '部门'),
    ], '分类', default=lambda self: self.env.context.get('type'))
    active = fields.Boolean('启用', default=True)
    company_id = fields.Many2one(
        'res.company',
        string='公司',
        change_default=True,
        default=lambda self: self.env.company)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', '辅助核算不能重名')
    ]


class ResCompany(models.Model):
    '''继承公司对象,添加字段'''
    _inherit = 'res.company'

    cogs_account = fields.Many2one(
        'finance.account',
        '主营业务成本科目',
        ondelete='restrict',
        help='主营业务成本科目,销项发票开具时会用到。')
    profit_account = fields.Many2one(
        'finance.account',
        '本年利润科目',
        ondelete='restrict',
        help='本年利润科目,本年中盈利的科目,在结转时会用到。')
    remain_account = fields.Many2one(
        'finance.account', '未分配利润科目', ondelete='restrict', help='未分配利润科目。')
    import_tax_account = fields.Many2one(
        'finance.account',
        "进项税科目",
        ondelete='restrict',
        help='进项税额，是指纳税人购进货物、加工修理修配劳务、服务、无形资产或者不动产，支付或者负担的增值税额。')
    output_tax_account = fields.Many2one(
        'finance.account', "销项税科目", ondelete='restrict')

    operating_cost_account_id = fields.Many2one(
        'finance.account',
        ondelete='restrict',
        string='生产费用科目',
        help='用在组装拆卸的费用上')


class BankAccount(models.Model):
    _inherit = 'bank.account'

    account_id = fields.Many2one(
        'finance.account',
        '科目',
        domain="[('account_type','=','normal')]")
    currency_id = fields.Many2one(
        'res.currency', '外币币别', related='account_id.currency_id', store=True)
    currency_amount = fields.Float('外币金额', digits='Amount')


class CoreCategory(models.Model):
    """继承core category，添加科目类型"""
    _inherit = 'core.category'

    account_id = fields.Many2one(
        'finance.account',
        '科目', required=True,
        help='科目',
        domain="[('account_type','=','normal')]")
