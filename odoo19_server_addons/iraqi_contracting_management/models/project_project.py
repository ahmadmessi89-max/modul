# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ProjectProject(models.Model):
    _inherit = 'project.project'

    # Iraqi Contracting Project Identity & Contract Details
    contract_ref = fields.Char(
        string='رقم العقد الإنشائي والمناقصة',
        tracking=True,
        help='رقم العقد الرسمي المسجل لدى رب العمل أو الوزارة.'
    )
    contract_sign_date = fields.Date(
        string='تاريخ توقيع العقد',
        tracking=True
    )
    site_handover_date = fields.Date(
        string='تاريخ المباشرة / استلام الموقع',
        tracking=True,
        help='تاريخ محضر استلام الموقع وبدء احتساب المدة العقدية.'
    )
    contract_duration_days = fields.Integer(
        string='مدة العقد الإنشائي (يوم تقويمي)',
        default=365,
        tracking=True
    )
    site_engineer_ids = fields.Many2many(
        'res.users',
        'project_site_engineer_rel',
        'project_id',
        'user_id',
        string='مهندسو الموقع المشرفون',
        help='المهندسون الموقعين المخولون بإعداد وتدقيق الذرعات ومتابعة بنود جدول الكميات.'
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='الحساب التحليلي للمشروع',
        help='الحساب التحليلي المرتبط بهذا المشروع الإنشائي لتتبع التكاليف والإيرادات.'
    )

    # Financial Contract Valuations
    contract_value_tender = fields.Monetary(
        string='قيمة الإحالة / العقد الأصلية',
        currency_field='currency_id',
        compute='_compute_contract_valuation',
        store=True,
        tracking=True,
        help='إجمالي قيمة جدول الكميات والتسعير التعاقدي الأصلي.'
    )
    vo_total_revenue = fields.Monetary(
        string='إجمالي أوامر الغيار المصادق عليها (+/-)',
        currency_field='currency_id',
        compute='_compute_contract_valuation',
        store=True,
        help='صافي قيمة أوامر الغيار المعتمدة من رب العمل.'
    )
    contract_value_current = fields.Monetary(
        string='قيمة العقد الحالية المعدلة',
        currency_field='currency_id',
        compute='_compute_contract_valuation',
        store=True,
        tracking=True,
        help='قيمة العقد بعد تطبيق أوامر الغيار = القيمة الأصلية + أوامر الغيار.'
    )

    # Advance Payment (السلفة الأولية / التشغيلية)
    advance_payment_amount = fields.Monetary(
        string='مبلغ السلفة التشغيلية المستلمة',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
        help='إجمالي مبلغ السلفة التشغيلية الممنوحة في بداية المشروع.'
    )
    advance_payment_recovered = fields.Monetary(
        string='إجمالي السلفة التشغيلية المستردة',
        currency_field='currency_id',
        compute='_compute_advance_and_retention',
        store=True,
        help='إجمالي المبالغ المستقطعة لإطفاء السلفة التشغيلية عبر السلف المنجزة.'
    )
    advance_payment_balance = fields.Monetary(
        string='المتبقي من السلفة التشغيلية',
        currency_field='currency_id',
        compute='_compute_advance_and_retention',
        store=True,
        help='الرصيد المتبقي بذمة المشروع من السلفة التشغيلية.'
    )

    # Retention Money (أمانات الصيانة والاستقطاعات النظامية)
    retention_balance_total = fields.Monetary(
        string='إجمالي أمانات الصيانة المحتجزة',
        currency_field='currency_id',
        compute='_compute_advance_and_retention',
        store=True,
        help='إجمالي المبالغ المحتجزة كأمانات صيانة وحسن تنفيذ حتى التسليم النهائي.'
    )

    # Project Cost & Execution Tracking
    total_boq_estimated_budget = fields.Monetary(
        string='إجمالي موازنة التكلفة التقديرية للبنود',
        currency_field='currency_id',
        compute='_compute_boq_analytics',
        store=True
    )
    total_committed_costs = fields.Monetary(
        string='إجمالي الالتزامات المحجوزة (أوامر الشراء)',
        currency_field='currency_id',
        compute='_compute_boq_analytics',
        store=True
    )
    total_actual_costs = fields.Monetary(
        string='إجمالي التكاليف الفعلية المصروفة',
        currency_field='currency_id',
        compute='_compute_boq_analytics',
        store=True
    )
    total_executed_revenue = fields.Monetary(
        string='إجمالي إيرادات الأعمال المنجزة (الذرعات)',
        currency_field='currency_id',
        compute='_compute_advance_and_retention',
        store=True
    )
    overall_project_progress = fields.Float(
        string='نسبة الإنجاز المالي التراكمي للمشروع (%)',
        compute='_compute_overall_progress',
        store=True
    )

    # Relational Fields
    boq_line_ids = fields.One2many(
        'contracting.project.boq',
        'project_id',
        string='جدول الكميات والتسعير (BOQ)'
    )
    variation_order_ids = fields.One2many(
        'contracting.variation.order',
        'project_id',
        string='أوامر الغيار (Variation Orders)'
    )
    interim_payment_ids = fields.One2many(
        'contracting.interim.payment',
        'project_id',
        string='الذرعات والسلف المنجزة (IPCs)'
    )
    site_delivery_ids = fields.One2many(
        'contracting.site.delivery',
        'project_id',
        string='أذونات الإدخال المخزني الموقعي'
    )
    petty_cash_ids = fields.One2many(
        'contracting.petty.cash',
        'project_id',
        string='سلف نقدية موقعية / ذمة المهندس'
    )

    # Smart Button Counts
    boq_count = fields.Integer(
        string='عدد بنود جدول الكميات',
        compute='_compute_smart_counts'
    )
    vo_count = fields.Integer(
        string='عدد أوامر الغيار',
        compute='_compute_smart_counts'
    )
    ipc_client_count = fields.Integer(
        string='عدد سلف رب العمل',
        compute='_compute_smart_counts'
    )
    ipc_sub_count = fields.Integer(
        string='عدد ذرعات المقاولين الثانويين',
        compute='_compute_smart_counts'
    )
    site_delivery_count = fields.Integer(
        string='عدد أذونات الإدخال الموقعي',
        compute='_compute_smart_counts'
    )
    petty_cash_count = fields.Integer(
        string='عدد كشوفات السلفة النقدية',
        compute='_compute_smart_counts'
    )

    @api.depends('boq_line_ids.total_tender_amount', 'variation_order_ids.state', 'variation_order_ids.total_revenue_change')
    def _compute_contract_valuation(self):
        for project in self:
            tender_val = sum(project.boq_line_ids.mapped('total_tender_amount'))
            approved_vos = project.variation_order_ids.filtered(lambda vo: vo.state == 'client_approved')
            vo_val = sum(approved_vos.mapped('total_revenue_change'))
            project.contract_value_tender = tender_val
            project.vo_total_revenue = vo_val
            project.contract_value_current = tender_val + vo_val

    @api.depends('interim_payment_ids.state', 'interim_payment_ids.advance_deduction_amount',
                 'interim_payment_ids.retention_amount', 'interim_payment_ids.current_gross_amount',
                 'advance_payment_amount')
    def _compute_advance_and_retention(self):
        for project in self:
            approved_ipcs = project.interim_payment_ids.filtered(
                lambda ipc: ipc.state in ['approved', 'invoiced'] and ipc.ipc_type == 'client'
            )
            recovered = sum(approved_ipcs.mapped('advance_deduction_amount'))
            retention = sum(approved_ipcs.mapped('retention_amount'))
            executed_rev = sum(approved_ipcs.mapped('current_gross_amount'))

            project.advance_payment_recovered = recovered
            project.advance_payment_balance = max(0.0, project.advance_payment_amount - recovered)
            project.retention_balance_total = retention
            project.total_executed_revenue = executed_rev

    @api.depends('boq_line_ids.total_estimated_budget', 'boq_line_ids.committed_cost_amount', 'boq_line_ids.actual_cost_amount')
    def _compute_boq_analytics(self):
        for project in self:
            project.total_boq_estimated_budget = sum(project.boq_line_ids.mapped('total_estimated_budget'))
            project.total_committed_costs = sum(project.boq_line_ids.mapped('committed_cost_amount'))
            project.total_actual_costs = sum(project.boq_line_ids.mapped('actual_cost_amount'))

    @api.depends('total_executed_revenue', 'contract_value_current')
    def _compute_overall_progress(self):
        for project in self:
            if project.contract_value_current > 0:
                project.overall_project_progress = (project.total_executed_revenue / project.contract_value_current) * 100.0
            else:
                project.overall_project_progress = 0.0

    @api.depends('boq_line_ids', 'variation_order_ids', 'interim_payment_ids', 'site_delivery_ids', 'petty_cash_ids')
    def _compute_smart_counts(self):
        for project in self:
            project.boq_count = len(project.boq_line_ids)
            project.vo_count = len(project.variation_order_ids)
            project.ipc_client_count = len(project.interim_payment_ids.filtered(lambda i: i.ipc_type == 'client'))
            project.ipc_sub_count = len(project.interim_payment_ids.filtered(lambda i: i.ipc_type == 'subcontractor'))
            project.site_delivery_count = len(project.site_delivery_ids)
            project.petty_cash_count = len(project.petty_cash_ids)

    # Smart Button Action Methods
    def action_view_boq(self):
        self.ensure_one()
        return {
            'name': _('جدول الكميات والتسعير (BOQ) - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'contracting.project.boq',
            'view_mode': 'list,form,pivot,graph',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_variation_orders(self):
        self.ensure_one()
        return {
            'name': _('أوامر الغيار (Variation Orders) - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'contracting.variation.order',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_client_ipcs(self):
        self.ensure_one()
        return {
            'name': _('السلف المنجزة والذرعات لرب العمل - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'contracting.interim.payment',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id), ('ipc_type', '=', 'client')],
            'context': {'default_project_id': self.id, 'default_ipc_type': 'client'},
        }

    def action_view_subcontractor_ipcs(self):
        self.ensure_one()
        return {
            'name': _('ذرعات وسلف المقاولين الثانويين - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'contracting.interim.payment',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id), ('ipc_type', '=', 'subcontractor')],
            'context': {'default_project_id': self.id, 'default_ipc_type': 'subcontractor'},
        }

    def action_view_site_deliveries(self):
        self.ensure_one()
        return {
            'name': _('أذونات الإدخال المخزني الموقعي - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'contracting.site.delivery',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_petty_cash(self):
        self.ensure_one()
        return {
            'name': _('كشوفات السلفة النقدية الموقعية (ذمة المهندس) - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'contracting.petty.cash',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_quick_new_ipc(self):
        self.ensure_one()
        return {
            'name': _('إعداد سلفة منجزة / ذرعة شهرية جديدة'),
            'type': 'ir.actions.act_window',
            'res_model': 'contracting.interim.payment',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_project_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_ipc_type': 'client',
            },
        }

    def action_quick_new_vo(self):
        self.ensure_one()
        return {
            'name': _('إعداد أمر غيار جديد'),
            'type': 'ir.actions.act_window',
            'res_model': 'contracting.variation.order',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_project_id': self.id,
            },
        }
