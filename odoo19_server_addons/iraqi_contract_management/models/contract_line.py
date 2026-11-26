from odoo import models, fields, api, _


class DirectSupplyContractLine(models.Model):
    _name = 'direct.supply.contract.line'
    _description = 'بند مواد عقد التجهيز والمقاولة (Contract Item Line)'
    _order = 'sequence, id'

    sequence = fields.Integer(string='التسلسل', default=10)
    contract_id = fields.Many2one(
        'direct.supply.contract',
        string='العقد المرتبط',
        required=True,
        ondelete='cascade',
        index=True
    )
    product_id = fields.Many2one(
        'product.product',
        string='المادة / الصنف'
    )
    name = fields.Text(
        string='المواصفات الفنية وتفاصيل المادة',
        required=True,
        help='المواصفات الهندسية الدقيقة، بلد المنشأ، الموديل، والمعايير المعتمدة.'
    )
    quantity = fields.Float(
        string='الكمية التعاقدية المطلوبة',
        digits='Product Unit of Measure',
        required=True,
        default=1.0
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='وحدة القياس',
        required=True,
        default=lambda self: self.env.ref('uom.product_uom_unit', raise_if_not_found=False)
    )
    unit_price = fields.Monetary(
        string='سعر شراء الوحدة',
        currency_field='currency_id',
        required=True,
        default=0.0
    )
    subtotal = fields.Monetary(
        string='إجمالي كلفة المادة',
        currency_field='currency_id',
        compute='_compute_subtotal',
        store=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='العملة',
        related='contract_id.currency_id',
        store=True,
        readonly=True
    )

    # Delivery Tracking
    delivered_quantity = fields.Float(
        string='الكمية المجهزة والمستلمة',
        digits='Product Unit of Measure',
        default=0.0
    )
    remaining_quantity = fields.Float(
        string='الكمية المتبقية للتجهيز',
        digits='Product Unit of Measure',
        compute='_compute_remaining_quantity',
        store=True
    )
    delivery_status = fields.Selection([
        ('pending', 'لم يتم التجهيز'),
        ('partial', 'تجهيز جزئي'),
        ('delivered', 'مجهز بالكامل')
    ], string='موقف التجهيز', compute='_compute_remaining_quantity', store=True)

    notes = fields.Char(string='ملاحظات فنية / محضر الفحص')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.display_name
            self.uom_id = self.product_id.uom_id.id
            self.unit_price = self.product_id.standard_price

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_price

    @api.depends('quantity', 'delivered_quantity')
    def _compute_remaining_quantity(self):
        for line in self:
            line.remaining_quantity = max(0.0, line.quantity - line.delivered_quantity)
            if line.delivered_quantity <= 0:
                line.delivery_status = 'pending'
            elif line.delivered_quantity >= line.quantity:
                line.delivery_status = 'delivered'
            else:
                line.delivery_status = 'partial'
