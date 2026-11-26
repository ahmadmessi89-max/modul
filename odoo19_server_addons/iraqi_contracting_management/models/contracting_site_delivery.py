# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ContractingSiteDelivery(models.Model):
    _name = 'contracting.site.delivery'
    _description = 'إدخال مخزني موقعي (Site Material Delivery Receipt)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(
        string='رقم إذن الاستلام الموقعي',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('مسودة إدخال موقعي'),
        tracking=True
    )
    delivery_type = fields.Selection([
        ('direct_purchase', 'تجهيز مباشر من مجهز / مورد إلى الموقع'),
        ('internal_transfer', 'تحويل مخزني من المستودع المركزي للموقع')
    ], string='نوع الإدخال المخزني', required=True, default='direct_purchase', tracking=True)

    project_id = fields.Many2one(
        'project.project',
        string='المشروع الإنشائي',
        required=True,
        tracking=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        related='project_id.company_id',
        store=True,
        readonly=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='العملة',
        related='project_id.currency_id',
        store=True,
        readonly=True
    )
    date = fields.Date(
        string='تاريخ الاستلام الموقعي',
        default=fields.Date.context_today,
        required=True,
        tracking=True
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='المجهز / المورد',
        help='اسم المورد أو الناقل للمواد إلى موقع المشروع.'
    )
    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='أمر الشراء المرتبط',
        domain="[('project_id', '=', project_id)]"
    )
    delivery_note_ref = fields.Char(
        string='رقم المنفيست / وصل الاستلام من المجهز',
        required=True,
        help='رقم وصل التجهيز أو كتاب الشحن المرفق مع شاحنة المواد.'
    )
    receiving_engineer_id = fields.Many2one(
        'res.users',
        string='مهندس الموقع المستلم',
        default=lambda self: self.env.user,
        required=True,
        tracking=True
    )
    resident_engineer_id = fields.Many2one(
        'res.users',
        string='المهندس المقيم المشرف',
        tracking=True
    )

    # Warehouse & Location
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='مخزن الموقع المستلم',
        help='المخزن الموقعي للمشروع الذي سيتم إدخال المواد فيه.'
    )
    location_dest_id = fields.Many2one(
        'stock.location',
        string='موقع التخزين الموقعي الداخلي',
        domain="[('usage', '=', 'internal')]",
        help='الموقع المخزني الموقعي الدقيق.'
    )
    picking_id = fields.Many2one(
        'stock.picking',
        string='إذن الاستلام المخزني المولد',
        readonly=True,
        copy=False
    )

    state = fields.Selection([
        ('draft', 'مسودة'),
        ('inspected', 'مفحوص موقعياً ومطابق للمواصفات'),
        ('confirmed', 'معتمد ومثبت في المخزن الموقعي'),
        ('cancelled', 'ملغى / معادة الشحنة')
    ], string='الحالة', default='draft', tracking=True, index=True)

    line_ids = fields.One2many(
        'contracting.site.delivery.line',
        'delivery_id',
        string='مواد الإدخال المخزني الموقعي',
        copy=True
    )
    total_amount = fields.Monetary(
        string='إجمالي قيمة المواد المستلمة',
        currency_field='currency_id',
        compute='_compute_total_amount',
        store=True
    )
    quality_notes = fields.Text(
        string='ملاحظات الفحص الفني والمختبري الموقعي',
        help='نتائج الفحص البصري وفحوصات المكعبات الكونكريتية أو حديد التسليح أو شهادات المنشأ.'
    )

    @api.onchange('project_id')
    def _onchange_project_id(self):
        if self.project_id:
            warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.project_id.company_id.id)], limit=1)
            if warehouse:
                self.warehouse_id = warehouse.id
                self.location_dest_id = warehouse.lot_stock_id.id

    @api.depends('line_ids.subtotal')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = sum(record.line_ids.mapped('subtotal'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('مسودة إدخال موقعي')) == _('مسودة إدخال موقعي'):
                vals['name'] = self.env['ir.sequence'].next_by_code('contracting.site.delivery') or _('DEL/NEW')
        return super().create(vals_list)

    def action_inspect(self):
        for record in self:
            if not record.line_ids:
                raise UserError(_("لا يمكن فحص إذن استلام لا يحتوي على أي مواد!"))
            record.state = 'inspected'

    def action_confirm(self):
        for record in self:
            # Generate real Odoo Stock Picking if warehouse and locations available
            picking_type = False
            if record.warehouse_id:
                picking_type = record.warehouse_id.in_type_id
            if not picking_type:
                picking_type = self.env['stock.picking.type'].search([
                    ('company_id', '=', record.company_id.id),
                    ('code', '=', 'incoming')
                ], limit=1)

            supplier_loc = self.env['stock.location'].search([('usage', '=', 'supplier')], limit=1)
            dest_loc = record.location_dest_id or (record.warehouse_id.lot_stock_id if record.warehouse_id else False)

            if picking_type and supplier_loc and dest_loc and record.line_ids:
                moves = []
                for line in record.line_ids:
                    moves.append((0, 0, {
                        'name': f"{record.name} - {line.product_id.name}",
                        'product_id': line.product_id.id,
                        'product_uom': line.uom_id.id,
                        'product_uom_qty': line.received_qty,
                        'location_id': supplier_loc.id,
                        'location_dest_id': dest_loc.id,
                    }))
                picking_vals = {
                    'picking_type_id': picking_type.id,
                    'location_id': supplier_loc.id,
                    'location_dest_id': dest_loc.id,
                    'origin': record.name,
                    'partner_id': record.partner_id.id if record.partner_id else False,
                    'move_ids_without_package': moves,
                    'company_id': record.company_id.id,
                }
                try:
                    picking = self.env['stock.picking'].create(picking_vals)
                    picking.action_confirm()
                    record.picking_id = picking.id
                except Exception:
                    pass

            record.state = 'confirmed'

    def action_cancel(self):
        for record in self:
            record.state = 'cancelled'

    def action_reset_draft(self):
        for record in self:
            record.state = 'draft'


class ContractingSiteDeliveryLine(models.Model):
    _name = 'contracting.site.delivery.line'
    _description = 'بند الإدخال المخزني الموقعي (Site Delivery Item)'
    _order = 'id'

    delivery_id = fields.Many2one(
        'contracting.site.delivery',
        string='إذن الاستلام الموقعي',
        required=True,
        ondelete='cascade'
    )
    project_id = fields.Many2one(
        'project.project',
        related='delivery_id.project_id',
        store=True,
        readonly=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='delivery_id.currency_id',
        store=True,
        readonly=True
    )
    product_id = fields.Many2one(
        'product.product',
        string='المادة / المنتج',
        required=True
    )
    name = fields.Char(
        string='وصف المادة ومواصفاتها',
        required=True
    )
    boq_id = fields.Many2one(
        'contracting.project.boq',
        string='الفقرة المستفيدة من جدول الكميات',
        domain="[('project_id', '=', project_id)]",
        required=True,
        help='الفقرة الإنشائية المخصصة لاستهلاك هذه المادة.'
    )
    cost_element_id = fields.Many2one(
        'contracting.cost.element',
        string='عنصر التكلفة',
        help='تبويب التكلفة (مواد خامات، تجهيزات MEP).'
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='وحدة القياس',
        required=True
    )
    received_qty = fields.Float(
        string='الكمية المستلمة فعلياً',
        digits='Product Unit of Measure',
        required=True,
        default=1.0
    )
    unit_cost = fields.Monetary(
        string='سعر تكلفة الوحدة',
        currency_field='currency_id',
        default=0.0
    )
    subtotal = fields.Monetary(
        string='إجمالي القيمة',
        currency_field='currency_id',
        compute='_compute_subtotal',
        store=True
    )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.display_name
            self.uom_id = self.product_id.uom_id
            self.unit_cost = self.product_id.standard_price

    @api.depends('received_qty', 'unit_cost')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.received_qty * line.unit_cost
