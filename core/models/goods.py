# Copyright 2016 上海开阖软件有限公司 (http://www.osbzr.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _

'''
会计月末的成本核算方法
库存收发明细表全部使用个别计价
月末结账时再根据此核算方法生成发出成本差异凭证
'''
CORE_COST_METHOD = [('average', '全月一次加权平均法'),
                    ('std', '定额成本'),
                    ('fifo', '个别计价法'),
                    ]

AVAILABLE_PRIORITIES = [
    ('0', 'E'),
    ('1', 'D'),
    ('2', 'C'),
    ('3', 'B'),
    ('4', 'A'),
]


class Goods(models.Model):
    _name = 'goods'
    _description = '商品'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc'

    @api.model
    def _get_default_not_saleable_impl(self):
        return False

    @api.model
    def _get_default_not_saleable(self):
        return self._get_default_not_saleable_impl()

    @api.model
    def _get_default_not_buyable_impl(self):
        return False

    @api.model
    def _get_default_not_buyable(self):
        return self._get_default_not_buyable_impl()

    def name_get(self):
        '''在many2one字段里显示 编号_名称'''
        res = []

        for Goods in self:
            res.append((Goods.id, Goods.code and (
                Goods.code + '_' + Goods.name) or Goods.name))
        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        '''在many2one字段中支持按编号搜索'''
        args = args or []
        code_search_goods = []
        if name:
            goods_id = self.search([('code', '=', name)])
            if goods_id:
                return goods_id.name_get()
            args.append(('code', 'ilike', name))
            goods_ids = self.search(args)
            if goods_ids:
                code_search_goods = goods_ids.name_get()

            args.remove(('code', 'ilike', name))
        search_goods = super(Goods, self).name_search(
            name=name, args=args,
            operator=operator, limit=limit
        )
        for good_tup in code_search_goods:  # 去除重复产品
            if good_tup not in search_goods:
                search_goods.append(good_tup)
        return search_goods

    @api.model_create_multi
    def create(self, vals_list):
        '''导入商品时，如果辅助单位为空，则用计量单位来填充它'''
        for vals in vals_list:
            if not vals.get('uos_id'):
                vals.update({'uos_id': vals.get('uom_id')})
        return super().create(vals_list)

    def copy(self, default=None):
        ''' 避免复制时提示名称和编号不可重复 '''
        if default is None:
            default = {}
        if 'name' not in default:
            default.update(name=_('%s (copy)') % (self.name))
        if self.code and 'code' not in default:
            default.update(code=_('%s (copy)') % (self.code))
        return super(Goods, self).copy(default=default)

    code = fields.Char('编号')
    name = fields.Char('名称', required=True, copy=False)
    priority = fields.Selection(AVAILABLE_PRIORITIES, '商品重要性', default='0')
    category_id = fields.Many2one('core.category', '核算类别',
                                  ondelete='restrict',
                                  domain=[('type', '=', 'goods')],
                                  required=True,
                                  help='从会计科目角度划分的类别',
                                  )
    uom_id = fields.Many2one('uom', ondelete='restrict',
                             string='计量单位', required=True)
    uos_id = fields.Many2one('uom', ondelete='restrict', string='辅助单位')
    conversion = fields.Float(
        string='转化率', default=1, digits=(16, 3),
        help='1个辅助单位等于多少计量单位的数量，如1箱30个苹果，这里就输入30')
    cost = fields.Float('成本',
                        digits='Price')
    cost_method = fields.Selection(CORE_COST_METHOD, '存货计价方法',
                                   help='''GoodERP仓库模块使用先进先出规则匹配
                                   每次出库对应的入库成本和数量，但不实时记账。
                                   财务月结时使用此方法相应调整发出成本''')
    tax_rate = fields.Float('税率(%)',
                            help='商品税率')
    not_saleable = fields.Boolean('不可销售',
                                  default=_get_default_not_saleable,
                                  help='商品是否不可销售，勾选了就不可销售，未勾选可销售')
    not_buyable = fields.Boolean('不可采购',
                                 default=_get_default_not_buyable,
                                 help='商品是否不可采购，勾选了就不可采购，未勾选可采购')
    active = fields.Boolean('启用', default=True)
    company_id = fields.Many2one(
        'res.company',
        string='公司',
        change_default=True,
        default=lambda self: self.env.company)
    brand = fields.Many2one('core.value', '品牌',
                            ondelete='restrict',
                            domain=[('type', '=', 'brand')],
                            context={'type': 'brand'})
    size = fields.Char('尺寸')

    _sql_constraints = [
        ('conversion_no_zero', 'check(conversion != 0)', '商品的转化率不能为0')
    ]
