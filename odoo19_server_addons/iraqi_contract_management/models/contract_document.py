from odoo import models, fields, api, _


class DirectSupplyDocument(models.Model):
    _name = 'direct.supply.document'
    _description = 'مستندات وأرشيف العقد والمناقصة (Contract Document Archive)'
    _order = 'doc_date desc, id desc'

    name = fields.Char(
        string='عنوان / اسم المستند',
        required=True,
        help='مثال: كتاب الإحالة والمصادقة، وثيقة العقد الموقعة، بوليصة الشحن، محضر الفحص الفني.'
    )
    contract_id = fields.Many2one(
        'direct.supply.contract',
        string='العقد المرتبط',
        required=True,
        ondelete='cascade',
        index=True
    )
    doc_type = fields.Selection([
        ('award_letter', 'كتاب الإحالة والمصادقة'),
        ('signed_contract', 'العقد الموقع وجدول المواصفات'),
        ('bank_guarantee', 'خطاب الضمان المصرفي (كفالة 5% / سلفة)'),
        ('purchase_order', 'أمر الشراء / الاعتماد المستندي LC'),
        ('shipping_bl', 'بوليصة الشحن وشهادة المنشأ'),
        ('inspection_cert', 'شهادة الفحص والسيطرة النوعية'),
        ('delivery_handover', 'محضر الاستلام والتجهيز الموقعي'),
        ('tax_clearance', 'كتاب براءة الذمة الضريبية الرسمية'),
        ('payment_receipt', 'سند ووصل تسديد المبلغ / إشعار الصرف'),
        ('correspondence', 'كتب المراسلات والمخاطبات الرسمية'),
        ('other', 'مستندات ووثائق أخرى')
    ], string='نوع المستند والوثيقة', required=True, default='signed_contract')

    doc_number = fields.Char(
        string='رقم الكتاب / الوثيقة الرسمية',
        help='العدد أو الرقم الإشاري الصادر به الكتاب الرسمي.'
    )
    doc_date = fields.Date(
        string='تاريخ الكتاب / الوثيقة',
        default=fields.Date.context_today,
        required=True
    )
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'direct_supply_document_ir_attachment_rel',
        'document_id',
        'attachment_id',
        string='الملفات والمرفقات (يمكن إضافة أكثر من مرفق)'
    )
    attachment_count = fields.Integer(
        string='عدد المرفقات',
        compute='_compute_attachment_count'
    )
    notes = fields.Text(string='تفاصيل وبيان المستند')

    @api.depends('attachment_ids')
    def _compute_attachment_count(self):
        for doc in self:
            doc.attachment_count = len(doc.attachment_ids)
