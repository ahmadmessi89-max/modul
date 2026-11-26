# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ContractingResidentialUnit(models.Model):
    _name = 'contracting.residential.unit'
    _description = 'وحدة سكنية / فيلا في المجمع السكني (Residential Compound Unit)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'block, name, id'

    name = fields.Char(
        string='رقم / رمز الوحدة السكنية',
        required=True,
        tracking=True,
        help='مثال: فيلا V-102، شقة A-401.'
    )
    project_id = fields.Many2one(
        'project.project',
        string='مشروع المجمع السكني',
        required=True,
        domain="[('is_residential_complex', '=', True)]",
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
    block = fields.Char(
        string='البلوك / الزون / المربع',
        required=True,
        tracking=True,
        help='مثال: زون الورد، بلوك 4.'
    )
    unit_type = fields.Selection([
        ('villa_type_a', 'فيلا نموذج (A) طابقين'),
        ('villa_type_b', 'فيلا نموذج (B) طابق واحد'),
        ('apt_duplex', 'شقة دوبلكس'),
        ('apt_std', 'شقة سكنية قياسية'),
        ('commercial', 'محل / مساحة تجارية بالمجمع')
    ], string='نموذج ونوع الوحدة', required=True, default='villa_type_a', tracking=True)

    land_area_sqm = fields.Float(
        string='مساحة الأرض (م2)',
        default=200.0
    )
    built_area_sqm = fields.Float(
        string='مساحة البناء (م2)',
        default=250.0
    )

    status = fields.Selection([
        ('structure', 'قيد أعمال الهيكل الإنشائي'),
        ('finishing', 'قيد أعمال الإنهاءات والتشطيب'),
        ('ready', 'جاهزة للتسليم (مكتملة)'),
        ('reserved', 'محجوزة بدفعة أولى'),
        ('sold', 'مباعة بالكامل'),
        ('handed_over', 'مسلمة للساكن')
    ], string='حالة الوحدة السكنية', default='structure', tracking=True, index=True)

    partner_id = fields.Many2one(
        'res.partner',
        string='المشتري / الحاجز',
        tracking=True
    )

    # Costing and Pricing
    target_selling_price = fields.Monetary(
        string='سعر البيع المعتمد للوحدة',
        currency_field='currency_id',
        tracking=True
    )
    accumulated_cost = fields.Monetary(
        string='إجمالي التكلفة الفعلية المحملة على الوحدة',
        currency_field='currency_id',
        compute='_compute_accumulated_cost',
        store=True,
        tracking=True,
        help='مجموع كلف مواد الإنهاءات والأطقم والأعمال المنفذة والمخصصة لهذه الوحدة بالتحديد.'
    )
    profit_margin = fields.Monetary(
        string='صافي هامش الربح المتوقع',
        currency_field='currency_id',
        compute='_compute_profit_margin',
        store=True
    )

    requisition_ids = fields.One2many(
        'contracting.material.requisition',
        'residential_unit_id',
        string='أذونات صرف المواد المخصصة للوحدة'
    )
    notes = fields.Text(string='ملاحظات ومواصفات الإنهاءات الخاصة')

    @api.depends('requisition_ids.state', 'requisition_ids.total_cost')
    def _compute_accumulated_cost(self):
        for rec in self:
            issued_reqs = rec.requisition_ids.filtered(lambda r: r.state == 'issued')
            rec.accumulated_cost = sum(issued_reqs.mapped('total_cost'))

    @api.depends('target_selling_price', 'accumulated_cost')
    def _compute_profit_margin(self):
        for rec in self:
            rec.profit_margin = rec.target_selling_price - rec.accumulated_cost


class ProjectProjectResidential(models.Model):
    _inherit = 'project.project'

    is_residential_complex = fields.Boolean(
        string='مشروع مجمع سكني وتطوير عقاري',
        default=False,
        help='تفعيل هذا الخيار لتحويل المشروع إلى مجمع سكني يضم وحدات وفلل ومخازن تشطيب وصيانة.'
    )
    residential_unit_ids = fields.One2many(
        'contracting.residential.unit',
        'project_id',
        string='الوحدات السكنية في المجمع'
    )
    residential_units_count = fields.Integer(
        string='إجمالي عدد الوحدات السكنية',
        compute='_compute_residential_counts'
    )
    sold_units_count = fields.Integer(
        string='عدد الوحدات المباعة والمحجوزة',
        compute='_compute_residential_counts'
    )

    # Multi-tier Warehouses for Compounds
    infrastructure_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='مخزن الهيكل الإنشائي والبنى التحتية',
        help='مخزن المواد الإنشائية الثقيلة (سمنت، حديد، طابوق، قوالب).'
    )
    finishing_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='مخزن مواد الإنهاءات والأطقم والتشطيب',
        help='مخزن السيراميك، الأدوات الصحية، الإنارة، الأبواب، وأطقم المطابخ.'
    )
    maintenance_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='مخزن صيانة وتشغيل المجمع (FM Store)',
        help='مخزن قطع الغيار والمضخات ومواد الصيانة المستمرة لإدارة المجمع بعد السكن.'
    )

    @api.depends('residential_unit_ids', 'residential_unit_ids.status')
    def _compute_residential_counts(self):
        for p in self:
            p.residential_units_count = len(p.residential_unit_ids)
            p.sold_units_count = len(p.residential_unit_ids.filtered(lambda u: u.status in ['reserved', 'sold', 'handed_over']))

    def action_view_residential_units(self):
        self.ensure_one()
        return {
            'name': _('الوحدات والفلل السكنية - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'contracting.residential.unit',
            'view_mode': 'kanban,list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {
                'default_project_id': self.id,
                'default_is_residential_complex': True,
            }
        }
