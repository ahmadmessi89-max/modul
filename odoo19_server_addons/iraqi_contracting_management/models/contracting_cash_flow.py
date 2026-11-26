# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ContractingCashFlow(models.Model):
    _name = 'contracting.cash.flow'
    _description = 'متابعة وتوقعات التدفقات النقدية للمشاريع (Project & Group Cash Flow Engine)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc, id desc'

    name = fields.Char(
        string='بيان / فترة التدفق النقدي',
        required=True,
        tracking=True,
        default=lambda self: _('كشف تدفق نقدي جديد')
    )
    project_id = fields.Many2one(
        'project.project',
        string='المشروع الإنشائي',
        help='تحديد مشروع معين أو تركه فارغاً لعرض التدفق النقدي المجمع للشركة.'
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
    date_from = fields.Date(
        string='من تاريخ',
        required=True,
        default=fields.Date.context_today
    )
    date_to = fields.Date(
        string='إلى تاريخ',
        required=True
    )

    # Cash Inflows (المقبوضات النقدية المتوقعة)
    inflow_client_ipcs = fields.Monetary(
        string='مقبوضات سلف رب العمل المتوقعة',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
        help='التحصيلات المتوقعة من سلف رب العمل المصادق عليها وشهادات الدفع.'
    )
    inflow_unit_sales = fields.Monetary(
        string='مقبوضات بيع وأقساط الوحدات السكنية',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
        help='دفعات وأقساط حجز وشراء الفلل والشقق في المجمعات السكنية.'
    )
    inflow_hotel_transfers = fields.Monetary(
        string='السيولة المحولة من إيرادات الفنادق',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
        help='السيولة اليومية المغذية للتدفق من أرباح الفنادق المقفلة.'
    )
    inflow_other = fields.Monetary(
        string='مقبوضات وإيداعات أخرى',
        currency_field='currency_id',
        default=0.0,
        tracking=True
    )
    total_inflows = fields.Monetary(
        string='إجمالي المقبوضات النقدية المتوقعة (Cash Inflows)',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
        tracking=True
    )

    # Cash Outflows (المدفوعات النقدية الملتزم بها)
    outflow_subcontractors = fields.Monetary(
        string='مستحقات مقاولي الباطن واجبة السداد',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
        help='صافي المستحقات المصادقة لمقاولي الباطن بعد تنزيل الأمانات والضرائب.'
    )
    outflow_suppliers = fields.Monetary(
        string='استحقاقات مجهزي المواد وأوامر الشراء',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
        help='دفعات موردي الإسمنت والحديد والمواد الإنشائية.'
    )
    outflow_site_petty_cash = fields.Monetary(
        string='سلف النثريات وذمم المهندسين الموقعية',
        currency_field='currency_id',
        default=0.0,
        tracking=True
    )
    outflow_salaries_wages = fields.Monetary(
        string='أجور يوميات العمال ورواتب الكادر الموقعي',
        currency_field='currency_id',
        default=0.0,
        tracking=True
    )
    outflow_other = fields.Monetary(
        string='مدفوعات ومصاريف أخرى',
        currency_field='currency_id',
        default=0.0,
        tracking=True
    )
    total_outflows = fields.Monetary(
        string='إجمالي المدفوعات والالتزامات (Cash Outflows)',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
        tracking=True
    )

    # Net Cash Flow & Liquidity Warnings
    net_cash_flow = fields.Monetary(
        string='صافي التدفق النقدي للفترة (Net Cash Flow)',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
        tracking=True,
        help='الفارق بين إجمالي المقبوضات وإجمالي المدفوعات = المقبوضات - المدفوعات.'
    )
    liquidity_status = fields.Selection([
        ('surplus', 'فائض سيولة مريح (+ Safe Surplus)'),
        ('balanced', 'متوازن ومستقر (Balanced)'),
        ('deficit', 'إنذار: فجوة سيولة وعجز متوقع (- Liquidity Deficit)')
    ], string='مؤشر الموقف المالي', compute='_compute_totals', store=True, tracking=True)

    action_recommendation = fields.Text(
        string='توصيات الإدارة المالية لمعالجة الموقف',
        compute='_compute_totals',
        store=True
    )

    state = fields.Selection([
        ('draft', 'مسودة'),
        ('confirmed', 'معتمد ومثبت للمتابعة'),
        ('closed', 'مقفل ومطابق فعلياً')
    ], string='الحالة', default='draft', tracking=True)

    @api.depends('inflow_client_ipcs', 'inflow_unit_sales', 'inflow_hotel_transfers', 'inflow_other',
                 'outflow_subcontractors', 'outflow_suppliers', 'outflow_site_petty_cash',
                 'outflow_salaries_wages', 'outflow_other')
    def _compute_totals(self):
        for rec in self:
            rec.total_inflows = (
                rec.inflow_client_ipcs + rec.inflow_unit_sales +
                rec.inflow_hotel_transfers + rec.inflow_other
            )
            rec.total_outflows = (
                rec.outflow_subcontractors + rec.outflow_suppliers +
                rec.outflow_site_petty_cash + rec.outflow_salaries_wages + rec.outflow_other
            )
            rec.net_cash_flow = rec.total_inflows - rec.total_outflows

            if rec.net_cash_flow > 5000000:
                rec.liquidity_status = 'surplus'
                rec.action_recommendation = _("الموقف المالي ممتاز. السيولة المتوقعة كافية لتغطية التزامات المواقع بدون الحاجة لتمويل خارجي.")
            elif rec.net_cash_flow >= 0:
                rec.liquidity_status = 'balanced'
                rec.action_recommendation = _("السيولة متوازنة. ينصح بجدولة دفعات المجهزين بالتوازي مع تحصيل سلف رب العمل.")
            else:
                rec.liquidity_status = 'deficit'
                rec.action_recommendation = _(
                    "تنبيه رقابي: يوجد عجز في السيولة النقدية بمقدار (%s). يوصى بتحويل سيولة من إيرادات الفنادق اليومية أو تسريع تحصيل سلف رب العمل وأقساط الوحدات."
                ) % "{:,.2f}".format(abs(rec.net_cash_flow))

    def action_auto_fill_from_system(self):
        """Auto-populate cash flow figures based on real IPCs, POs, and Hotel Revenues in date range."""
        self.ensure_one()
        # 1. Approved client IPCs
        client_ipcs = self.env['contracting.interim.payment'].search([
            ('ipc_type', '=', 'client'),
            ('state', 'in', ['approved', 'invoiced']),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to)
        ])
        if self.project_id:
            client_ipcs = client_ipcs.filtered(lambda i: i.project_id == self.project_id)
        self.inflow_client_ipcs = sum(client_ipcs.mapped('net_payable_amount'))

        # 2. Approved Subcontractor IPCs
        sub_ipcs = self.env['contracting.interim.payment'].search([
            ('ipc_type', '=', 'subcontractor'),
            ('state', 'in', ['approved', 'invoiced']),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to)
        ])
        if self.project_id:
            sub_ipcs = sub_ipcs.filtered(lambda i: i.project_id == self.project_id)
        self.outflow_subcontractors = sum(sub_ipcs.mapped('net_payable_amount'))

        # 3. Hotel revenues transfer
        hotel_entries = self.env['hotel.daily.revenue'].search([
            ('transfer_to_contracting', '=', True),
            ('state', 'in', ['audited', 'posted']),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to)
        ])
        self.inflow_hotel_transfers = sum(hotel_entries.mapped('transfer_amount'))

        # 4. Site Petty cash
        petty = self.env['contracting.petty.cash'].search([
            ('state', 'in', ['submitted', 'approved', 'settled']),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to)
        ])
        if self.project_id:
            petty = petty.filtered(lambda p: p.project_id == self.project_id)
        self.outflow_site_petty_cash = sum(petty.mapped('total_spent_amount'))

    def action_confirm(self):
        for rec in self:
            rec.state = 'confirmed'

    def action_close(self):
        for rec in self:
            rec.state = 'closed'

    def action_reset_draft(self):
        for rec in self:
            rec.state = 'draft'
