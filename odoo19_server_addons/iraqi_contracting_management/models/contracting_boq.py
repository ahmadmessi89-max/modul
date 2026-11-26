# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class ContractingBoqPackage(models.Model):
    _name = 'contracting.boq.package'
    _description = 'حزمة عمل جدول الكميات (BOQ Package / WBS Group)'
    _order = 'sequence, code'

    name = fields.Char(
        string='اسم حزمة العمل',
        required=True,
        translate=True
    )
    code = fields.Char(
        string='رمز الحزمة',
        required=True
    )
    sequence = fields.Integer(
        string='التسلسل',
        default=10
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='الحساب التحليلي للحزمة'
    )
    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        default=lambda self: self.env.company
    )


class ContractingCostElement(models.Model):
    _name = 'contracting.cost.element'
    _description = 'عنصر التكلفة الإنشائية (Cost Element)'
    _order = 'code'

    name = fields.Char(
        string='اسم عنصر التكلفة',
        required=True,
        translate=True
    )
    code = fields.Char(
        string='رمز العنصر',
        required=True
    )
    description = fields.Text(
        string='الوصف والتبويب'
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='الحساب التحليلي لعنصر التكلفة'
    )
    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        default=lambda self: self.env.company
    )


class ContractingProjectBoq(models.Model):
    _name = 'contracting.project.boq'
    _description = 'بند جدول الكميات والتسعير (Bill of Quantities Line)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, item_no, id'

    item_no = fields.Char(
        string='رقم الفقرة / البند',
        required=True,
        copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('contracting.project.boq') or 'BOQ-0001',
        help='رقم تسلسل الفقرة في جدول الكميات والتسعير التعاقدي (مثل 1.1، 2.4).'
    )
    sequence = fields.Integer(
        string='التسلسل',
        default=10
    )
    name = fields.Text(
        string='وصف الفقرة / جدول الكميات والتسعير',
        required=True,
        help='المواصفات الفنية التفصيلية للفقرة وجدول الكميات.'
    )
    project_id = fields.Many2one(
        'project.project',
        string='المشروع الإنشائي',
        required=True,
        ondelete='cascade',
        index=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        related='project_id.company_id',
        store=True,
        readonly=True
    )
    package_id = fields.Many2one(
        'contracting.boq.package',
        string='حزمة العمل (BOQ Package)',
        required=True,
        help='تصنيف الفقرة ضمن حزم العمل (أعمال ترابية، هياكل كونكريتية، إنهاءات، MEP).'
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='وحدة القياس',
        required=True,
        help='وحدة القياس الهندسية للفقرة (م3، م2، م.ط، عدد، طن، مقطوعية، ...).'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='العملة',
        related='project_id.currency_id',
        store=True,
        readonly=True
    )

    # Contract & Variation Quantities
    contract_qty = fields.Float(
        string='الكمية العقدية الأصلية',
        digits='Product Unit of Measure',
        required=True,
        default=1.0,
        help='كمية الفقرة المعتمدة في وثيقة العقد الأصلية.'
    )
    vo_qty = fields.Float(
        string='تعديلات أوامر الغيار (+/-)',
        digits='Product Unit of Measure',
        compute='_compute_vo_adjustments',
        store=True,
        help='صافي التعديلات على الكمية الناتجة من أوامر الغيار المصادق عليها.'
    )
    revised_contract_qty = fields.Float(
        string='الكمية العقدية المعدلة',
        digits='Product Unit of Measure',
        compute='_compute_quantities',
        store=True,
        help='الكمية العقدية بعد تطبيق أوامر الغيار المعتمدة (الكمية الأصلية + أوامر الغيار).'
    )

    # Tender Prices & Revenues
    tender_unit_price = fields.Monetary(
        string='سعر الوحدة العقدي',
        currency_field='currency_id',
        required=True,
        default=0.0,
        help='سعر الوحدة التعاقدي للفقرة (Tender Unit Price) المعتمد في جدول التسعير.'
    )
    total_tender_amount = fields.Monetary(
        string='القيمة الإجمالية العقدية الأصلية',
        currency_field='currency_id',
        compute='_compute_amounts',
        store=True,
        help='القيمة الإجمالية الأصلية للفقرة (الكمية العقدية × سعر الوحدة).'
    )
    revised_total_amount = fields.Monetary(
        string='القيمة الإجمالية بعد أوامر الغيار',
        currency_field='currency_id',
        compute='_compute_amounts',
        store=True,
        help='القيمة الإجمالية للفقرة بعد احتساب أوامر الغيار المصادق عليها.'
    )

    # Cost Budgeting & Control
    estimated_cost_unit_price = fields.Monetary(
        string='سعر التكلفة التقديري للوحدة',
        currency_field='currency_id',
        default=0.0,
        help='التكلفة التقديرية لوحدة العمل المعتمدة في دراسة الجدوى والموازنة التخطيطية.'
    )
    total_estimated_budget = fields.Monetary(
        string='إجمالي موازنة التكلفة التقديرية',
        currency_field='currency_id',
        compute='_compute_budget',
        store=True,
        help='الموازنة التقديرية المرصودة للفقرة (الكمية المعدلة × سعر التكلفة التقديري).'
    )
    committed_cost_amount = fields.Monetary(
        string='التكاليف المحجوزة (أوامر الشراء)',
        currency_field='currency_id',
        compute='_compute_cost_tracking',
        store=True,
        help='إجمالي قيمة أوامر الشراء الصادرة وغير المفوترة لهذا البند.'
    )
    actual_cost_amount = fields.Monetary(
        string='التكاليف الفعلية المصروفة',
        currency_field='currency_id',
        compute='_compute_cost_tracking',
        store=True,
        help='إجمالي التكاليف الفعلية المسجلة بالفواتير والمصروفات المباشرة لهذا البند.'
    )
    total_incurred_cost = fields.Monetary(
        string='إجمالي التكاليف المنفقة والمحجوزة',
        currency_field='currency_id',
        compute='_compute_cost_tracking',
        store=True,
        help='مجموع التكاليف الفعلية وأوامر الشراء المحجوزة.'
    )
    remaining_budget = fields.Monetary(
        string='المتبقي من ميزانية البند',
        currency_field='currency_id',
        compute='_compute_cost_tracking',
        store=True,
        help='المبلغ المتبقي المتاح للصرف على هذا البند قبل تجاوز الموازنة التقديرية.'
    )
    budget_consumed_percent = fields.Float(
        string='نسبة استهلاك الموازنة (%)',
        compute='_compute_cost_tracking',
        store=True
    )

    # Execution & Cumulative Quantities (الذرعات المنفذة والتراكمية)
    previous_cumulative_qty = fields.Float(
        string='الذرعة التراكمية السابقة',
        digits='Product Unit of Measure',
        compute='_compute_ipc_quantities',
        store=True,
        help='كمية الأعمال المنفذة والمصادق عليها حتى الذرعة السابقة.'
    )
    current_executed_qty = fields.Float(
        string='الذرعة المنفذة الحالية',
        digits='Product Unit of Measure',
        compute='_compute_ipc_quantities',
        store=True,
        help='كمية الأعمال المنفذة خلال الفترة الحالية.'
    )
    cumulative_qty = fields.Float(
        string='الذرعة التراكمية الإجمالية',
        digits='Product Unit of Measure',
        compute='_compute_ipc_quantities',
        store=True,
        help='إجمالي الذرعة التراكمية المنفذة حتى تاريخه (السابقة + الحالية).'
    )
    completion_percentage = fields.Float(
        string='نسبة الإنجاز الفني للفقرة (%)',
        compute='_compute_completion_progress',
        store=True,
        help='نسبة الإنجاز الفعلي = (الذرعة التراكمية ÷ الكمية العقدية المعدلة) × 100.'
    )
    boq_alert_state = fields.Selection([
        ('normal', 'طبيعي (ضمن الحدود)'),
        ('warning_80', 'تنبيه: اقتراب استنفاذ الكمية التعاقدية (80%+)'),
        ('warning_100', 'استنفاذ كامل الكمية العقدية (100%)'),
        ('exceeded', 'تجاوز الكمية التعاقدية (مطلوب أمر غيار عاجل)')
    ], string='مؤشر الرقابة الموقعية', compute='_compute_boq_alerts', store=True)
    
    cost_variance_amount = fields.Monetary(
        string='انحراف التكلفة التقديرية عن الفعلي',
        currency_field='currency_id',
        compute='_compute_cost_tracking',
        store=True,
        help='الفارق بين الموازنة التقديرية والتكاليف الفعلية والمحجوزة (+ وفر / - عجز).'
    )
    cumulative_amount = fields.Monetary(
        string='القيمة التراكمية للأعمال المنجزة',
        currency_field='currency_id',
        compute='_compute_completion_progress',
        store=True,
        help='القيمة المالية المستحقة عن الأعمال التراكمية المنفذة (الذرعة التراكمية × سعر الوحدة).'
    )

    # Analytic Distribution (Odoo 19 Standard: JSON Dict)
    analytic_distribution = fields.Json(
        string='التوزيع التحليلي ثلاثي الأبعاد',
        compute='_compute_analytic_distribution',
        store=True,
        help='التوزيع التحليلي التلقائي ثلاثي الأبعاد (المشروع - حزمة العمل - البند).'
    )
    analytic_precision = fields.Integer(
        string='دقة التوزيع التحليلي',
        store=False,
        default=2,
    )

    state = fields.Selection([
        ('draft', 'مسودة'),
        ('confirmed', 'معتمد'),
        ('in_progress', 'قيد التنفيذ'),
        ('completed', 'مكتمل الإنجاز'),
        ('cancelled', 'ملغى')
    ], string='الحالة', default='draft', tracking=True)

    # Relational lines
    purchase_order_line_ids = fields.One2many(
        'purchase.order.line',
        'boq_id',
        string='أوامر الشراء المرتبطة'
    )
    vo_line_ids = fields.One2many(
        'contracting.variation.order.line',
        'boq_id',
        string='تعديلات أوامر الغيار'
    )
    ipc_line_ids = fields.One2many(
        'contracting.interim.payment.line',
        'boq_id',
        string='أسطر الذرعات والسلف المنجزة'
    )
    material_line_ids = fields.One2many(
        'contracting.boq.material.line',
        'boq_id',
        string='تحليل المواد والمكونات المعيارية (BOQ Material BOM)'
    )
    requisition_line_ids = fields.One2many(
        'contracting.material.requisition.line',
        'boq_id',
        string='أذونات صرف المواد المصروفة من المخزن'
    )
    material_consumed_amount = fields.Monetary(
        string='كلفة المواد المصروفة من المخازن',
        currency_field='currency_id',
        compute='_compute_cost_tracking',
        store=True,
        help='إجمالي كلفة المواد الإنشائية المصروفة فعلياً من مخزن الموقع على هذا البند.'
    )
    subcontractor_executed_amount = fields.Monetary(
        string='كلفة ذرعات مقاولي الباطن',
        currency_field='currency_id',
        compute='_compute_cost_tracking',
        store=True,
        help='إجمالي مبالغ الذرعات المصادق عليها لمقاولي الباطن المنفذين لهذا البند.'
    )

    # Computes
    @api.depends('vo_line_ids', 'vo_line_ids.vo_id.state', 'vo_line_ids.delta_qty')
    def _compute_vo_adjustments(self):
        for record in self:
            approved_lines = record.vo_line_ids.filtered(
                lambda l: l.vo_id.state == 'client_approved'
            )
            record.vo_qty = sum(approved_lines.mapped('delta_qty'))

    @api.depends('contract_qty', 'vo_qty')
    def _compute_quantities(self):
        for record in self:
            record.revised_contract_qty = record.contract_qty + record.vo_qty

    @api.depends('contract_qty', 'revised_contract_qty', 'tender_unit_price')
    def _compute_amounts(self):
        for record in self:
            record.total_tender_amount = record.contract_qty * record.tender_unit_price
            record.revised_total_amount = record.revised_contract_qty * record.tender_unit_price

    @api.depends('revised_contract_qty', 'estimated_cost_unit_price')
    def _compute_budget(self):
        for record in self:
            record.total_estimated_budget = record.revised_contract_qty * record.estimated_cost_unit_price

    @api.depends('purchase_order_line_ids.price_subtotal', 'purchase_order_line_ids.order_id.state',
                 'purchase_order_line_ids.qty_invoiced', 'purchase_order_line_ids.product_qty',
                 'requisition_line_ids.subtotal', 'requisition_line_ids.requisition_id.state',
                 'ipc_line_ids.current_amount', 'ipc_line_ids.ipc_id.state', 'ipc_line_ids.ipc_id.ipc_type',
                 'total_estimated_budget')
    def _compute_cost_tracking(self):
        for record in self:
            po_lines = record.purchase_order_line_ids.filtered(
                lambda l: l.order_id.state in ['purchase', 'done']
            )
            committed = 0.0
            actual_po = 0.0
            for line in po_lines:
                if line.product_qty > 0:
                    uninvoiced_ratio = max(0.0, (line.product_qty - line.qty_invoiced) / line.product_qty)
                    invoiced_ratio = min(1.0, line.qty_invoiced / line.product_qty)
                    committed += line.price_subtotal * uninvoiced_ratio
                    actual_po += line.price_subtotal * invoiced_ratio
                else:
                    committed += line.price_subtotal

            # Material Consumed from Site/Central Warehouses
            issued_reqs = record.requisition_line_ids.filtered(
                lambda r: r.requisition_id.state == 'issued'
            )
            mat_consumed = sum(issued_reqs.mapped('subtotal'))

            # Subcontractor IPCs executed
            sub_ipcs = record.ipc_line_ids.filtered(
                lambda l: l.ipc_id.ipc_type == 'subcontractor' and l.ipc_id.state in ['approved', 'invoiced']
            )
            sub_executed = sum(sub_ipcs.mapped('current_amount'))

            record.committed_cost_amount = committed
            record.material_consumed_amount = mat_consumed
            record.subcontractor_executed_amount = sub_executed
            record.actual_cost_amount = actual_po + mat_consumed + sub_executed
            record.total_incurred_cost = committed + record.actual_cost_amount
            record.remaining_budget = record.total_estimated_budget - record.total_incurred_cost
            record.cost_variance_amount = record.total_estimated_budget - record.total_incurred_cost
            if record.total_estimated_budget > 0:
                record.budget_consumed_percent = (record.total_incurred_cost / record.total_estimated_budget) * 100.0
            else:
                record.budget_consumed_percent = 0.0

    @api.depends('ipc_line_ids', 'ipc_line_ids.ipc_id.state', 'ipc_line_ids.current_qty', 'ipc_line_ids.previous_qty')
    def _compute_ipc_quantities(self):
        for record in self:
            approved_ipc_lines = record.ipc_line_ids.filtered(
                lambda l: l.ipc_id.state in ['approved', 'invoiced'] and l.ipc_id.ipc_type == 'client'
            ).sorted(key=lambda l: l.ipc_id.date or fields.Date.today(), reverse=True)

            if approved_ipc_lines:
                latest_line = approved_ipc_lines[0]
                record.previous_cumulative_qty = latest_line.previous_qty
                record.current_executed_qty = latest_line.current_qty
                record.cumulative_qty = latest_line.cumulative_qty
            else:
                record.previous_cumulative_qty = 0.0
                record.current_executed_qty = 0.0
                record.cumulative_qty = 0.0

    @api.depends('cumulative_qty', 'revised_contract_qty', 'tender_unit_price')
    def _compute_completion_progress(self):
        for record in self:
            if record.revised_contract_qty > 0:
                record.completion_percentage = (record.cumulative_qty / record.revised_contract_qty) * 100.0
            else:
                record.completion_percentage = 0.0
            record.cumulative_amount = record.cumulative_qty * record.tender_unit_price

    @api.depends('completion_percentage', 'cumulative_qty', 'revised_contract_qty')
    def _compute_boq_alerts(self):
        for record in self:
            if record.cumulative_qty > record.revised_contract_qty:
                record.boq_alert_state = 'exceeded'
            elif record.completion_percentage >= 100.0:
                record.boq_alert_state = 'warning_100'
            elif record.completion_percentage >= 80.0:
                record.boq_alert_state = 'warning_80'
            else:
                record.boq_alert_state = 'normal'

    @api.depends('project_id', 'project_id.analytic_account_id', 'package_id', 'package_id.analytic_account_id')
    def _compute_analytic_distribution(self):
        for record in self:
            distribution = {}
            if record.project_id and record.project_id.analytic_account_id:
                distribution[str(record.project_id.analytic_account_id.id)] = 100.0
            if record.package_id and record.package_id.analytic_account_id:
                distribution[str(record.package_id.analytic_account_id.id)] = 100.0
            record.analytic_distribution = distribution or False

    # Workflow Actions
    def action_confirm(self):
        for record in self:
            record.state = 'confirmed'

    def action_start_progress(self):
        for record in self:
            record.state = 'in_progress'

    def action_complete(self):
        for record in self:
            record.state = 'completed'

    def action_reset_draft(self):
        for record in self:
            record.state = 'draft'


