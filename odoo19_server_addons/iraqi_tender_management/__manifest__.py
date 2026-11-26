{
    'name': 'إدارة المناقصات والعطاءات (المشاركة والتسعير) - العراق',
    'version': '19.0.1.0.0',
    'category': 'Operations/Tenders',
    'summary': 'نظام متكامل لإدارة ملفات المشاركة في المناقصات والدعوات المباشرة، دراسة وتكليف جداول الكميات، تسعير العطاءات، كفالات الدخول (Bid Bond 1%)، تحليل المنافسين والإحالة',
    'description': """
نظام إدارة المشاركة في المناقصات والعطاءات - العراق (Bidding & Tendering Management)
=====================================================================================
يختص هذا النظام بشركات المقاولات والتجهيز لدراسة والمشاركة في المناقصات:
- تسجيل المناقصات والدعوات المباشرة المستلمة وتتبع مواعيد الغلق وفتح المظاريف.
- دراسة وتسعير جداول الكميات (BOQ Pricing) مع احتساب الكلفة التقديرية وهامش الربح.
- إدارة كفالات دخول المناقصة (Bid Bond 1%) وتتبع صلاحيتها واستردادها.
- قائمة تدقيق المستمسكات والوثائق الرسمية المطلوبة للعطاء (Checklist).
- رصد وتحليل أسعار المنافسين عند فتح المظاريف وتحديد الترتيب المالي.
- توثيق الإحالة والمصادقة أو أسباب عدم الفوز والدروس المستفادة.
- الربط الذكي مع موديول إدارة العقود (إنشاء عقد التجهيز/المقاولة بنقرة واحدة عند الفوز).
    """,
    'author': 'SAG Group Contracting & Legal Systems',
    'website': 'https://sag2.group',
    'depends': [
        'base',
        'mail',
        'product',
        'hr',
    ],
    'data': [
        'security/tender_security.xml',
        'security/ir.model.access.csv',
        'data/tender_sequence_data.xml',
        'views/tender_announcement_views.xml',
        'views/tender_menus.xml',
        'reports/reports.xml',
        'reports/report_tender_announcement_template.xml',
        'reports/report_tender_evaluation_template.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
