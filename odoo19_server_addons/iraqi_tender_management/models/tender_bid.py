from odoo import models, fields, api, _


class IraqiTenderBid(models.Model):
    _name = 'iraqi.tender.bid'
    _description = 'عطاء وعرض المناقصة (Tender Bid Offer)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'total_bid_amount asc, id desc'

    name = fields.Char(
        string='رمز العطاء / العرض',
        required=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('iraqi.tender.bid') or _('BID-001'),
        tracking=True
    )
    tender_id = fields.Many2one(
        'iraqi.tender.announcement',
        string='المناقصة المرتبطة',
        required=True,
        ondelete='cascade',
        index=True
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='مقدم العطاء (الشركة / المجهز / المقاول)',
        required=True,
        tracking=True
    )
    submission_date = fields.Date(
        string='تاريخ تقديم العطاء',
        default=fields.Date.context_today,
        required=True,
        tracking=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='العملة',
        related='tender_id.currency_id',
        store=True,
        readonly=True
    )
    
    # Financial Pricing
    total_bid_amount = fields.Monetary(
        string='إجمالي مبلغ العطاء المالي',
        currency_field='currency_id',
        compute='_compute_total_bid_amount',
        store=True,
        tracking=True,
        help='إجمالي السعر المقدم من الشركة لكافة بنود المناقصة.'
    )
    variance_with_estimated = fields.Monetary(
        string='الفارق عن الكلفة التخمينية (+/-)',
        currency_field='currency_id',
        compute='_compute_variance',
        store=True,
        help='الفارق بين السعر المقدم والكلفة التخمينية الرسمية.'
    )
    variance_percentage = fields.Float(
        string='نسبة الانحراف عن التخميني (%)',
        compute='_compute_variance',
        store=True
    )

    # Initial Guarantees (كفالة دخول المناقصة - Bid Bond)
    has_bid_bond = fields.Boolean(
        string='تقديم خطاب ضمان التأمينات الأولية (Bid Bond)',
        default=True,
        tracking=True
    )
    bid_bond_number = fields.Char(
        string='رقم خطاب الضمان / الصك المصدق',
        tracking=True
    )
    bid_bond_bank = fields.Char(
        string='المصرف العراقي المصدر للضمان',
        tracking=True
    )
    bid_bond_amount = fields.Monetary(
        string='مبلغ التأمينات المقدم',
        currency_field='currency_id',
        tracking=True
    )
    bid_bond_expiry_date = fields.Date(
        string='تاريخ نفاذ الكفالة المصرفية',
        tracking=True
    )
    bid_bond_status = fields.Selection([
        ('valid', 'سارية ومطابقة'),
        ('expired', 'منتهية الصلاحية'),
        ('returned', 'أعيدت للشركة (غير فائزة)'),
        ('confiscated', 'مصادرة (نكول / إخلال)')
    ], string='موقف التأمينات الأولية', default='valid', tracking=True)

    # Technical & Committee Evaluation
    technical_score = fields.Float(
        string='الدرجة الفنية (من 100)',
        default=80.0,
        tracking=True,
        help='تقييم اللجنة الفنية للعطاء وجودة المواصفات والخبرات السابقة.'
    )
    financial_rank = fields.Integer(
        string='الترتيب المالي',
        default=1,
        help='ترتيب العطاء من حيث السعر (الأول الأوطأ سعراً).'
    )
    is_technically_accepted = fields.Boolean(
        string='المطابقة الفنية (مقبول فنياً)',
        default=True,
        tracking=True
    )
    evaluation_notes = fields.Text(string='ملاحظات وتوصيات لجنة فتح وتحليل العطاءات')

    # State
    state = fields.Selection([
        ('submitted', 'تم الاستلام'),
        ('under_eval', 'قيد التحليل الفني والمالي'),
        ('accepted', 'مقبول فنياً ومطابق'),
        ('awarded', 'تمت الإحالة (عطاء فائز)'),
        ('rejected', 'مستبعد / غير مؤهل'),
        ('cancelled', 'ملغى')
    ], string='حالة العطاء', default='submitted', tracking=True)

    line_ids = fields.One2many(
        'iraqi.tender.bid.line',
        'bid_id',
        string='تسعير بنود العطاء'
    )

    @api.depends('line_ids.subtotal')
    def _compute_total_bid_amount(self):
        for bid in self:
            bid.total_bid_amount = sum(bid.line_ids.mapped('subtotal'))

    @api.depends('total_bid_amount', 'tender_id.estimated_cost')
    def _compute_variance(self):
        for bid in self:
            bid.variance_with_estimated = bid.total_bid_amount - bid.tender_id.estimated_cost
            if bid.tender_id.estimated_cost > 0:
                bid.variance_percentage = (bid.variance_with_estimated / bid.tender_id.estimated_cost) * 100.0
            else:
                bid.variance_percentage = 0.0

    def action_accept(self):
        self.ensure_one()
        self.write({'state': 'accepted', 'is_technically_accepted': True})

    def action_reject(self):
        self.ensure_one()
        self.write({'state': 'rejected'})


class IraqiTenderBidLine(models.Model):
    _name = 'iraqi.tender.bid.line'
    _description = 'تسعير بند العطاء (Bid Line Price)'
    _order = 'sequence, id'

    sequence = fields.Integer(string='التسلسل', default=10)
    bid_id = fields.Many2one(
        'iraqi.tender.bid',
        string='العطاء المرتبط',
        required=True,
        ondelete='cascade',
        index=True
    )
    tender_line_id = fields.Many2one(
        'iraqi.tender.line',
        string='بند المناقصة الأصلي',
        required=True
    )
    name = fields.Text(
        string='المواصفات الفنية والمادة المسعرة',
        required=True
    )
    quantity = fields.Float(
        string='الكمية',
        digits='Product Unit of Measure',
        required=True,
        default=1.0
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='وحدة القياس',
        required=True
    )
    unit_price = fields.Monetary(
        string='سعر الوحدة المقدم',
        currency_field='currency_id',
        required=True,
        default=0.0
    )
    subtotal = fields.Monetary(
        string='إجمالي السعر المقدم',
        currency_field='currency_id',
        compute='_compute_subtotal',
        store=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='العملة',
        related='bid_id.currency_id',
        store=True,
        readonly=True
    )

    @api.onchange('tender_line_id')
    def _onchange_tender_line_id(self):
        if self.tender_line_id:
            self.name = self.tender_line_id.name
            self.quantity = self.tender_line_id.quantity
            self.uom_id = self.tender_line_id.uom_id.id
            self.unit_price = self.tender_line_id.estimated_unit_price

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_price