class ContractingBoqMaterialLine(models.Model):
    _name = 'contracting.boq.material.line'
    _description = 'تحليل مكونات ومواد بند جدول الكميات (BOQ Material BOM Breakdown)'
    _order = 'id'

    boq_id = fields.Many2one(
        'contracting.project.boq',
        string='فقرة جدول الكميات',
        required=True,
        ondelete='cascade'
    )
    project_id = fields.Many2one(
        'project.project',
        related='boq_id.project_id',
        store=True,
        readonly=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='boq_id.currency_id',
        store=True,
        readonly=True
    )
    product_id = fields.Many2one(
        'product.product',
        string='المادة الإنشائية',
        required=True,
        help='المادة الخام المستهلكة في هذه الفقرة (سمنت، حديد، رمل، طابوق، كابلات).'
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='وحدة القياس للمادة',
        required=True
    )
    standard_qty_per_unit = fields.Float(
        string='الكمية المعيارية للوحدة الواحدة',
        digits='Product Unit of Measure',
        required=True,
        default=1.0,
        help='كمية المادة المطلوبة لإنجاز وحدة واحدة من فقرة جدول الكميات (مثلاً: 350 كغم سمنت لكل 1 م3 كونكريت).'
    )
    planned_total_qty = fields.Float(
        string='إجمالي الكمية المخططة للمشروع',
        digits='Product Unit of Measure',
        compute='_compute_planned_qty',
        store=True,
        help='إجمالي احتياج المشروع من هذه المادة = كمية الفقرة المعدلة × الكمية المعيارية للوحدة.'
    )
    standard_unit_cost = fields.Monetary(
        string='كلفة وحدة المادة التقديرية',
        currency_field='currency_id',
        default=0.0
    )
    estimated_subtotal = fields.Monetary(
        string='إجمالي كلفة المادة التقديرية',
        currency_field='currency_id',
        compute='_compute_subtotal',
        store=True
    )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id
            self.standard_unit_cost = self.product_id.standard_price

    @api.depends('standard_qty_per_unit', 'boq_id.revised_contract_qty')
    def _compute_planned_qty(self):
        for line in self:
            contract_qty = line.boq_id.revised_contract_qty if line.boq_id else 0.0
            line.planned_total_qty = contract_qty * line.standard_qty_per_unit

    @api.depends('planned_total_qty', 'standard_unit_cost')
    def _compute_subtotal(self):
        for line in self:
            line.estimated_subtotal = line.planned_total_qty * line.standard_unit_cost

