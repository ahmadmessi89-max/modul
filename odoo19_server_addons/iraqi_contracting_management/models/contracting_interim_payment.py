# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ContractingInterimPayment(models.Model):
    _name = 'contracting.interim.payment'
    _description = 'السلفة المنجزة / الذرعة الشهرية (Interim Payment Certificate - IPC)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(
        string='رقم السلفة المنجزة / الذرعة',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('مسودة ذرعة جديدة'),
        tracking=True
    )
    ipc_type = fields.Selection([
        ('client', 'سلفة منجزة لرب العمل (Client IPC)'),
        ('subcontractor', 'سلفة منجزة لمقاول ثانوي (Subcontractor IPC)')
    ], string='نوع السلفة / الذرعة', required=True, default='client', tracking=True)

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
    partner_id = fields.Many2one(
        'res.partner',
        string='رب العمل / المقاول الثانوي',
        required=True,
        tracking=True,
        help='الجهة المصروف لها أو منها السلفة (رب العمل في سلف المالك، أو المقاول الثانوي في ذرعات المقاولين الباطن).'
    )
    subcontract_id = fields.Many2one(
        'contracting.subcontract.agreement',
        string='عقد مقاولة الباطن المرتبط',
        domain="[('project_id', '=', project_id), ('subcontractor_id', '=', partner_id)]",
        tracking=True,
        help='عقد مقاولة الباطن المعتمد والمحدد لأسعار وبنود هذا المقاول الثانوي.'
    )
    sequence_in_project = fields.Integer(
        string='تسلسل السلفة في المشروع',
        default=1,
        help='رقم السلفة التسلسلي ضمن هذا المشروع (مثلاً: السلفة 1، السلفة 2...).'
    )
    date = fields.Date(
        string='تاريخ إعداد الذرعة',
        default=fields.Date.context_today,
        required=True,
        tracking=True
    )
    period_start = fields.Date(
        string='تاريخ بداية فترة الذرعة',
        required=True
    )
    period_end = fields.Date(
        string='تاريخ نهاية فترة الذرعة',
        required=True
    )
    resident_engineer_id = fields.Many2one(
        'res.users',
        string='المهندس المقيم المدقق',
        default=lambda self: self.env.user,
        tracking=True
    )
    state = fields.Selection([
        ('draft', 'مسودة الذرعة'),
        ('site_audited', 'مدققة موقعياً من المهندس'),
        ('approved', 'معتمدة ومصادقة'),
        ('invoiced', 'مرحلة محاسبياً (تم إنشاء القيد)'),
        ('cancelled', 'ملغاة')
    ], string='الحالة', default='draft', tracking=True, index=True)

    line_ids = fields.One2many(
        'contracting.interim.payment.line',
        'ipc_id',
        string='بنود الأعمال المنفذة في الذرعة',
        copy=True
    )

    # Financial Totals & Iraqi Deductions
    gross_cumulative_amount = fields.Monetary(
        string='إجمالي الأعمال المنجزة التراكمية',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
        tracking=True,
        help='إجمالي القيمة التراكمية لكافة الأعمال المنفذة منذ بداية المشروع حتى نهاية فترة هذه الذرعة.'
    )
    previous_gross_amount = fields.Monetary(
        string='إجمالي الأعمال التراكمية السابقة',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
        help='إجمالي القيمة التراكمية المصادق عليها في السلفة السابقة.'
    )
    current_gross_amount = fields.Monetary(
        string='صافي إنجاز الفترة الحالية',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
        tracking=True,
        help='قيمة الأعمال المنفذة فعلياً خلال فترة هذه الذرعة = التراكمي الإجمالي - التراكمي السابق.'
    )

    # Deductions: Advance Payment & Retention
    advance_deduction_percent = fields.Float(
        string='نسبة استرداد السلفة التشغيلية (%)',
        default=lambda self: self.env.company.contracting_advance_deduction_percent or 10.0,
        help='النسبة المئوية المستقطعة من إنجاز الفترة الحالية لإطفاء السلفة الأولية/التشغيلية.'
    )
    advance_deduction_amount = fields.Monetary(
        string='مبلغ استرداد السلفة التشغيلية',
        currency_field='currency_id',
        compute='_compute_deductions',
        store=True,
        readonly=False,
        tracking=True,
        help='المبلغ المستقطع لإطفاء السلفة التشغيلية.'
    )

    retention_percent = fields.Float(
        string='نسبة أمانات الصيانة / الاستقطاعات النظامية (%)',
        default=lambda self: self.env.company.contracting_retention_percent or 10.0,
        help='النسبة المئوية المحتجزة كتأمينات صيانة وحسن تنفيذ حتى التسليم النهائي.'
    )
    retention_amount = fields.Monetary(
        string='مبلغ أمانات الصيانة / الاستقطاعات النظامية',
        currency_field='currency_id',
        compute='_compute_deductions',
        store=True,
        readonly=False,
        tracking=True,
        help='المبلغ المحتجز لحساب أمانات الصيانة.'
    )

    # Tax Withholding (الاستقطاع الضريبي المباشر - العراق)
    tax_deduction_percent = fields.Float(
        string='نسبة الاستقطاع الضريبي المباشر (%)',
        default=lambda self: getattr(self.env.company, 'contracting_tax_deduction_percent', 2.7),
        help='النسبة المئوية المستقطعة لحساب الأمانات الضريبية (الهيئة العامة للضرائب) لمقاولي الباطن.'
    )
    tax_deduction_amount = fields.Monetary(
        string='مبلغ الاستقطاع الضريبي المباشر',
        currency_field='currency_id',
        compute='_compute_deductions',
        store=True,
        readonly=False,
        tracking=True,
        help='مبلغ الأمانات الضريبية المحتجزة لصالح الهيئة العامة للضرائب.'
    )

    other_deductions_amount = fields.Monetary(
        string='استقطاعات وغرامات أخرى',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
        help='أي غرامات تأخيرية أو استقطاعات مواد ممنوحة أو فحوصات مختبرية.'
    )
    other_deductions_note = fields.Char(
        string='بيان الاستقطاعات الأخرى'
    )

    net_payable_amount = fields.Monetary(
        string='صافي المبلغ المستحق للصرف',
        currency_field='currency_id',
        compute='_compute_deductions',
        store=True,
        tracking=True,
        help='المبلغ الصافي المستحق الدفع بعد تنزيل كافة الاستقطاعات والأمانات = إنجاز الفترة - السلفة التشغيلية - أمانات الصيانة - الاستقطاعات الأخرى.'
    )

    invoice_id = fields.Many2one(
        'account.move',
        string='الفاتورة / القيد المحاسبي المولد',
        readonly=True,
        copy=False,
        help='الفاتورة الصادرة لرب العمل أو فاتورة المورد للمقاول الثانوي المترتبة على هذه الذرعة.'
    )
    notes = fields.Text(
        string='ملاحظات وتوصيات المهندس المقيم'
    )

    @api.onchange('project_id')
    def _onchange_project_id(self):
        if self.project_id:
            if self.ipc_type == 'client':
                self.partner_id = self.project_id.partner_id
            
            # Count previous IPCs for sequence
            prev_ipcs = self.search([
                ('project_id', '=', self.project_id.id),
                ('ipc_type', '=', self.ipc_type),
                ('state', '!=', 'cancelled')
            ])
            self.sequence_in_project = len(prev_ipcs) + 1

    @api.depends('line_ids.cumulative_amount', 'line_ids.previous_amount', 'line_ids.current_amount')
    def _compute_totals(self):
        for record in self:
            record.gross_cumulative_amount = sum(record.line_ids.mapped('cumulative_amount'))
            record.previous_gross_amount = sum(record.line_ids.mapped('previous_amount'))
            record.current_gross_amount = sum(record.line_ids.mapped('current_amount'))

    @api.depends('current_gross_amount', 'advance_deduction_percent', 'retention_percent', 'tax_deduction_percent', 'other_deductions_amount', 'ipc_type')
    def _compute_deductions(self):
        for record in self:
            # Advance Payment Amortization
            if record.advance_deduction_percent > 0:
                record.advance_deduction_amount = (record.current_gross_amount * record.advance_deduction_percent) / 100.0
            else:
                record.advance_deduction_amount = 0.0

            # Retention
            if record.retention_percent > 0:
                record.retention_amount = (record.current_gross_amount * record.retention_percent) / 100.0
            else:
                record.retention_amount = 0.0

            # Iraqi Tax Withholding (only on subcontractors)
            if record.ipc_type == 'subcontractor' and record.tax_deduction_percent > 0:
                record.tax_deduction_amount = (record.current_gross_amount * record.tax_deduction_percent) / 100.0
            else:
                record.tax_deduction_amount = 0.0

            # Net Payable
            record.net_payable_amount = record.current_gross_amount - (
                record.advance_deduction_amount + record.retention_amount + record.tax_deduction_amount + record.other_deductions_amount
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('مسودة ذرعة جديدة')) == _('مسودة ذرعة جديدة'):
                ipc_type = vals.get('ipc_type', 'client')
                seq_code = 'contracting.interim.payment.client' if ipc_type == 'client' else 'contracting.interim.payment.subcontractor'
                vals['name'] = self.env['ir.sequence'].next_by_code(seq_code) or _('IPC/NEW')
        return super().create(vals_list)

    def action_load_boq_lines(self):
        """Auto-populate IPC lines from Subcontract Agreement or Project BOQ with previous cumulative values."""
        self.ensure_one()
        if not self.project_id:
            raise UserError(_("يرجى اختيار المشروع أولاً!"))

        # Find previous approved IPC for this project to get previous quantities
        domain_prev = [
            ('project_id', '=', self.project_id.id),
            ('ipc_type', '=', self.ipc_type),
            ('state', 'in', ['approved', 'invoiced']),
            ('id', '!=', self.id)
        ]
        if self.subcontract_id:
            domain_prev.append(('subcontract_id', '=', self.subcontract_id.id))

        last_ipc = self.search(domain_prev, order='date desc, id desc', limit=1)

        prev_qty_map = {}
        if last_ipc:
            for l in last_ipc.line_ids:
                if l.boq_id:
                    prev_qty_map[l.boq_id.id] = l.cumulative_qty

        # Clear existing lines if draft
        self.line_ids.unlink()

        lines_to_create = []

        # If Subcontract Agreement is selected, populate from Subcontract lines
        if self.subcontract_id and self.subcontract_id.line_ids:
            for s_line in self.subcontract_id.line_ids:
                prev_qty = prev_qty_map.get(s_line.boq_id.id, 0.0) if s_line.boq_id else 0.0
                lines_to_create.append((0, 0, {
                    'boq_id': s_line.boq_id.id if s_line.boq_id else False,
                    'item_no': s_line.item_no,
                    'name': s_line.name,
                    'package_id': s_line.boq_id.package_id.id if s_line.boq_id else False,
                    'uom_id': s_line.uom_id.id,
                    'contract_qty': s_line.agreed_qty,
                    'unit_price': s_line.subcontract_unit_price,
                    'previous_qty': prev_qty,
                    'current_qty': 0.0,
                }))
        else:
            for boq in self.project_id.boq_line_ids.filtered(lambda b: b.state in ['confirmed', 'in_progress']):
                prev_qty = prev_qty_map.get(boq.id, boq.cumulative_qty or 0.0)
                lines_to_create.append((0, 0, {
                    'boq_id': boq.id,
                    'item_no': boq.item_no,
                    'name': boq.name,
                    'package_id': boq.package_id.id,
                    'uom_id': boq.uom_id.id,
                    'contract_qty': boq.revised_contract_qty,
                    'unit_price': boq.tender_unit_price,
                    'previous_qty': prev_qty,
                    'current_qty': 0.0,
                }))

        if lines_to_create:
            self.write({'line_ids': lines_to_create})
        else:
            raise UserError(_("لم يتم العثور على بنود معتمدة في جدول الكميات أو عقد مقاولة الباطن!"))

    # Workflow Actions
    def action_site_audit(self):
        for record in self:
            if not record.line_ids:
                raise UserError(_("لا يمكن تدقيق ذرعة لا تحتوي على أسطر أعمال منفذة!"))
            record.state = 'site_audited'

    def action_approve(self):
        for record in self:
            record.state = 'approved'
            # Trigger updates on BOQ
            for line in record.line_ids:
                if line.boq_id:
                    line.boq_id._compute_ipc_quantities()
                    line.boq_id._compute_completion_progress()

    def action_generate_invoice(self):
        """Generate official Customer Invoice or Vendor Bill with proper Iraqi retention and advance amortization entries."""
        self.ensure_one()
        if self.state not in ['approved']:
            raise UserError(_("يجب مصادقة واعتماد السلفة المنجزة قبل توليد القيد المحاسبي أو الفاتورة!"))

        company = self.company_id or self.env.company
        retention_account = company.retention_receivable_account_id if self.ipc_type == 'client' else company.retention_payable_account_id
        advance_account = company.advance_payment_account_id

        if self.retention_amount > 0 and not retention_account:
            raise UserError(_("يرجى ضبط حساب أمانات الصيانة والاستقطاعات النظامية في إعدادات الشركة قبل إصدار الفاتورة!"))

        move_type = 'out_invoice' if self.ipc_type == 'client' else 'in_invoice'
        
        # Build invoice lines
        invoice_lines = []

        # 1. Revenue/Expense lines per BOQ package or per line
        for line in self.line_ids.filtered(lambda l: l.current_amount > 0):
            analytic_distribution = {}
            if line.boq_id and line.boq_id.analytic_distribution:
                analytic_distribution = line.boq_id.analytic_distribution
            elif self.project_id.analytic_account_id:
                analytic_distribution = {str(self.project_id.analytic_account_id.id): 100.0}

            invoice_lines.append((0, 0, {
                'name': f"الذرعة رقم ({self.sequence_in_project}) - الفقرة [{line.item_no}]: {line.name[:50]}",
                'quantity': line.current_qty if line.current_qty > 0 else 1.0,
                'price_unit': line.unit_price if line.current_qty > 0 else line.current_amount,
                'analytic_distribution': analytic_distribution,
            }))

        # If all lines are 0 but current gross is positive
        if not invoice_lines and self.current_gross_amount > 0:
            analytic_distribution = {str(self.project_id.analytic_account_id.id): 100.0} if self.project_id.analytic_account_id else {}
            invoice_lines.append((0, 0, {
                'name': f"إجمالي الأعمال المنجزة - السلفة رقم ({self.sequence_in_project}) للمشروع {self.project_id.name}",
                'quantity': 1.0,
                'price_unit': self.current_gross_amount,
                'analytic_distribution': analytic_distribution,
            }))

        # 2. Deduction Line: Advance Payment Recovery ("استرداد السلفة التشغيلية")
        if self.advance_deduction_amount > 0:
            line_vals = {
                'name': f"استقطاع استرداد السلفة التشغيلية ({self.advance_deduction_percent}%) - السلفة رقم ({self.sequence_in_project})",
                'quantity': 1.0,
                'price_unit': -1.0 * self.advance_deduction_amount,
            }
            if advance_account:
                line_vals['account_id'] = advance_account.id
            invoice_lines.append((0, 0, line_vals))

        # 3. Deduction Line: Retention Money ("أمانات صيانة / استقطاعات نظامية")
        if self.retention_amount > 0:
            line_vals = {
                'name': f"استقطاع أمانات الصيانة وحسن التنفيذ ({self.retention_percent}%) - السلفة رقم ({self.sequence_in_project})",
                'quantity': 1.0,
                'price_unit': -1.0 * self.retention_amount,
            }
            if retention_account:
                line_vals['account_id'] = retention_account.id
            invoice_lines.append((0, 0, line_vals))

        # 4. Deduction Line: Iraqi Tax Withholding ("استقطاع الأمانات الضريبية")
        if self.tax_deduction_amount > 0:
            tax_account = getattr(company, 'tax_retention_payable_account_id', False)
            tax_line_vals = {
                'name': f"استقطاع الأمانات الضريبية المباشرة ({self.tax_deduction_percent}%) - السلفة رقم ({self.sequence_in_project})",
                'quantity': 1.0,
                'price_unit': -1.0 * self.tax_deduction_amount,
            }
            if tax_account:
                tax_line_vals['account_id'] = tax_account.id
            invoice_lines.append((0, 0, tax_line_vals))

        # 5. Other deductions
        if self.other_deductions_amount > 0:
            invoice_lines.append((0, 0, {
                'name': f"استقطاعات وغرامات أخرى: {self.other_deductions_note or 'استقطاعات موقعية'}",
                'quantity': 1.0,
                'price_unit': -1.0 * self.other_deductions_amount,
            }))

        move_vals = {
            'move_type': move_type,
            'partner_id': self.partner_id.id,
            'invoice_date': self.date,
            'date': self.date,
            'currency_id': self.currency_id.id,
            'ref': f"{self.name} - مشروع: {self.project_id.name}",
            'invoice_origin': self.name,
            'invoice_line_ids': invoice_lines,
        }

        invoice = self.env['account.move'].create(move_vals)
        self.write({
            'invoice_id': invoice.id,
            'state': 'invoiced'
        })

        return {
            'name': _('الفاتورة المولدة للسلفة المنجزة'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_("لم يتم توليد أي فاتورة لهذه السلفة بعد!"))
        return {
            'name': _('الفاتورة المرتبطة بالسلفة المنجزة'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_cancel(self):
        for record in self:
            record.state = 'cancelled'

    def action_reset_draft(self):
        for record in self:
            record.state = 'draft'


class ContractingInterimPaymentLine(models.Model):
    _name = 'contracting.interim.payment.line'
    _description = 'سطر الذرعة المنجزة (IPC Line Item)'
    _order = 'item_no, id'

    ipc_id = fields.Many2one(
        'contracting.interim.payment',
        string='السلفة المنجزة / الذرعة',
        required=True,
        ondelete='cascade'
    )
    project_id = fields.Many2one(
        'project.project',
        related='ipc_id.project_id',
        store=True,
        readonly=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='ipc_id.currency_id',
        store=True,
        readonly=True
    )
    boq_id = fields.Many2one(
        'contracting.project.boq',
        string='بند جدول الكميات والتسعير',
        domain="[('project_id', '=', project_id)]"
    )
    item_no = fields.Char(
        string='رقم الفقرة',
        required=True
    )
    name = fields.Text(
        string='وصف العمل المنفذ',
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
    unit_price = fields.Monetary(
        string='سعر الوحدة العقدي',
        currency_field='currency_id',
        required=True,
        default=0.0
    )
    contract_qty = fields.Float(
        string='الكمية العقدية المعدلة',
        digits='Product Unit of Measure',
        default=1.0
    )

    # Progress Quantities (Previous, Current, Cumulative)
    previous_qty = fields.Float(
        string='الذرعة التراكمية السابقة',
        digits='Product Unit of Measure',
        default=0.0,
        help='كمية الأعمال المنفذة التراكمية حتى نهاية الذرعة السابقة.'
    )
    current_qty = fields.Float(
        string='ذرعة الفترة الحالية',
        digits='Product Unit of Measure',
        default=0.0,
        required=True,
        help='كمية الأعمال المنفذة والمقاسة في الموقع خلال فترة هذه الذرعة.'
    )
    cumulative_qty = fields.Float(
        string='الذرعة التراكمية الإجمالية',
        digits='Product Unit of Measure',
        compute='_compute_cumulative_values',
        store=True,
        help='إجمالي الكميات المنفذة حتى تاريخ هذه الذرعة = السابقة + الحالية.'
    )
    completion_rate = fields.Float(
        string='نسبة الإنجاز (%)',
        compute='_compute_cumulative_values',
        store=True
    )

    # Progress Monetary Amounts
    previous_amount = fields.Monetary(
        string='المبلغ التراكمي السابق',
        currency_field='currency_id',
        compute='_compute_amounts',
        store=True
    )
    current_amount = fields.Monetary(
        string='مبلغ الفترة الحالية',
        currency_field='currency_id',
        compute='_compute_amounts',
        store=True
    )
    cumulative_amount = fields.Monetary(
        string='المبلغ التراكمي الإجمالي',
        currency_field='currency_id',
        compute='_compute_amounts',
        store=True
    )
    notes = fields.Char(
        string='ملاحظات الذرعة'
    )

    @api.onchange('boq_id')
    def _onchange_boq_id(self):
        if self.boq_id:
            self.item_no = self.boq_id.item_no
            self.name = self.boq_id.name
            self.package_id = self.boq_id.package_id
            self.uom_id = self.boq_id.uom_id
            self.contract_qty = self.boq_id.revised_contract_qty
            self.unit_price = self.boq_id.tender_unit_price
            self.previous_qty = self.boq_id.cumulative_qty

    @api.depends('previous_qty', 'current_qty', 'contract_qty')
    def _compute_cumulative_values(self):
        for line in self:
            line.cumulative_qty = line.previous_qty + line.current_qty
            if line.contract_qty > 0:
                line.completion_rate = (line.cumulative_qty / line.contract_qty) * 100.0
            else:
                line.completion_rate = 0.0

    @api.depends('previous_qty', 'current_qty', 'cumulative_qty', 'unit_price')
    def _compute_amounts(self):
        for line in self:
            line.previous_amount = line.previous_qty * line.unit_price
            line.current_amount = line.current_qty * line.unit_price
            line.cumulative_amount = line.cumulative_qty * line.unit_price
