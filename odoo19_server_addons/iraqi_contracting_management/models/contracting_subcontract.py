# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ContractingSubcontractAgreement(models.Model):
    _name = 'contracting.subcontract.agreement'
    _description = 'عقد مقاولة باطن / مقاول ثانوي (Subcontract Agreement)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc, id desc'

    name = fields.Char(
        string='رقم عقد مقاولة الباطن',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('مسودة عقد مقاولة باطن'),
        tracking=True
    )
    contract_ref = fields.Char(
        string='الرقم المرجعي / رمز العقد',
        tracking=True,
        help='الرقم المسجل على الوثيقة الورقية للعقد.'
    )
    title = fields.Char(
        string='موضوع وعنوان المقاولة',
        required=True,
        tracking=True,
        help='مثال: أعمال التأسيسات الكهربائية للمشروع، أعمال الصبغ والإنهاءات.'
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
    subcontractor_id = fields.Many2one(
        'res.partner',
        string='المقاول الثانوي (مقاول الباطن)',
        required=True,
        tracking=True
    )
    date_signed = fields.Date(
        string='تاريخ توقيع العقد',
        default=fields.Date.context_today,
        tracking=True
    )
    date_start = fields.Date(
        string='تاريخ المباشرة الموقعية',
        tracking=True
    )
    date_end = fields.Date(
        string='تاريخ انتهاء المدة العقدية',
        tracking=True
    )
    contract_duration_days = fields.Integer(
        string='مدة التنفيذ (يوم تقويمي)',
        default=90
    )

    # Financial and Terms
    contract_amount = fields.Monetary(
        string='القيمة الإجمالية لعقد مقاولة الباطن',
        currency_field='currency_id',
        compute='_compute_contract_amount',
        store=True,
        tracking=True
    )
    advance_payment_amount = fields.Monetary(
        string='مبلغ السلفة التشغيلية الممنوحة للمقاول',
        currency_field='currency_id',
        default=0.0,
        tracking=True
    )
    advance_recovery_rate = fields.Float(
        string='نسبة استرداد السلفة التشغيلية من الذرعات (%)',
        default=10.0,
        help='نسبة الخصم من كل سلفة منجزة لمقاول الباطن لإطفاء السلفة الأولية.'
    )
    retention_rate = fields.Float(
        string='نسبة أمانات حسن التنفيذ والصيانة (%)',
        default=10.0,
        help='النسبة المحتجزة كأمانات صيانة حتى إنجاز الأعمال والتسليم النهائي.'
    )
    tax_deduction_rate = fields.Float(
        string='نسبة الاستقطاع الضريبي المباشر (%)',
        default=2.7,
        help='نسبة الأمانات الضريبية المحتجزة لصالح الهيئة العامة للضرائب (عادة 2.7% إلى 3.3%).'
    )

    # Bank Guarantees / Bonds
    performance_bond_ref = fields.Char(
        string='رقم خطاب ضمان حسن التنفيذ'
    )
    performance_bond_bank = fields.Char(
        string='المصرف المصدر لخطاب الضمان'
    )
    performance_bond_expiry = fields.Date(
        string='تاريخ نفاذ خطاب الضمان',
        tracking=True
    )

    state = fields.Selection([
        ('draft', 'مسودة العقد'),
        ('confirmed', 'معتمد وموقع'),
        ('in_progress', 'قيد التنفيذ والمباشرة'),
        ('completed', 'منجز ومسلم نهائياً'),
        ('terminated', 'مفسوخ / ملغى')
    ], string='الحالة', default='draft', tracking=True, index=True)

    line_ids = fields.One2many(
        'contracting.subcontract.line',
        'subcontract_id',
        string='بنود أعمال العقد وأسعار الباطن',
        copy=True
    )
    ipc_ids = fields.One2many(
        'contracting.interim.payment',
        'subcontract_id',
        string='ذرعات وسلف مقاول الباطن'
    )

    # Progress tracking
    total_executed_amount = fields.Monetary(
        string='إجمالي الأعمال المنجزة بموجب الذرعات',
        currency_field='currency_id',
        compute='_compute_progress',
        store=True
    )
    total_paid_amount = fields.Monetary(
        string='إجمالي المبالغ الصافية المصروفة',
        currency_field='currency_id',
        compute='_compute_progress',
        store=True
    )
    remaining_balance = fields.Monetary(
        string='المتبقي من قيمة العقد',
        currency_field='currency_id',
        compute='_compute_progress',
        store=True
    )
    ipc_count = fields.Integer(
        string='عدد الذرعات المنجزة',
        compute='_compute_ipc_count'
    )

    notes = fields.Text(string='شروط والتزامات العقد')

    @api.depends('line_ids.subtotal')
    def _compute_contract_amount(self):
        for rec in self:
            rec.contract_amount = sum(rec.line_ids.mapped('subtotal'))

    @api.depends('ipc_ids.state', 'ipc_ids.gross_cumulative_amount', 'ipc_ids.net_payable_amount', 'contract_amount')
    def _compute_progress(self):
        for rec in self:
            approved_ipcs = rec.ipc_ids.filtered(lambda i: i.state in ['approved', 'invoiced'])
            executed = 0.0
            paid = 0.0
            if approved_ipcs:
                latest_ipc = approved_ipcs.sorted(key=lambda x: x.date, reverse=True)[0]
                executed = latest_ipc.gross_cumulative_amount
                paid = sum(approved_ipcs.mapped('net_payable_amount'))
            rec.total_executed_amount = executed
            rec.total_paid_amount = paid
            rec.remaining_balance = max(0.0, rec.contract_amount - executed)

    @api.depends('ipc_ids.state')
    def _compute_ipc_count(self):
        for rec in self:
            rec.ipc_count = len(rec.ipc_ids.filtered(lambda i: i.state in ['approved', 'invoiced']))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('مسودة عقد مقاولة باطن')) == _('مسودة عقد مقاولة باطن'):
                vals['name'] = self.env['ir.sequence'].next_by_code('contracting.subcontract.agreement') or _('SC/NEW')
        return super().create(vals_list)

    def action_confirm(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(_("لا يمكن اعتماد عقد لا يحتوي على أي بنود أعمال!"))
            rec.state = 'confirmed'

    def action_start(self):
        for rec in self:
            rec.state = 'in_progress'

    def action_complete(self):
        for rec in self:
            rec.state = 'completed'

    def action_terminate(self):
        for rec in self:
            rec.state = 'terminated'

    def action_reset_draft(self):
        for rec in self:
            rec.state = 'draft'

    def action_view_ipcs(self):
        self.ensure_one()
        return {
            'name': _('ذرعات وسلف المقاول الثانوي - %s') % self.subcontractor_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'contracting.interim.payment',
            'view_mode': 'list,form',
            'domain': [('subcontract_id', '=', self.id)],
            'context': {
                'default_subcontract_id': self.id,
                'default_project_id': self.project_id.id,
                'default_partner_id': self.subcontractor_id.id,
                'default_ipc_type': 'subcontractor',
            }
        }


class ContractingSubcontractLine(models.Model):
    _name = 'contracting.subcontract.line'
    _description = 'بند أعمال عقد مقاولة الباطن (Subcontract Item Line)'
    _order = 'item_no, id'

    subcontract_id = fields.Many2one(
        'contracting.subcontract.agreement',
        string='عقد مقاولة الباطن',
        required=True,
        ondelete='cascade'
    )
    project_id = fields.Many2one(
        'project.project',
        related='subcontract_id.project_id',
        store=True,
        readonly=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='subcontract_id.currency_id',
        store=True,
        readonly=True
    )
    boq_id = fields.Many2one(
        'contracting.project.boq',
        string='بند جدول كميات المشروع المرتبط',
        domain="[('project_id', '=', project_id)]",
        help='الفقرة الأصلية المقابلة في جدول كميات المشروع.'
    )
    item_no = fields.Char(
        string='تسلسل الفقرة',
        required=True
    )
    name = fields.Text(
        string='وصف العمل والمواصفات',
        required=True
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='وحدة القياس',
        required=True
    )
    agreed_qty = fields.Float(
        string='الكمية المتفق عليها',
        digits='Product Unit of Measure',
        required=True,
        default=1.0
    )
    subcontract_unit_price = fields.Monetary(
        string='سعر الوحدة لمقاول الباطن',
        currency_field='currency_id',
        required=True,
        default=0.0,
        help='السعر الفعلي المتفق عليه مع مقاول الباطن (يختلف عن سعر رب العمل).'
    )
    subtotal = fields.Monetary(
        string='إجمالي قيمة الفقرة',
        currency_field='currency_id',
        compute='_compute_subtotal',
        store=True
    )

    @api.onchange('boq_id')
    def _onchange_boq_id(self):
        if self.boq_id:
            self.item_no = self.boq_id.item_no
            self.name = self.boq_id.name
            self.uom_id = self.boq_id.uom_id
            self.agreed_qty = self.boq_id.revised_contract_qty

    @api.depends('agreed_qty', 'subcontract_unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.agreed_qty * line.subcontract_unit_price
