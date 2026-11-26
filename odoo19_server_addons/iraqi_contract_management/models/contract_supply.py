from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta


class DirectSupplyContract(models.Model):
    _name = 'direct.supply.contract'
    _description = 'عقد التجهيز المباشر والمقاولات (Direct Supply Contract)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    # Identification
    name = fields.Char(
        string='رمز العقد التسلسلي',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('جديد'),
        tracking=True
    )
    contract_number = fields.Char(
        string='رقم العقد التعاقدي المعتمد',
        required=True,
        tracking=True,
        help='رقم العقد الرسمي الصادر من الجهة المستفيدة أو وزارة التخطيط.'
    )
    contract_subject = fields.Char(
        string='موضوع وعنوان العقد',
        required=True,
        tracking=True,
        help='العنوان الرئيسي لعقد التجهيز والمقاولة.'
    )
    description = fields.Html(
        string='تفاصيل العقد ونطاق التجهيز والمواصفات',
        help='الشروط الفنية، المواصفات القياسية، وجداول التجهيز المعتمدة.'
    )

    # Tender Link (Smart Connection to Iraqi Tender Management)
    tender_id = fields.Many2one(
        'iraqi.tender.announcement',
        string='المناقصة المرتبطة (إن وجدت)',
        tracking=True,
        help='المناقصة أو الدعوة المباشرة التي نتج عنها إبرام هذا العقد.'
    )

    # Parties
    beneficiary_id = fields.Many2one(
        'res.partner',
        string='الجهة المستفيدة (العميل / الوزارة / الدائرة)',
        required=True,
        tracking=True,
        domain="[('is_company', '=', True)]"
    )
    vendor_id = fields.Many2one(
        'res.partner',
        string='الجهة الموردة لمواد العقد (المجهز / المقاول)',
        required=True,
        tracking=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='الشركة المنفذة',
        required=True,
        default=lambda self: self.env.company
    )
    department_id = fields.Many2one(
        'hr.department',
        string='القسم المسؤول عن العقد',
        tracking=True
    )
    responsible_user_id = fields.Many2one(
        'res.users',
        string='الشخص / الموظف المسؤول',
        default=lambda self: self.env.user,
        tracking=True
    )

    # Dates & Execution Timeline
    contract_date = fields.Date(
        string='تاريخ توقيع العقد',
        default=fields.Date.context_today,
        required=True,
        tracking=True
    )
    expected_delivery_date = fields.Date(
        string='تاريخ التجهيز / التسليم التعاقدي',
        required=True,
        tracking=True
    )
    actual_delivery_date = fields.Date(
        string='تاريخ التسليم الفعلي المنجز',
        tracking=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='العملة',
        required=True,
        default=lambda self: self.env.company.currency_id
    )

    # Supply Type (Local vs Imported)
    is_local_supply = fields.Boolean(
        string='تجهيز داخلي (محلي)',
        default=False,
        tracking=True,
        help='إذا تم التحديد، يتم إلغاء وتصفير تكاليف الشحن الدولي والتخليص الجمركي الخارجي.'
    )

    # Cost Elements & Pricing
    material_cost = fields.Monetary(
        string='كلفة المواد الأساسية',
        currency_field='currency_id',
        compute='_compute_material_cost',
        store=True,
        tracking=True
    )
    shipping_cost = fields.Monetary(
        string='كلفة الشحن والنقل الدولي',
        currency_field='currency_id',
        default=0.0,
        tracking=True
    )
    customs_cost = fields.Monetary(
        string='كلفة التخليص الجمركي والفحص',
        currency_field='currency_id',
        default=0.0,
        tracking=True
    )
    other_cost = fields.Monetary(
        string='مصاريف إضافية وثانوية أخرى',
        currency_field='currency_id',
        default=0.0,
        tracking=True
    )

    # Analytic Account / Cost Center Link
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='الحساب التحليلي (مركز الكلفة)',
        tracking=True
    )
    analytic_distribution = fields.Json(
        string='التوزيع التحليلي',
        compute='_compute_analytic_distribution',
        store=True
    )
    analytic_precision = fields.Integer(
        string='دقة التوزيع التحليلي',
        store=False,
        default=2
    )
    analytic_incurred_cost = fields.Monetary(
        string='المصاريف الفعلية المسجلة بمركز الكلفة',
        currency_field='currency_id',
        compute='_compute_analytic_incurred_cost',
        store=True
    )

    # Financial Totals & Margins
    total_contract_cost = fields.Monetary(
        string='الكلفة التقديرية الإجمالية للعقد',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
        tracking=True
    )
    total_actual_spent = fields.Monetary(
        string='الكلفة الإجمالية المصروفة فعلياً',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
        tracking=True
    )
    contract_tender_value = fields.Monetary(
        string='القيمة الإجمالية التعاقدية (قيمة الإحالة)',
        currency_field='currency_id',
        required=True,
        default=0.0,
        tracking=True
    )
    expected_profit_margin = fields.Monetary(
        string='هامش الربح المتوقع / الفارق المالي',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True
    )
    profit_percentage = fields.Float(
        string='نسبة الربح المتوقعة (%)',
        compute='_compute_totals',
        store=True
    )

    # Bank Guarantees & Bonds (المعايير والضوابط العراقية)
    # 1. Performance Bond (5%)
    has_performance_bond = fields.Boolean(
        string='خطاب ضمان حسن التنفيذ (Performance Bond 5%)',
        default=True,
        tracking=True
    )
    performance_bond_number = fields.Char(string='رقم خطاب ضمان حسن التنفيذ', tracking=True)
    performance_bond_bank = fields.Char(string='المصرف العراقي المصدر لضمان حسن التنفيذ', tracking=True)
    performance_bond_amount = fields.Monetary(
        string='مبلغ ضمان حسن التنفيذ (5%)',
        currency_field='currency_id',
        compute='_compute_guarantee_amounts',
        store=True,
        readonly=False,
        tracking=True
    )
    performance_bond_expiry = fields.Date(string='تاريخ نفاذ ضمان حسن التنفيذ', tracking=True)
    performance_bond_status = fields.Selection([
        ('deposited', 'مودع وساري المفعول'),
        ('extended', 'تم التمديد'),
        ('released', 'مطلق ومسترد بعد الاستلام النهائي'),
        ('confiscated', 'مصادر (إخلال بالعقد)')
    ], string='موقف ضمان حسن التنفيذ', default='deposited', tracking=True)

    # 2. Advance Payment Guarantee (10%)
    has_advance_payment_bond = fields.Boolean(
        string='خطاب ضمان السلفة التشغيلية (Advance Guarantee)',
        default=False,
        tracking=True
    )
    advance_bond_number = fields.Char(string='رقم خطاب ضمان السلفة', tracking=True)
    advance_bond_bank = fields.Char(string='مصرف السلفة التشغيلية', tracking=True)
    advance_bond_amount = fields.Monetary(
        string='مبلغ كفالة السلفة التشغيلية',
        currency_field='currency_id',
        compute='_compute_guarantee_amounts',
        store=True,
        readonly=False,
        tracking=True
    )
    advance_bond_expiry = fields.Date(string='تاريخ نفاذ كفالة السلفة', tracking=True)
    advance_bond_status = fields.Selection([
        ('active', 'ساري ومودع'),
        ('recovered', 'تم استرداده بالكامل مع الدفعات'),
        ('released', 'مطلق')
    ], string='موقف ضمان السلفة التشغيلية', default='active', tracking=True)

    # Delay Penalties & Time Extensions (العقود الحكومية رقم 2 لسنة 2014)
    apply_penalty = fields.Boolean(
        string='تطبيق الغرامات التأخيرية',
        default=True
    )
    penalty_rate_per_day = fields.Float(
        string='نسبة الغرامة التأخيرية اليومية (%)',
        default=0.1,  # 0.1% or 1/1000 per day
        help='النسبة اليومية المعتمدة (افتراضياً 0.1% يومياً أو 1 بالـ 1000).'
    )
    time_extension_days = fields.Integer(
        string='أوامر التمديد والمدد التعويضية المعتمدة (أيام)',
        default=0,
        tracking=True,
        help='المدد الإضافية المصادق عليها بأوامر وزارية / إدارية ممددة لمدة العقد.'
    )
    adjusted_delivery_date = fields.Date(
        string='تاريخ التسليم بعد التمديدات المعتمدة',
        compute='_compute_delay_penalties',
        store=True
    )
    delay_days = fields.Integer(
        string='عدد أيام التأخير الفعلية',
        compute='_compute_delay_penalties',
        store=True
    )
    total_penalty_amount = fields.Monetary(
        string='إجمالي مبلغ الغرامات التأخيرية المستقطعة',
        currency_field='currency_id',
        compute='_compute_delay_penalties',
        store=True,
        tracking=True
    )
    net_contract_payout = fields.Monetary(
        string='صافي مستحقات العقد بعد استقطاع الغرامات',
        currency_field='currency_id',
        compute='_compute_delay_penalties',
        store=True
    )

    # Tax Retentions & Clearance (أمانات الهيئة العامة للضرائب)
    tax_retention_rate = fields.Float(
        string='نسبة الأمانات الضريبية (%)',
        default=3.0,
        help='النسبة القانونية المستقطعة لحساب الهيئة العامة للضرائب لغاية تقديم براءة الذمة.'
    )
    tax_retention_amount = fields.Monetary(
        string='مبلغ الأمانات الضريبية المحتجز',
        currency_field='currency_id',
        compute='_compute_tax_retentions',
        store=True
    )
    tax_clearance_status = fields.Selection([
        ('pending', 'بانتظار التحصيل وتقديم الأوليات'),
        ('submitted', 'تم تقديم طلب براءة الذمة'),
        ('cleared', 'صدرت براءة الذمة الضريبية الرسمية'),
        ('released', 'تم إطلاق الأمانات الضريبية للمجهز')
    ], string='موقف براءة الذمة الضريبية', default='pending', tracking=True)

    # Handover & Warranty (الاستلام والصيانة)
    provisional_handover_date = fields.Date(string='تاريخ الاستلام الأولي للمواد', tracking=True)
    warranty_period_months = fields.Integer(string='فترة الصيانة والضمان (بالأشهر)', default=12)
    final_handover_date = fields.Date(string='تاريخ الاستلام النهائي والقبول', tracking=True)

    # Workflow Stages
    state = fields.Selection([
        ('draft', 'مسودة'),
        ('signed', 'تم توقيع العقد'),
        ('guarantee_deposited', 'إيداع خطابات الضمان المصرفية'),
        ('sourcing', 'التعاقد وأمر الشراء مع المورد'),
        ('shipping', 'الشحن والنقل الدولي'),
        ('clearance', 'التخليص الجمركي والفحص النوعي'),
        ('site_delivery', 'التجهيز والتوريد للموقع'),
        ('provisional_acceptance', 'الاستلام الأولي والمطابقة'),
        ('final_acceptance', 'الاستلام النهائي وانتهاء الضمان'),
        ('completed', 'منجز ومسدد بالكامل ومصادق'),
        ('cancelled', 'ملغى')
    ], string='مرحلة تنفيذ العقد', default='draft', tracking=True)

    progress_percentage = fields.Float(
        string='نسبة إنجاز العقد (%)',
        compute='_compute_progress_percentage',
        store=True
    )

    # Payment Schedule & Due Status
    payment_type = fields.Selection([
        ('full', 'تسديد كامل (دفعة واحدة)'),
        ('installments', 'دفعات مرحلية مجدولة')
    ], string='طريقة تسديد العقد', default='installments', required=True)

    payment_schedule_ids = fields.One2many(
        'direct.supply.payment.schedule',
        'contract_id',
        string='جدول الدفعات وتواريخ الاستحقاق'
    )
    total_paid_amount = fields.Monetary(
        string='إجمالي المبالغ المسددة',
        currency_field='currency_id',
        compute='_compute_payment_summary',
        store=True
    )
    remaining_payment_amount = fields.Monetary(
        string='المبلغ المتبقي غير المسدد',
        currency_field='currency_id',
        compute='_compute_payment_summary',
        store=True
    )
    next_due_date = fields.Date(
        string='تاريخ استحقاق الدفعة القادمة',
        compute='_compute_payment_summary',
        store=True
    )
    due_status = fields.Selection([
        ('paid', 'مسدد بالكامل'),
        ('up_to_date', 'منتظم السداد'),
        ('due_soon', 'دفعة مستحقة خلال 7 أيام'),
        ('overdue', 'توجد دفعات متأخرة عن موعدها')
    ], string='حالة استحقاق الدفعات', compute='_compute_payment_summary', store=True)

    # Relational Lines & Documents
    line_ids = fields.One2many(
        'direct.supply.contract.line',
        'contract_id',
        string='بنود المواد والتجهيز'
    )
    document_ids = fields.One2many(
        'direct.supply.document',
        'contract_id',
        string='أرشيف ومستندات العقد والمناقصة'
    )
    document_count = fields.Integer(
        string='عدد المستندات والمرفقات',
        compute='_compute_document_count'
    )

    # -------------------------------------------------------------------------
    # COMPUTED METHODS
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('جديد')) == _('جديد'):
                vals['name'] = self.env['ir.sequence'].next_by_code('direct.supply.contract') or _('جديد')
        return super().create(vals_list)

    @api.onchange('is_local_supply')
    def _onchange_is_local_supply(self):
        if self.is_local_supply:
            self.shipping_cost = 0.0
            self.customs_cost = 0.0

    @api.depends('line_ids.subtotal')
    def _compute_material_cost(self):
        for record in self:
            record.material_cost = sum(record.line_ids.mapped('subtotal'))

    @api.depends('contract_tender_value', 'has_performance_bond', 'has_advance_payment_bond')
    def _compute_guarantee_amounts(self):
        for record in self:
            if record.has_performance_bond and record.contract_tender_value:
                record.performance_bond_amount = record.contract_tender_value * 0.05
            if record.has_advance_payment_bond and record.contract_tender_value:
                record.advance_bond_amount = record.contract_tender_value * 0.10

    @api.depends('analytic_account_id')
    def _compute_analytic_distribution(self):
        for record in self:
            if record.analytic_account_id:
                record.analytic_distribution = {str(record.analytic_account_id.id): 100.0}
            else:
                record.analytic_distribution = False

    @api.depends('analytic_account_id')
    def _compute_analytic_incurred_cost(self):
        for record in self:
            if record.analytic_account_id:
                lines = self.env['account.analytic.line'].search([
                    ('account_id', '=', record.analytic_account_id.id),
                    ('amount', '<', 0)
                ])
                record.analytic_incurred_cost = abs(sum(lines.mapped('amount')))
            else:
                record.analytic_incurred_cost = 0.0

    @api.depends('material_cost', 'shipping_cost', 'customs_cost', 'other_cost', 'contract_tender_value', 'analytic_incurred_cost', 'is_local_supply')
    def _compute_totals(self):
        for record in self:
            shipping = 0.0 if record.is_local_supply else record.shipping_cost
            customs = 0.0 if record.is_local_supply else record.customs_cost
            record.total_contract_cost = record.material_cost + shipping + customs + record.other_cost
            record.total_actual_spent = record.analytic_incurred_cost or record.total_contract_cost
            record.expected_profit_margin = record.contract_tender_value - record.total_contract_cost
            if record.contract_tender_value > 0:
                record.profit_percentage = (record.expected_profit_margin / record.contract_tender_value) * 100.0
            else:
                record.profit_percentage = 0.0

    @api.depends('apply_penalty', 'penalty_rate_per_day', 'expected_delivery_date', 'time_extension_days', 'actual_delivery_date', 'contract_tender_value', 'state')
    def _compute_delay_penalties(self):
        today = fields.Date.context_today(self)
        for record in self:
            if record.expected_delivery_date:
                record.adjusted_delivery_date = record.expected_delivery_date + timedelta(days=record.time_extension_days)
            else:
                record.adjusted_delivery_date = False

            if not record.apply_penalty or not record.adjusted_delivery_date:
                record.delay_days = 0
                record.total_penalty_amount = 0.0
                record.net_contract_payout = record.contract_tender_value
                continue

            end_date = record.actual_delivery_date or (today if record.state not in ('draft', 'cancelled') else record.adjusted_delivery_date)
            if end_date > record.adjusted_delivery_date:
                delta = (end_date - record.adjusted_delivery_date).days
                record.delay_days = delta if delta > 0 else 0
            else:
                record.delay_days = 0

            penalty = (record.contract_tender_value * (record.penalty_rate_per_day / 100.0)) * record.delay_days
            max_penalty_cap = record.contract_tender_value * 0.10
            record.total_penalty_amount = min(penalty, max_penalty_cap) if max_penalty_cap > 0 else penalty
            record.net_contract_payout = record.contract_tender_value - record.total_penalty_amount

    @api.depends('contract_tender_value', 'tax_retention_rate')
    def _compute_tax_retentions(self):
        for record in self:
            record.tax_retention_amount = record.contract_tender_value * (record.tax_retention_rate / 100.0)

    @api.depends('state', 'line_ids.delivered_quantity', 'line_ids.quantity')
    def _compute_progress_percentage(self):
        state_weights = {
            'draft': 0.0,
            'signed': 10.0,
            'guarantee_deposited': 20.0,
            'sourcing': 35.0,
            'shipping': 55.0,
            'clearance': 75.0,
            'site_delivery': 90.0,
            'provisional_acceptance': 95.0,
            'final_acceptance': 99.0,
            'completed': 100.0,
            'cancelled': 0.0
        }
        for record in self:
            total_qty = sum(record.line_ids.mapped('quantity'))
            delivered_qty = sum(record.line_ids.mapped('delivered_quantity'))
            if total_qty > 0 and record.state in ('site_delivery', 'provisional_acceptance', 'final_acceptance', 'completed'):
                qty_progress = (delivered_qty / total_qty) * 100.0
                record.progress_percentage = min(100.0, max(qty_progress, state_weights.get(record.state, 0.0)))
            else:
                record.progress_percentage = state_weights.get(record.state, 0.0)

    @api.depends('payment_schedule_ids.state', 'payment_schedule_ids.amount', 'payment_schedule_ids.due_date', 'contract_tender_value')
    def _compute_payment_summary(self):
        today = fields.Date.context_today(self)
        for record in self:
            paid_sum = sum(record.payment_schedule_ids.filtered(lambda p: p.state == 'paid').mapped('amount'))
            record.total_paid_amount = paid_sum
            record.remaining_payment_amount = max(0.0, record.contract_tender_value - paid_sum)
            
            pending_payments = record.payment_schedule_ids.filtered(lambda p: p.state != 'paid').sorted('due_date')
            if pending_payments:
                next_p = pending_payments[0]
                record.next_due_date = next_p.due_date
                if next_p.due_date and next_p.due_date < today:
                    record.due_status = 'overdue'
                elif next_p.due_date and (next_p.due_date - today).days <= 7:
                    record.due_status = 'due_soon'
                else:
                    record.due_status = 'up_to_date'
            else:
                record.next_due_date = False
                if record.total_paid_amount >= record.contract_tender_value and record.contract_tender_value > 0:
                    record.due_status = 'paid'
                else:
                    record.due_status = 'up_to_date'

    @api.depends('document_ids')
    def _compute_document_count(self):
        for record in self:
            record.document_count = len(record.document_ids)

    # -------------------------------------------------------------------------
    # WORKFLOW ACTIONS
    # -------------------------------------------------------------------------
    def action_sign(self):
        self.ensure_one()
        self.write({'state': 'signed'})

    def action_guarantee_deposited(self):
        self.ensure_one()
        self.write({'state': 'guarantee_deposited'})

    def action_sourcing(self):
        self.ensure_one()
        self.write({'state': 'sourcing'})

    def action_shipping(self):
        self.ensure_one()
        if self.is_local_supply:
            self.write({'state': 'site_delivery'})
        else:
            self.write({'state': 'shipping'})

    def action_clearance(self):
        self.ensure_one()
        self.write({'state': 'clearance'})

    def action_site_delivery(self):
        self.ensure_one()
        self.write({'state': 'site_delivery'})

    def action_provisional_acceptance(self):
        self.ensure_one()
        if not self.provisional_handover_date:
            self.provisional_handover_date = fields.Date.context_today(self)
        if not self.actual_delivery_date:
            self.actual_delivery_date = self.provisional_handover_date
        self.write({'state': 'provisional_acceptance'})

    def action_final_acceptance(self):
        self.ensure_one()
        if not self.final_handover_date:
            self.final_handover_date = fields.Date.context_today(self)
        self.write({'state': 'final_acceptance'})

    def action_complete(self):
        self.ensure_one()
        self.write({'state': 'completed'})

    def action_reset_draft(self):
        self.ensure_one()
        self.write({'state': 'draft'})

    def action_cancel(self):
        self.ensure_one()
        self.write({'state': 'cancelled'})

    def action_view_tender(self):
        self.ensure_one()
        if not self.tender_id:
            raise ValidationError(_('هذا العقد غير مرتبط بمناقصة سابقة (عقد تجهيز مباشر مستقل).'))
        return {
            'name': _('المناقصة المرتبطة'),
            'type': 'ir.actions.act_window',
            'res_model': 'iraqi.tender.announcement',
            'view_mode': 'form',
            'res_id': self.tender_id.id,
        }

    def action_view_documents(self):
        self.ensure_one()
        return {
            'name': _('مستندات ومرفقات العقد'),
            'type': 'ir.actions.act_window',
            'res_model': 'direct.supply.document',
            'view_mode': 'list,form',
            'domain': [('contract_id', '=', self.id)],
            'context': {'default_contract_id': self.id},
        }

    def action_view_analytic_lines(self):
        self.ensure_one()
        if not self.analytic_account_id:
            raise ValidationError(_('لا يوجد مركز كلفة مرتبط بهذا العقد.'))
        return {
            'name': _('القيود المحاسبية والمصروفات لمركز الكلفة'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.analytic.line',
            'view_mode': 'list,form,pivot',
            'domain': [('account_id', '=', self.analytic_account_id.id)],
            'context': {'default_account_id': self.analytic_account_id.id},
        }
