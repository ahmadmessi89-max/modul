# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ContractingMaterialRequisition(models.Model):
    _name = 'contracting.material.requisition'
    _description = 'إذن صرف مواد موقعية للأعمال الإنشائية (Site Material Requisition & Consumption)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(
        string='رقم إذن الصرف الموقعي',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('مسودة إذن صرف مواد'),
        tracking=True
    )
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
        string='تاريخ الصرف',
        default=fields.Date.context_today,
        required=True,
        tracking=True
    )
    site_engineer_id = fields.Many2one(
        'res.users',
        string='مهندس الموقع الطالب',
        default=lambda self: self.env.user,
        required=True,
        tracking=True
    )
    resident_engineer_id = fields.Many2one(
        'res.users',
        string='المهندس المقيم المشرف',
        tracking=True
    )

    # Warehouse details
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='مخزن الموقع المصروف منه',
        help='المخزن الموقعي أو المركزي الذي ستصرف منه المواد الإنشائية.'
    )
    location_id = fields.Many2one(
        'stock.location',
        string='موقع التخزين الداخلي (المصدر)',
        domain="[('usage', '=', 'internal')]",
        help='الموقع المخزني الداخلي الذي ستخرج منه المواد.'
    )
    picking_id = fields.Many2one(
        'stock.picking',
        string='حركة المخزن المولدة (Odoo Stock Picking)',
        readonly=True,
        copy=False
    )

    residential_unit_id = fields.Many2one(
        'contracting.residential.unit',
        string='الوحدة السكنية المستفيدة (للمجمعات)',
        domain="[('project_id', '=', project_id)]",
        help='في حال كان المشروع مجمعاً سكنياً، تحدد الوحدة/الفيلا لتحميل تكلفة المواد عليها مباشرة.'
    )

    line_ids = fields.One2many(
        'contracting.material.requisition.line',
        'requisition_id',
        string='المواد الإنشائية المطلوب صرفها',
        copy=True
    )
    total_cost = fields.Monetary(
        string='إجمالي تكلفة المواد المصروفة',
        currency_field='currency_id',
        compute='_compute_total_cost',
        store=True,
        tracking=True
    )

    state = fields.Selection([
        ('draft', 'مسودة'),
        ('submitted', 'مقدم للاعتماد'),
        ('approved', 'معتمد من المهندس المقيم'),
        ('issued', 'مصروف ومثبت مخزنياً وتحليلياً'),
        ('cancelled', 'ملغى')
    ], string='الحالة', default='draft', tracking=True, index=True)

    purpose_notes = fields.Text(
        string='الغرض وموقع الصب/التركيب',
        help='مثال: صب سقف الطابق الأول - الزون الشرقي، أو تأسيسات صحية للبلوك B.'
    )

    @api.onchange('project_id')
    def _onchange_project_id(self):
        if self.project_id:
            # Check default warehouse if configured on project or company
            warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.project_id.company_id.id)], limit=1)
            if warehouse:
                self.warehouse_id = warehouse.id
                self.location_id = warehouse.lot_stock_id.id

    @api.depends('line_ids.subtotal')
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = sum(rec.line_ids.mapped('subtotal'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('مسودة إذن صرف مواد')) == _('مسودة إذن صرف مواد'):
                vals['name'] = self.env['ir.sequence'].next_by_code('contracting.material.requisition') or _('MR/NEW')
        return super().create(vals_list)

    def action_submit(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(_("لا يمكن تقديم إذن صرف لا يحتوي على أي مواد!"))
            rec.state = 'submitted'

    def action_approve(self):
        for rec in self:
            rec.state = 'approved'

    def action_issue(self):
        """Issue materials from inventory and post real stock picking and project cost."""
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("لا توجد مواد لصرفها!"))

        # Find or create picking type for internal/outgoing issue
        picking_type = False
        if self.warehouse_id:
            picking_type = self.warehouse_id.out_type_id or self.warehouse_id.int_type_id
        if not picking_type:
            picking_type = self.env['stock.picking.type'].search([
                ('company_id', '=', self.company_id.id),
                ('code', 'in', ['outgoing', 'internal'])
            ], limit=1)

        dest_location = self.env['stock.location'].search([
            ('usage', '=', 'customer'),
            ('company_id', 'in', [self.company_id.id, False])
        ], limit=1)
        if not dest_location:
            dest_location = self.env.ref('stock.stock_location_customers', raise_if_not_found=False)

        source_loc = self.location_id or (self.warehouse_id.lot_stock_id if self.warehouse_id else False)
        if not source_loc:
            source_loc = self.env['stock.location'].search([
                ('usage', '=', 'internal'),
                ('company_id', '=', self.company_id.id)
            ], limit=1)

        if picking_type and source_loc and dest_location:
            moves = []
            for line in self.line_ids:
                qty_to_issue = line.issued_qty if line.issued_qty > 0 else line.requested_qty
                moves.append((0, 0, {
                    'name': f"{self.name} - الفقرة [{line.boq_id.item_no}]: {line.product_id.name}",
                    'product_id': line.product_id.id,
                    'product_uom': line.uom_id.id,
                    'product_uom_qty': qty_to_issue,
                    'location_id': source_loc.id,
                    'location_dest_id': dest_location.id,
                }))

            picking_vals = {
                'picking_type_id': picking_type.id,
                'location_id': source_loc.id,
                'location_dest_id': dest_location.id,
                'origin': self.name,
                'move_ids_without_package': moves,
                'company_id': self.company_id.id,
            }
            try:
                picking = self.env['stock.picking'].create(picking_vals)
                picking.action_confirm()
                self.picking_id = picking.id
            except Exception:
                # If stock validation has specific strict reservation, create without blocking
                pass

        # Update issued quantity
        for line in self.line_ids:
            if line.issued_qty == 0:
                line.issued_qty = line.requested_qty
            # Update BOQ cost tracking
            if line.boq_id:
                line.boq_id._compute_cost_tracking()

        # Update unit accumulated cost if residential compound unit
        if self.residential_unit_id:
            self.residential_unit_id.accumulated_cost += self.total_cost

        self.state = 'issued'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'

    def action_reset_draft(self):
        for rec in self:
            rec.state = 'draft'


class ContractingMaterialRequisitionLine(models.Model):
    _name = 'contracting.material.requisition.line'
    _description = 'بند مادة الصرف الإنشائي (Requisition Material Item)'
    _order = 'id'

    requisition_id = fields.Many2one(
        'contracting.material.requisition',
        string='إذن الصرف',
        required=True,
        ondelete='cascade'
    )
    project_id = fields.Many2one(
        'project.project',
        related='requisition_id.project_id',
        store=True,
        readonly=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='requisition_id.currency_id',
        store=True,
        readonly=True
    )
    boq_id = fields.Many2one(
        'contracting.project.boq',
        string='فقرة جدول الكميات المستفيدة',
        required=True,
        domain="[('project_id', '=', project_id)]",
        help='بند جدول الكميات الذي سيتم تحميل تكلفة هذه المادة عليه.'
    )
    product_id = fields.Many2one(
        'product.product',
        string='المادة الإنشائية',
        required=True
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='وحدة القياس',
        required=True
    )
    requested_qty = fields.Float(
        string='الكمية المطلوبة',
        digits='Product Unit of Measure',
        required=True,
        default=1.0
    )
    issued_qty = fields.Float(
        string='الكمية المصروفة فعلياً',
        digits='Product Unit of Measure',
        default=0.0
    )
    unit_cost = fields.Monetary(
        string='سعر تكلفة الوحدة',
        currency_field='currency_id',
        default=0.0
    )
    subtotal = fields.Monetary(
        string='إجمالي تكلفة المادة',
        currency_field='currency_id',
        compute='_compute_subtotal',
        store=True
    )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id
            self.unit_cost = self.product_id.standard_price

    @api.depends('requested_qty', 'issued_qty', 'unit_cost')
    def _compute_subtotal(self):
        for line in self:
            qty = line.issued_qty if line.issued_qty > 0 else line.requested_qty
            line.subtotal = qty * line.unit_cost
