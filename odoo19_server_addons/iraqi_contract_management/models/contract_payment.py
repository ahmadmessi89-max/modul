from odoo import models, fields, api, _


class DirectSupplyPaymentSchedule(models.Model):
    _name = 'direct.supply.payment.schedule'
    _description = 'جدول دفعات العقد وتنبيهات الاستحقاق (Contract Payment Milestone)'
    _order = 'due_date, id'

    contract_id = fields.Many2one(
        'direct.supply.contract',
        string='العقد المرتبط',
        required=True,
        ondelete='cascade',
        index=True
    )
    name = fields.Char(
        string='بيان / اسم الدفعة',
        required=True,
        help='مثال: الدفعة الأولى (السلفة التشغيلية 10%)، الدفعة الثانية عند الشحن، الدفعة الختامية بعد التسليم.'
    )
    percentage = fields.Float(
        string='النسبة من قيمة العقد (%)',
        default=0.0
    )
    amount = fields.Monetary(
        string='مبلغ الدفعة المستحق',
        currency_field='currency_id',
        required=True,
        default=0.0
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='العملة',
        related='contract_id.currency_id',
        store=True,
        readonly=True
    )
    due_date = fields.Date(
        string='تاريخ الاستحقاق التعاقدي',
        required=True,
        help='الموعد المحدد لدفع أو استلام هذه الدفعة.'
    )
    actual_payment_date = fields.Date(
        string='تاريخ التسديد الفعلي',
        help='تاريخ إيداع أو صرف المبلغ فعلياً.'
    )
    state = fields.Selection([
        ('pending', 'قيد الانتظار'),
        ('due_soon', 'مستحقة قريباً (خلال 7 أيام)'),
        ('overdue', 'متأخرة عن موعد الاستحقاق'),
        ('paid', 'تم التسديد بالكامل'),
        ('cancelled', 'ملغاة')
    ], string='حالة الدفعة', default='pending')

    payment_reference = fields.Char(
        string='رقم الصك / إشعار التحويل البنكي',
        help='رقم الإشعار أو السند المالي الدال على التسديد.'
    )
    notes = fields.Text(string='ملاحظات وشروط الدفعة')

    @api.onchange('percentage', 'contract_id.contract_tender_value')
    def _onchange_percentage(self):
        if self.percentage and self.contract_id.contract_tender_value:
            self.amount = (self.contract_id.contract_tender_value * (self.percentage / 100.0))

    def action_mark_as_paid(self):
        self.ensure_one()
        if not self.actual_payment_date:
            self.actual_payment_date = fields.Date.context_today(self)
        self.write({'state': 'paid'})

    def action_reset_pending(self):
        self.ensure_one()
        self.write({'state': 'pending'})
