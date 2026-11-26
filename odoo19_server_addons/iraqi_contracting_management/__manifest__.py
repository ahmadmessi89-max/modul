# -*- coding: utf-8 -*-
{
    'name': 'Iraqi Contracting & Project Costing Management',
    'name_ar': 'إدارة المقاولات وحسابات المشاريع الإنشائية العراقية',
    'version': '19.0.1.0.0',
    'category': 'Construction / Contracting',
    'summary': 'Iraqi Contracting Management: BOQ (جدول الكميات والتسعير), IPC Progress Invoicing (الذرعات والسلف المنجزة), Variation Orders (أوامر الغيار), Retention (أمانات الصيانة), Site Material Deliveries (إدخال مخزني موقعي), Site Petty Cash (ذمة المهندس), Interactive Dashboard & Reports',
    'description': """
نظام إدارة المقاولات والإنشاءات وفق المعايير العراقية - Odoo 19
============================================================
هذا الموديول مخصص لشركات المقاولات العامة والإنشاءات الهندسية في العراق:
- جدول الكميات والتسعير (Bill of Quantities - WBS) مع مؤشرات التحذير ونسب الاستهلاك.
- إدارة أوامر الغيار (Variation Orders) وتحديث الإيرادات والموازنات تحليلياً.
- نظام السلف المنجزة والذرعات الشهرية (Interim Payment Certificates - IPC) لرب العمل والمقاولين الثانويين.
- المعالجة المحاسبية التلقائية لاسترداد السلفة التشغيلية (Advance Payment Recovery) واستقطاعات الصيانة والأمانات النظامية (Retention).
- إدخال مخزني موقعي (Site Material Deliveries) وتتبع المواد في مخازن المواقع.
- سلفة نقدية موقعية / ذمة المهندس (Site Petty Cash) لمتابعة النثريات ووصولات الصرف.
- الرقابة التكاليفية ثلاثية الأبعاد (Multi-Dimensional Analytic Distribution).
- لوحة متابعة تفاعلية (Interactive Kanban & Dashboard) للمشاريع الإنشائية.
- رقابة أوامر الشراء (Purchase Orders) ومنع تجاوز ميزانية البنود مع تنبيهات رقابية عراقية معتمدة.
- تقارير رسمية QWeb PDF: كشف الذرعة الدورية، تقرير انحراف موازنة الكميات، وكشف موقف أوامر الغيار.
    """,
    'author': 'Senior Odoo 19 Technical Architect',
    'website': 'https://www.odoo.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'project',
        'account',
        'purchase',
        'stock',
        'analytic',
        'hr',
    ],
    'data': [
        # Security
        'security/contracting_security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/analytic_plans_data.xml',
        'data/contracting_sequence_data.xml',
        
        # Views
        'views/contracting_subcontract_views.xml',
        'views/contracting_material_requisition_views.xml',
        'views/contracting_residential_compound_views.xml',
        'views/hotel_daily_revenue_views.xml',
        'views/contracting_cash_flow_views.xml',
        'views/contracting_boq_views.xml',
        'views/contracting_variation_order_views.xml',
        'views/contracting_interim_payment_views.xml',
        'views/contracting_site_delivery_views.xml',
        'views/contracting_petty_cash_views.xml',
        'views/purchase_order_views.xml',
        'views/project_project_views.xml',
        'views/res_config_settings_views.xml',
        'views/contracting_menus.xml',
        
        # Reports
        'reports/reports.xml',
        'reports/report_ipc_template.xml',
        'reports/report_boq_template.xml',
        'reports/report_boq_variance_template.xml',
        'reports/report_vo_summary_template.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
