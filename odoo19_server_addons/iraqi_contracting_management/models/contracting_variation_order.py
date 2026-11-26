# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ContractingVariationOrder(models.Model):
    _name = 'contracting.variation.order'
    _description = 'أمر غيار إداري وهندسي (Variation Order / Change Order)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(
        string='رقم أمر الغيار',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('مسودة جديدة'),
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
        string='تاريخ أمر الغيار',
        default=fields.Date.context_today,
        required=True,
        tracking=True
    )
    engineer_in_charge_id = fields.Many2one(
        'res.users',
        string='المهندس المقيم المشرف',
        default=lambda self: self.env.user,
        tracking=True,
        help='المهندس المقيم المسؤول عن إعداد وتدقيق جدول الكميات المعدل لأمر الغيار.'
    )
    client_ref = fields.Char(
        string='رقم كتاب مصادقة رب العمل / الجهة المستفيدة',
        tracking=True,
        help='رقم وتاريخ الكتاب الرسمي الصادر من دائرة المهندس المقيم أو رب العمل بالموافقة على أمر الغيار.'
    )
    reason = fields.Text(
        string='أسباب ومبررات أمر الغيار',
        required=True,
        help='شرح تفصيلي للمتطلبات الهندسية والموقعية الموجبة لاستحداث أو تعديل الفقرات.'
    )
    state = fields.Selection([
        ('draft', 'مسودة'),
        ('submitted', 'مقدم للمهندس المقيم'),
        ('engineer_approved', 'موافق عليه من المهندس المقيم'),
        ('client_approved', 'موافق عليه من رب العمل (معتمد)'),
        ('rejected', 'مرفوض')
    ], string='الحالة', default='draft', tracking=True, index=True)

    line_ids = fields.One2many(
        'contracting.variation.order.line',
        'vo_id',
        string='فقرات أمر الغيار',
        copy=True
    )

    total_revenue_change = fields.Monetary(
        string='صافي التغيير في قيمة العقد (الإيرادات)',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
        tracking=True,
        help='الأثر المالي الإجمالي لأمر الغيار على قيمة العقد الكلية.'
    )
    total_cost_budget_change = fields.Monetary(
        string='صافي التغيير في موازنة التكلفة التقديرية',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
        tracking=True,
        help='الأثر المالي على موازنة التكلفة التقديرية لبنود المشروع.'
    )

    @api.depends('line_ids.subtotal_revenue', 'line_ids.subtotal_cost_budget')
    def _compute_totals(self):
        for record in self:
            record.total_revenue_change = sum(record.line_ids.mapped('subtotal_revenue'))
            record.total_cost_budget_change = sum(record.line_ids.mapped('subtotal_cost_budget'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('مسودة جديدة')) == _('مسودة جديدة'):
                vals['name'] = self.env['ir.sequence'].next_by_code('contracting.variation.order') or _('VO/NEW')
        return super().create(vals_list)

    # Workflow Actions
    def action_submit(self):
        for record in self:
            if not record.line_ids:
                raise UserError(_("لا يمكن تقديم أمر غيار فارغ بدون أي فقرات!"))
            record.state = 'submitted'

    def action_engineer_approve(self):
        for record in self:
            record.state = 'engineer_approved'

    def action_client_approve(self):
        for record in self:
            if not record.client_ref:
                raise UserError(_("يرجى إدخال رقم كتاب مصادقة رب العمل الرسمي قبل اعتماد أمر الغيار!"))

            # Process lines: add new BOQ items or update existing
            for line in record.line_ids:
                if line.change_type == 'new_item' and not line.boq_id:
                    # Create new BOQ line for project
                    new_boq = self.env['contracting.project.boq'].create({
                        'item_no': line.item_no or ('VO-' + line.vo_id.name),
                        'name': line.name,
                        'project_id': record.project_id.id,
                        'package_id': line.package_id.id or self.env['contracting.boq.package'].search([], limit=1).id,
                        'uom_id': line.uom_id.id,
                        'contract_qty': 0.0,
                        'tender_unit_price': line.unit_price,
                        'estimated_cost_unit_price': line.estimated_cost_unit_price,
                        'state': 'confirmed',
                    })
                    line.boq_id = new_boq.id

            record.state = 'client_approved'

            # Trigger recomputation on project and BOQ
            record.project_id._compute_contract_valuation()
            for line in record.line_ids:
                if line.boq_id:
                    line.boq_id._compute_vo_adjustments()
                    line.boq_id._compute_quantities()
                    line.boq_id._compute_amounts()
                    line.boq_id._compute_budget()

    def action_reject(self):
        for record in self:
            record.state = 'rejected'

    def action_reset_draft(self):
        for record in self:
            record.state = 'draft'


class ContractingVariationOrderLine(models.Model):
    _name = 'contracting.variation.order.line'
    _description = 'فقرة أمر الغيار (Variation Order Line)'
    _order = 'id'

    vo_id = fields.Many2one(
        'contracting.variation.order',
        string='أمر الغيار',
        required=True,
        ondelete='cascade'
    )
    project_id = fields.Many2one(
        'project.project',
        related='vo_id.project_id',
        store=True,
        readonly=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='vo_id.currency_id',
        store=True,
        readonly=True
    )
    change_type = fields.Selection([
        ('qty_change', 'تعديل كمية فقرة قائمة (+/-)'),
        ('new_item', 'إضافة فقرة جديدة مستحدثة'),
        ('price_change', 'تعديل سعر الوحدة'),
        ('omission', 'حذف / تقليص فقرة')
    ], string='نوع التغيير', required=True, default='qty_change')

    boq_id = fields.Many2one(
        'contracting.project.boq',
        string='بند جدول الكميات المرتبط',
        domain="[('project_id', '=', project_id)]",
        help='اختر البند القائم في جدول الكميات في حال تعديل كمية أو حذف.'
    )
    item_no = fields.Char(
        string='رقم الفقرة',
        help='رقم الفقرة في أمر الغيار أو جدول الكميات.'
    )
    name = fields.Text(
        string='وصف الفقرة المعدلة / المستحدثة',
        required=True
    )
    package_id = fields.Many2one(
        'contracting.boq.package',
        string='حزمة العمل'
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='وحدة القياس',
        required=True
    )

    current_contract_qty = fields.Float(
        string='الكمية الحالية قبل التعديل',
        digits='Product Unit of Measure',
        compute='_compute_current_qty',
        store=True,
        readonly=False
    )
    delta_qty = fields.Float(
        string='الكمية المضافة / المحذوفة (+/-)',
        digits='Product Unit of Measure',
        required=True,
        default=0.0,
        help='أدخل القيمة موجبة للزيادة وسالبة للحذف أو التخفيض.'
    )
    new_qty = fields.Float(
        string='الكمية النهائية بعد التعديل',
        digits='Product Unit of Measure',
        compute='_compute_new_qty',
        store=True
    )

    unit_price = fields.Monetary(
        string='سعر الوحدة التعاقدي',
        currency_field='currency_id',
        required=True,
        default=0.0
    )
    estimated_cost_unit_price = fields.Monetary(
        string='سعر التكلفة التقديري للوحدة',
        currency_field='currency_id',
        default=0.0
    )

    subtotal_revenue = fields.Monetary(
        string='تأثير الإيرادات (قيمة العقد)',
        currency_field='currency_id',
        compute='_compute_line_subtotals',
        store=True
    )
    subtotal_cost_budget = fields.Monetary(
        string='تأثير موازنة التكلفة',
        currency_field='currency_id',
        compute='_compute_line_subtotals',
        store=True
    )

    @api.onchange('boq_id')
    def _onchange_boq_id(self):
        if self.boq_id:
            self.item_no = self.boq_id.item_no
            self.name = self.boq_id.name
            self.package_id = self.boq_id.package_id
            self.uom_id = self.boq_id.uom_id
            self.current_contract_qty = self.boq_id.revised_contract_qty
            self.unit_price = self.boq_id.tender_unit_price
            self.estimated_cost_unit_price = self.boq_id.estimated_cost_unit_price

    @api.depends('boq_id', 'boq_id.revised_contract_qty')
    def _compute_current_qty(self):
        for line in self:
            if line.boq_id:
                line.current_contract_qty = line.boq_id.revised_contract_qty
            else:
                line.current_contract_qty = line.current_contract_qty or 0.0

    @api.depends('current_contract_qty', 'delta_qty', 'change_type')
    def _compute_new_qty(self):
        for line in self:
            if line.change_type == 'new_item':
                line.new_qty = line.delta_qty
            else:
                line.new_qty = line.current_contract_qty + line.delta_qty

    @api.depends('delta_qty', 'unit_price', 'estimated_cost_unit_price', 'change_type')
    def _compute_line_subtotals(self):
        for line in self:
            qty = line.delta_qty if line.change_type in ['qty_change', 'omission'] else line.new_qty
            line.subtotal_revenue = qty * line.unit_price
            line.subtotal_cost_budget = qty * line.estimated_cost_unit_price
