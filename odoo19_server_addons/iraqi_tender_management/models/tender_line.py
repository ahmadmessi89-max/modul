from odoo import models, fields, api, _


class IraqiTenderLine(models.Model):
    _name = 'iraqi.tender.line'
    _description = 'بند تسعير وجدول كميات العطاء (Tender BOQ Pricing Line)'
    _order = 'sequence, id'

    sequence = fields.Integer(string='التسلسل', default=10)
    tender_id = fields.Many2one(
        'iraqi.tender.announcement',
        string='المناقصة المرتبطة',
        required=True,
        ondelete='cascade',
        index=True
    )
    product_id = fields.Many2one(
        'product.product',
        string='المادة / الصنف',
        help='اختياري لربط البند ببطاقة صنف معرفة في المخازن.'
    )
    name = fields.Char(
        string='بيان المادة والمواصفات الفنية المطلوبة',
        required=True,
        help='المواصفات الفنية القياسية للمادة أو الفقرة كما وردت في كراس الشروط.'
    )
    quantity = fields.Float(
        string='الكمية المطلوبة',
        required=True,
        default=1.0
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='وحدة القياس',
        help='متر، طن، عدد، كغم، مقطوعية، إلخ.'
    )

    # Costing & Internal Estimation (الكلفة الداخلية التقديرية)
    cost_price = fields.Monetary(
        string='كلفة الشراء / التنفيذ التقديرية (للوحدة)',
        currency_field='currency_id',
        default=0.0,
        help='كلفة المادة أو الفقرة علينا (سعر المصنع/المورد + شحن/تنفيذ تقريبي).'
    )
    total_cost = fields.Monetary(
        string='إجمالي الكلفة التقديرية',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True
    )

    # Offered Bid Price (سعر العطاء المقدم للعميل)
    unit_price = fields.Monetary(
        string='سعر الوحدة المقدم في العطاء (عرض السعر)',
        currency_field='currency_id',
        required=True,
        default=0.0,
        help='السعر الفردي للوحدة الذي سيتم تقديمه في العطاء المالي للجهة المعلنة.'
    )
    subtotal = fields.Monetary(
        string='إجمالي مبلغ البند في العطاء',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True
    )

    # Margin Analysis
    margin_amount = fields.Monetary(
        string='هامش الربح للبند',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True
    )
    margin_percentage = fields.Float(
        string='نسبة الربح (%)',
        compute='_compute_totals',
        store=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='العملة',
        related='tender_id.currency_id',
        store=True,
        readonly=True
    )
    notes = fields.Char(string='ملاحظات العرض والمورد المقترح')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.display_name
            self.uom_id = self.product_id.uom_id.id
            if self.product_id.standard_price:
                self.cost_price = self.product_id.standard_price
            if self.product_id.lst_price:
                self.unit_price = self.product_id.lst_price

    @api.depends('quantity', 'cost_price', 'unit_price')
    def _compute_totals(self):
        for line in self:
            line.total_cost = line.quantity * line.cost_price
            line.subtotal = line.quantity * line.unit_price
            line.margin_amount = line.subtotal - line.total_cost
            if line.total_cost > 0:
                line.margin_percentage = (line.margin_amount / line.total_cost) * 100.0
            else:
                line.margin_percentage = 100.0 if line.subtotal > 0 else 0.0
