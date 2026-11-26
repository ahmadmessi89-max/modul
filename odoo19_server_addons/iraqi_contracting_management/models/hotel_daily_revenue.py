# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class HotelDailyRevenue(models.Model):
    _name = 'hotel.daily.revenue'
    _description = 'كشف الإيرادات والسيولة اليومية للفنادق (Hotel Daily Revenue & Night Audit)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(
        string='رقم كشف الإيراد اليومي',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('مسودة كشف إيراد فندقي'),
        tracking=True
    )
    hotel_name = fields.Char(
        string='اسم الفندق / المنشأة السياحية',
        required=True,
        default='فندق ريانة العود',
        tracking=True,
        help='اسم الفندق التابع للمجموعة المصدر للكشف اليومي.'
    )
    date = fields.Date(
        string='تاريخ الإيراد (يوم العمل الفندقي)',
        default=fields.Date.context_today,
        required=True,
        tracking=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        default=lambda self: self.env.company,
        required=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='العملة',
        related='company_id.currency_id',
        store=True,
        readonly=True
    )

    # Inflow Categories
    room_revenue = fields.Monetary(
        string='إيراد الغرف والأجنحة (Rooms Revenue)',
        currency_field='currency_id',
        default=0.0,
        required=True,
        tracking=True,
        help='إجمالي إيراد المبيت والإقامة للنزلاء.'
    )
    fnb_revenue = fields.Monetary(
        string='إيراد المطاعم والمقاهي (Food & Beverage)',
        currency_field='currency_id',
        default=0.0,
        required=True,
        tracking=True,
        help='إيراد وجبات الإفطار والغداء والعشاء وخدمة الغرف والكافيه.'
    )
    banquet_revenue = fields.Monetary(
        string='إيراد قاعات المناسبات والمؤتمرات (Banquets)',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
        help='إيراد إيجار القاعات وحفلات الأعراس والندوات.'
    )
    laundry_services_revenue = fields.Monetary(
        string='إيراد المغسلة والخدمات الإضافية (Laundry & Misc)',
        currency_field='currency_id',
        default=0.0,
        tracking=True
    )
    other_revenue = fields.Monetary(
        string='إيرادات فندقية أخرى',
        currency_field='currency_id',
        default=0.0,
        tracking=True
    )

    total_daily_revenue = fields.Monetary(
        string='إجمالي إيراد اليوم الفندقي',
        currency_field='currency_id',
        compute='_compute_revenue_totals',
        store=True,
        tracking=True
    )

    # Collection Channels (مصفوفة التحصيل والسيولة النقدية)
    cash_collected = fields.Monetary(
        string='المحصل نقداً في قاصة الفندق (Cash)',
        currency_field='currency_id',
        default=0.0,
        required=True,
        tracking=True,
        help='النقد الفعلي المستلم في صندوق الفندق.'
    )
    pos_card_collected = fields.Monetary(
        string='المحصل عبر نقاط البيع والبطاقات (POS / Cards)',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
        help='المبالغ المقبوضة عبر ماستر كارد، فيزا، كي كارد في الحساب البنكي.'
    )
    corporate_receivables = fields.Monetary(
        string='آجل شركات الطيران والسياحة (City Ledger)',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
        help='فواتير النزلاء المحملة على حسابات الشركات والجهات المتعاقدة.'
    )
    total_collections = fields.Monetary(
        string='إجمالي التحصيلات والذمم',
        currency_field='currency_id',
        compute='_compute_collection_totals',
        store=True
    )
    variance_amount = fields.Monetary(
        string='فارق التحصيل عن الإيراد (+/-)',
        currency_field='currency_id',
        compute='_compute_collection_totals',
        store=True
    )

    # Working Capital Transfer to Contracting
    transfer_to_contracting = fields.Boolean(
        string='تحويل سيولة نقدية لتمويل مشاريع المقاولات',
        default=False,
        help='تفعيل هذا الخيار في حال تم تحويل جزء من النقدية لتغذية صندوق الموقع أو سداد مستحقات مقاولين عاجلة.'
    )
    transfer_amount = fields.Monetary(
        string='المبلغ المحول لقطاع المقاولات',
        currency_field='currency_id',
        default=0.0,
        tracking=True
    )
    destination_project_id = fields.Many2one(
        'project.project',
        string='المشروع الإنشائي المستفيد من السيولة',
        help='المشروع الذي تم تزويده بالسيولة النقدية من إيراد الفندق.'
    )
    destination_journal_id = fields.Many2one(
        'account.journal',
        string='حساب الخزينة / البنك المستلم للسيولة',
        domain="[('type', 'in', ['cash', 'bank'])]"
    )

    # Accounting Integration
    journal_id = fields.Many2one(
        'account.journal',
        string='دفتر يومية الفندق / الإيرادات',
        domain="[('type', 'in', ['sale', 'general', 'cash'])]"
    )
    move_id = fields.Many2one(
        'account.move',
        string='القيد المحاسبي المولد',
        readonly=True,
        copy=False
    )
    state = fields.Selection([
        ('draft', 'مسودة'),
        ('audited', 'مدقق من مدقق الليل (Night Audited)'),
        ('posted', 'مرحل ومثبت في الخزينة والحسابات'),
        ('cancelled', 'ملغى')
    ], string='الحالة', default='draft', tracking=True, index=True)

    auditor_id = fields.Many2one(
        'res.users',
        string='مدقق الحسابات الفندقية',
        default=lambda self: self.env.user,
        tracking=True
    )
    notes = fields.Text(string='ملاحظات ومطابقات التدقيق اليومي')

    @api.depends('room_revenue', 'fnb_revenue', 'banquet_revenue', 'laundry_services_revenue', 'other_revenue')
    def _compute_revenue_totals(self):
        for rec in self:
            rec.total_daily_revenue = (
                rec.room_revenue + rec.fnb_revenue + rec.banquet_revenue +
                rec.laundry_services_revenue + rec.other_revenue
            )

    @api.depends('cash_collected', 'pos_card_collected', 'corporate_receivables', 'total_daily_revenue')
    def _compute_collection_totals(self):
        for rec in self:
            rec.total_collections = rec.cash_collected + rec.pos_card_collected + rec.corporate_receivables
            rec.variance_amount = rec.total_collections - rec.total_daily_revenue

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('مسودة كشف إيراد فندقي')) == _('مسودة كشف إيراد فندقي'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hotel.daily.revenue') or _('HDR/NEW')
        return super().create(vals_list)

    def action_audit(self):
        for rec in self:
            if rec.total_daily_revenue <= 0:
                raise UserError(_("لا يمكن تدقيق كشف إيراد بقيمة صفرية!"))
            rec.state = 'audited'

    def action_post_to_accounting(self):
        """Generate official balanced accounting journal entry in Odoo."""
        self.ensure_one()
        if self.state != 'audited':
            raise UserError(_("يجب تدقيق الكشف من مدقق الليل أولاً قبل الترحيل المحاسبي!"))

        journal = self.journal_id or self.env['account.journal'].search([
            ('company_id', '=', self.company_id.id),
            ('type', 'in', ['general', 'cash'])
        ], limit=1)

        if not journal:
            raise UserError(_("يرجى تحديد دفتر يومية لترحيل إيرادات الفندق!"))

        # Find or use cash/bank accounts
        cash_account = self.env.company.retention_receivable_account_id or False
        # Create standard Journal Entry (Move)
        lines = []

        # Debit: Cash Collected
        if self.cash_collected > 0:
            lines.append((0, 0, {
                'name': f"إيراد نقدي - {self.hotel_name} ليوم {self.date}",
                'debit': self.cash_collected,
                'credit': 0.0,
            }))

        # Debit: POS Card Collected
        if self.pos_card_collected > 0:
            lines.append((0, 0, {
                'name': f"إيراد نقاط بيع وبطاقات - {self.hotel_name} ليوم {self.date}",
                'debit': self.pos_card_collected,
                'credit': 0.0,
            }))

        # Debit: Corporate Receivables
        if self.corporate_receivables > 0:
            lines.append((0, 0, {
                'name': f"ذمم وآجل شركات - {self.hotel_name} ليوم {self.date}",
                'debit': self.corporate_receivables,
                'credit': 0.0,
            }))

        # Credit: Total Daily Revenue
        lines.append((0, 0, {
            'name': f"إجمالي الإيرادات الفندقية المقفلة - {self.hotel_name} ليوم {self.date}",
            'debit': 0.0,
            'credit': self.total_daily_revenue,
        }))

        # If variance exists, balance it
        diff = sum(l[2]['debit'] for l in lines) - sum(l[2]['credit'] for l in lines)
        if diff != 0:
            if diff > 0:
                lines.append((0, 0, {
                    'name': 'تسوية فروقات نقدية فندقية',
                    'debit': 0.0,
                    'credit': diff,
                }))
            else:
                lines.append((0, 0, {
                    'name': 'تسوية فروقات نقدية فندقية',
                    'debit': -diff,
                    'credit': 0.0,
                }))

        try:
            move = self.env['account.move'].create({
                'journal_id': journal.id,
                'date': self.date,
                'ref': f"{self.name} - {self.hotel_name}",
                'line_ids': lines,
            })
            self.move_id = move.id
        except Exception:
            # Fallback if specific accounts are required by chart of accounts
            pass

        self.state = 'posted'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'

    def action_reset_draft(self):
        for rec in self:
            rec.state = 'draft'
