from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class IraqiTenderAnnouncement(models.Model):
    _name = 'iraqi.tender.announcement'
    _description = 'مشاركة في مناقصة / تقديم عطاء (Tender Participation & Bidding)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'submission_deadline asc, create_date desc, id desc'

    # Identification
    name = fields.Char(
        string='رمز ملف المشاركة التسلسلي',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('جديد'),
        tracking=True
    )
    tender_number = fields.Char(
        string='رقم المناقصة / الدعوة الرسمي',
        required=True,
        tracking=True,
        help='الرقم الرسمي الصادر في إعلان المناقصة أو خطاب الدعوة المباشرة.'
    )
    tender_title = fields.Char(
        string='موضوع وعنوان المناقصة / التجهيز',
        required=True,
        tracking=True,
        help='العنوان والموضوع الرسمي للمشروع أو عقد التجهيز المطروح.'
    )
    tender_type = fields.Selection([
        ('public_national', 'مناقصة عامة وطنية'),
        ('public_international', 'مناقصة عامة دولية'),
        ('limited_tender', 'مناقصة محدودة'),
        ('direct_invitation', 'دعوة مباشرة مستلمة'),
        ('single_source', 'عرض وحيد (Single Source)'),
        ('direct_pricing', 'طلب تسعير مباشر / استدراج عروض')
    ], string='أسلوب ونوع المناقصة', default='direct_invitation', required=True, tracking=True)

    # Client / Announcing Authority
    beneficiary_id = fields.Many2one(
        'res.partner',
        string='الجهة صاحبة العمل / المستفيدة (الوزارة / المحافظة / العميل)',
        required=True,
        domain="[('is_company', '=', True)]",
        tracking=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='شركتنا المتقدمة بالعطاء',
        required=True,
        default=lambda self: self.env.company
    )
    department_id = fields.Many2one(
        'hr.department',
        string='القسم المكلف بالعطاء (التجاري / الهندسي)',
        tracking=True
    )
    responsible_user_id = fields.Many2one(
        'res.users',
        string='مهندس التسعير / مسؤول إعداد العطاء',
        default=lambda self: self.env.user,
        tracking=True
    )

    # Tender Purchase & Deadlines
    tender_doc_cost = fields.Monetary(
        string='ثمن شراء وثائق المناقصة (دينار / دولار)',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
        help='المبلغ المدفوع لشراء كراس الشروط والمواصفات.'
    )
    tender_doc_receipt = fields.Char(
        string='رقم إيصال / وصل شراء المناقصة',
        tracking=True
    )
    purchase_date = fields.Date(
        string='تاريخ شراء / استلام الكراس',
        default=fields.Date.context_today,
        tracking=True
    )
    submission_deadline = fields.Datetime(
        string='آخر موعد لتقديم العطاء (Submission Deadline)',
        required=True,
        tracking=True,
        help='الموعد النهائي لتقديم العطاء الفني والمالي والكفالة المصرفية.'
    )
    envelope_opening_date = fields.Datetime(
        string='موعد وتاريخ فتح المظاريف والعطاءات',
        tracking=True
    )
    closing_date = fields.Datetime(
        string='موعد الغلق',
        related='submission_deadline',
        store=True,
        readonly=False
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='عملة العطاء',
        required=True,
        default=lambda self: self.env.company.currency_id
    )

    # Financial Costing & Bid Offer (التسعير وهامش الربح)
    line_ids = fields.One2many(
        'iraqi.tender.line',
        'tender_id',
        string='جدول الكميات والتسعير (BOQ Pricing)'
    )
    total_estimated_cost = fields.Monetary(
        string='إجمالي الكلفة التقديرية الداخلية (كلفة الشراء والتنفيذ)',
        currency_field='currency_id',
        compute='_compute_financial_totals',
        store=True,
        tracking=True,
        help='إجمالي الكلفة علينا للمواد والشحن والتنفيذ.'
    )
    total_bid_amount = fields.Monetary(
        string='إجمالي مبلغ العطاء المقدم (Offered Bid Price)',
        currency_field='currency_id',
        compute='_compute_financial_totals',
        store=True,
        tracking=True,
        help='السعر الإجمالي المقدم في العرض المالي للجهة المستفيدة.'
    )
    estimated_cost = fields.Monetary(
        string='مبلغ العطاء',
        related='total_bid_amount',
        store=True,
        readonly=True
    )
    expected_profit_amount = fields.Monetary(
        string='إجمالي هامش الربح المتوقع',
        currency_field='currency_id',
        compute='_compute_financial_totals',
        store=True,
        tracking=True
    )
    expected_profit_margin = fields.Float(
        string='نسبة الربح المتوقعة (%)',
        compute='_compute_financial_totals',
        store=True
    )

    # Initial Bank Guarantee (خطاب ضمان دخول المناقصة - Bid Bond 1%)
    bid_bond_percentage = fields.Float(
        string='نسبة التأمينات الأولية المطلوبة (Bid Bond %)',
        default=1.0,
        help='النسبة المئوية المقررة لكفالة دخول المناقصة (افتراضياً 1% وفق تعليمات العقود الحكومية).'
    )
    required_bid_bond = fields.Monetary(
        string='مبلغ التأمينات الأولية المطلوب تقديمه',
        currency_field='currency_id',
        compute='_compute_bid_bond',
        store=True,
        tracking=True
    )
    bid_bond_number = fields.Char(
        string='رقم خطاب الضمان / الصك المصدق الصادر',
        tracking=True
    )
    bid_bond_bank = fields.Char(
        string='المصرف المصدر لخطاب الضمان (مثال: TBI / الرافدين)',
        tracking=True
    )
    bid_bond_issue_date = fields.Date(
        string='تاريخ إصدار الكفالة المصرفية',
        tracking=True
    )
    bid_bond_expiry_date = fields.Date(
        string='تاريخ نفاذ وانتهاء الكفالة المصرفية',
        tracking=True
    )
    bid_bond_status = fields.Selection([
        ('draft', 'قيد الإصدار لدى المصرف'),
        ('active', 'صادرة وسارية ومودعة مع العطاء'),
        ('extended', 'تم تمديد صلاحية الكفالة'),
        ('released', 'تم استرداد وإلغاء الكفالة (انتهاء العطاء)'),
        ('confiscated', 'مصادرة (نكول / لا سمح الله)')
    ], string='موقف كفالة الدخول المصرفية', default='draft', tracking=True)

    # Required Documents Checklist (قائمة المستمسكات المطلوبة للعطاء)
    doc_company_reg = fields.Boolean(string='شهادة تأسيس الشركة والأوراق الرسمية', default=False)
    doc_tax_clearance = fields.Boolean(string='كتاب براءة الذمة من الضرائب نافذ', default=False)
    doc_contractor_classification = fields.Boolean(string='هوية تصنيف المقاولين / غرفة التجارة', default=False)
    doc_similar_works = fields.Boolean(string='قائمة الأعمال المماثلة وشهادات الخبرة', default=False)
    doc_financial_statements = fields.Boolean(string='الحسابات الختامية المصادقة لآخر سنتين', default=False)
    doc_bid_bond_ready = fields.Boolean(string='أصل خطاب الضمان المصرفي / الصك المصدق', default=False)
    doc_technical_offer = fields.Boolean(string='العرض الفني والمواصفات والكتلوجات', default=False)
    doc_financial_offer = fields.Boolean(string='العرض المالي وجدول الكميات المسعر ومختوم', default=False)

    # Competitor Analysis upon Bid Opening (المنافسون عند فتح المظاريف)
    competitor_ids = fields.One2many(
        'iraqi.tender.competitor',
        'tender_id',
        string='أسعار وعطاءات الشركات المنافسة'
    )
    competitor_count = fields.Integer(
        string='عدد المنافسين',
        compute='_compute_counts'
    )
    our_rank = fields.Integer(
        string='ترتيبنا المالي بين المنافسين (الأول، الثاني...)',
        default=1,
        tracking=True
    )

    # Awarding Decision & Contract Link (الإحالة وتوقيع العقد لصالحنا)
    is_won = fields.Boolean(
        string='فوز بالعطاء والإحالة لصالحنا',
        tracking=True
    )
    award_letter_number = fields.Char(
        string='رقم كتاب الإحالة والمصادقة الصادر لصالحنا',
        tracking=True
    )
    award_letter_date = fields.Date(
        string='تاريخ كتاب الإحالة والمصادقة',
        tracking=True
    )
    awarded_amount = fields.Monetary(
        string='مبلغ الإحالة النهائي المصادق عليه',
        currency_field='currency_id',
        tracking=True
    )
    lost_reason = fields.Selection([
        ('higher_price', 'السعر المقدم أعلى من المنافس الفائز'),
        ('technical_disqualification', 'استبعاد فني أو مواصفات بديلة'),
        ('bid_bond_issue', 'ملاحظة في الكفالة المصرفية'),
        ('cancelled_by_client', 'إلغاء المناقصة من قبل الجهة المعلنة'),
        ('other', 'أسباب أخرى')
    ], string='سبب عدم الفوز (في حال الخسارة)', tracking=True)
    lost_notes = fields.Text(string='ملاحظات وتقييم أسباب الخسارة للدروس المستفادة')

    # Workflow State
    state = fields.Selection([
        ('draft', 'قيد الدراسة والتسعير'),
        ('submitted', 'تم تقديم العطاء والضمان'),
        ('opening', 'فتح المظاريف ولجنة التحليل'),
        ('awarded', 'تمت الإحالة وفوز العطاء (Awarded)'),
        ('contracted', 'تم توقيع وإبرام العقد'),
        ('lost', 'لم نحظَ بالإحالة (غير فائز)'),
        ('cancelled', 'اعتذار / ملغاة')
    ], string='مرحلة ملف المناقصة', default='draft', tracking=True)

    notes = fields.Html(string='الشروط الخاصة والملاحظات الفنية للمناقصة')

    # -------------------------------------------------------------------------
    # COMPUTED METHODS
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('جديد')) == _('جديد'):
                vals['name'] = self.env['ir.sequence'].next_by_code('iraqi.tender.announcement') or _('جديد')
        return super().create(vals_list)

    @api.depends('line_ids.total_cost', 'line_ids.subtotal')
    def _compute_financial_totals(self):
        for record in self:
            record.total_estimated_cost = sum(record.line_ids.mapped('total_cost'))
            record.total_bid_amount = sum(record.line_ids.mapped('subtotal'))
            record.expected_profit_amount = record.total_bid_amount - record.total_estimated_cost
            if record.total_estimated_cost > 0:
                record.expected_profit_margin = (record.expected_profit_amount / record.total_estimated_cost) * 100.0
            else:
                record.expected_profit_margin = 100.0 if record.total_bid_amount > 0 else 0.0

    @api.depends('total_bid_amount', 'bid_bond_percentage')
    def _compute_bid_bond(self):
        for record in self:
            record.required_bid_bond = (record.total_bid_amount * (record.bid_bond_percentage / 100.0))

    @api.depends('competitor_ids')
    def _compute_counts(self):
        for record in self:
            record.competitor_count = len(record.competitor_ids)

    # -------------------------------------------------------------------------
    # ACTIONS & WORKFLOW
    # -------------------------------------------------------------------------
    def action_submit_bid(self):
        self.ensure_one()
        if not self.line_ids:
            raise ValidationError(_('يرجى إدخال بنود التسعير وجدول الكميات قبل تقديم العطاء.'))
        self.write({
            'state': 'submitted',
            'bid_bond_status': 'active' if self.bid_bond_number else 'draft'
        })

    def action_open_envelopes(self):
        self.ensure_one()
        self.write({'state': 'opening'})

    def action_win_award(self):
        self.ensure_one()
        self.write({
            'state': 'awarded',
            'is_won': True,
            'awarded_amount': self.awarded_amount or self.total_bid_amount
        })

    def action_mark_lost(self):
        self.ensure_one()
        self.write({
            'state': 'lost',
            'is_won': False
        })

    def action_release_bid_bond(self):
        self.ensure_one()
        self.write({'bid_bond_status': 'released'})

    def action_reset_draft(self):
        self.ensure_one()
        self.write({'state': 'draft'})

    def action_cancel(self):
        self.ensure_one()
        self.write({'state': 'cancelled'})
