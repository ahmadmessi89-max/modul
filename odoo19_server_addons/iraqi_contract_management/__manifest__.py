{
    'name': 'إدارة العقود والتجهيز المباشر - العراق',
    'version': '19.0.1.0.0',
    'category': 'Operations/Contracts',
    'summary': 'نظام متكامل لإدارة عقود التجهيز المباشر، خطابات الضمان المصرفية (5%)، التكاليف، الغرامات التأخيرية، والاستقطاعات الضريبية وفق المعايير العراقية',
    'description': """
نظام إدارة العقود والتجهيز المباشر والمقاولات - العراق
======================================================
يختص هذا النظام بمرحلة تنفيذ العقد وما بعد الإحالة (Post-Contract Execution Phase):
- نافذة شاملة لعقود التجهيز المباشر والمقاولات مع الربط التكاملي المباشر بموديول المناقصات.
- خطابات الضمان المصرفية (كفالة حسن التنفيذ 5%، كفالة السلفة التشغيلية 10%).
- هيكل التكاليف (المواد، الشحن الدولي، التخليص الجمركي، مركز الكلفة، المصروف الفعلي، والأرباح).
- احتساب الغرامات التأخيرية والمدد التعويضية وفق تعليمات العقود الحكومية العراقية رقم 2 لسنة 2014.
- الاستقطاعات الضريبية (أمانات الهيئة العامة للضرائب) وتتبع براءة الذمة.
- محاضر الاستلام الأولي، فترات الصيانة والضمان، والاستلام النهائي.
- جدول الدفعات وتنبيهات الاستحقاق.
- أرشيف ومرفقات متعددة لكل وثيقة.
- تقارير PDF طباعية احترافية.
    """,
    'author': 'SAG Group Contracting & Legal Systems',
    'website': 'https://sag2.group',
    'depends': [
        'base',
        'mail',
        'analytic',
        'account',
        'product',
        'hr',
        'iraqi_tender_management',
    ],
    'data': [
        'security/contract_security.xml',
        'security/ir.model.access.csv',
        'data/contract_sequence_data.xml',
        'views/contract_document_views.xml',
        'views/contract_payment_views.xml',
        'views/contract_supply_views.xml',
        'views/tender_announcement_inherit_views.xml',
        'views/contract_menus.xml',
        'reports/reports.xml',
        'reports/report_direct_contract_template.xml',
        'reports/report_direct_contract_financial_template.xml',
        'reports/report_direct_contract_handover_template.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
