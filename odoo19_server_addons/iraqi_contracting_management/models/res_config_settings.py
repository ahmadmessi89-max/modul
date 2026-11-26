# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    retention_receivable_account_id = fields.Many2one(
        'account.account',
        string='حساب أمانات الصيانة المدينة (رب العمل)',
        help='الحساب المالي المستخدم لتسجيل استقطاعات الصيانة والأمانات النظامية المحتجزة لدى رب العمل في السلف المنجزة.'
    )
    retention_payable_account_id = fields.Many2one(
        'account.account',
        string='حساب أمانات الصيانة الدائنة (المقاولين الثانويين)',
        help='الحساب المالي المستخدم لتسجيل تأمينات الصيانة المحتجزة على المقاولين الثانويين لحين التسليم النهائي.'
    )
    tax_retention_payable_account_id = fields.Many2one(
        'account.account',
        string='حساب الأمانات الضريبية المستقطعة (الهيئة العامة للضرائب)',
        help='الحساب المالي لتسجيل الأمانات الضريبية المحتجزة من دفعات مقاولي الباطن لحين تزويد براءة الذمة.'
    )
    advance_payment_account_id = fields.Many2one(
        'account.account',
        string='حساب السلفة التشغيلية / الأولية',
        help='الحساب الوسيط لتسجيل السلفة الأولية الممنوحة للمشروع واستردادها تدريجياً عبر السلف المنجزة.'
    )
    contracting_retention_percent = fields.Float(
        string='نسبة استقطاع أمانات الصيانة الافتراضية (%)',
        default=10.0,
        help='النسبة الافتراضية المحددة في العقود الحكومية العراقية لأمانات الصيانة وحسن التنفيذ (غالباً 5% أو 10%).'
    )
    contracting_tax_deduction_percent = fields.Float(
        string='نسبة الاستقطاع الضريبي الافتراضية (%)',
        default=2.7,
        help='نسبة الأمانات الضريبية القانونية على المقاولات والتجهيز (عادة 2.7% إلى 3.3%).'
    )
    contracting_advance_deduction_percent = fields.Float(
        string='نسبة استرداد السلفة التشغيلية الافتراضية (%)',
        default=10.0,
        help='نسبة الاستقطاع المعتمدة من كل سلفة منجزة لإطفاء السلفة التشغيلية حتى استردادها بالكامل.'
    )
    analytic_plan_projects_id = fields.Many2one(
        'account.analytic.plan',
        string='خطة المشاريع الإنشائية',
        help='البُعد التحليلي الأول: مستوى المشروع الإنشائي.'
    )
    analytic_plan_boq_packages_id = fields.Many2one(
        'account.analytic.plan',
        string='خطة حزم عمل جدول الكميات',
        help='البُعد التحليلي الثاني: حزم وبنود الأعمال التخصصية (أعمال ترابية، هياكل، إنهاءات، MEP).'
    )
    analytic_plan_cost_elements_id = fields.Many2one(
        'account.analytic.plan',
        string='خطة عناصر التكلفة',
        help='البُعد التحليلي الثالث: التبويب النوعي للتكلفة (مواد، مقاولين ثانويين، آليات، أجور يوميات).'
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    retention_receivable_account_id = fields.Many2one(
        related='company_id.retention_receivable_account_id',
        readonly=False,
        string='حساب أمانات الصيانة المدينة (رب العمل)'
    )
    retention_payable_account_id = fields.Many2one(
        related='company_id.retention_payable_account_id',
        readonly=False,
        string='حساب أمانات الصيانة الدائنة (المقاولين الثانويين)'
    )
    tax_retention_payable_account_id = fields.Many2one(
        related='company_id.tax_retention_payable_account_id',
        readonly=False,
        string='حساب الأمانات الضريبية المستقطعة (الهيئة العامة للضرائب)'
    )
    advance_payment_account_id = fields.Many2one(
        related='company_id.advance_payment_account_id',
        readonly=False,
        string='حساب السلفة التشغيلية / الأولية'
    )
    contracting_retention_percent = fields.Float(
        related='company_id.contracting_retention_percent',
        readonly=False,
        string='نسبة استقطاع أمانات الصيانة الافتراضية (%)'
    )
    contracting_tax_deduction_percent = fields.Float(
        related='company_id.contracting_tax_deduction_percent',
        readonly=False,
        string='نسبة الاستقطاع الضريبي الافتراضية (%)'
    )
    contracting_advance_deduction_percent = fields.Float(
        related='company_id.contracting_advance_deduction_percent',
        readonly=False,
        string='نسبة استرداد السلفة التشغيلية الافتراضية (%)'
    )
    analytic_plan_projects_id = fields.Many2one(
        related='company_id.analytic_plan_projects_id',
        readonly=False,
        string='خطة المشاريع الإنشائية'
    )
    analytic_plan_boq_packages_id = fields.Many2one(
        related='company_id.analytic_plan_boq_packages_id',
        readonly=False,
        string='خطة حزم عمل جدول الكميات'
    )
    analytic_plan_cost_elements_id = fields.Many2one(
        related='company_id.analytic_plan_cost_elements_id',
        readonly=False,
        string='خطة عناصر التكلفة'
    )
