# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ContractingPettyCash(models.Model):
    _name = 'contracting.petty.cash'
    _description = 'سلفة نقدية موقعية / ذمة المهندس (Site Petty Cash & Expenses)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(
        string='رقم كشف السلفة الموقعية',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('مسودة كشف سلفة'),
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
    engineer_id = fields.Many2one(
        'res.users',
        string='مهندس الموقع (صاحب الذمة)',
        default=lambda self: self.env.user,
        required=True,
        tracking=True
    )
    resident_engineer_id = fields.Many2one(
        'res.users',
        string='المهندس المقيم المشرف',
        tracking=True
    )
    date = fields.Date(
        string='تاريخ تسوية الكشف',
        default=fields.Date.context_today,
        required=True,
        tracking=True
    )
    custody_amount = fields.Monetary(
        string='مبلغ السلفة النقدية المستلمة (العهدة)',
        currency_field='currency_id',
        default=0.0,
        required=True,
        tracking=True,
        help='إجمالي النقد المسلم لمهندس الموقع كنفقات نثرية وموقعية عاجلة.'
    )
    total_spent_amount = fields.Monetary(
        string='إجمالي المصروفات المنفقة بموجب الوصولات',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
        tracking=True
    )
    balance_remaining = fields.Monetary(
        string='المتبقي بذمة المهندس',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
        tracking=True
    )
    state = fields.Selection([
        ('draft', 'مسودة'),
        ('submitted', 'مقدم للمهندس المقيم'),
        ('approved', 'معتمد فنياً من المهندس المقيم'),
        ('settled', 'تمت التسوية المالية والقيد المحاسبي')
    ], string='الحالة', default='draft', tracking=True, index=True)

    line_ids = fields.One2many(
        'contracting.petty.cash.line',
        'petty_cash_id',
        string='وصولات ومصروفات السلفة الموقعية',
        copy=True
    )
    notes = fields.Text(
        string='ملاحظات وتفاصيل الكشف'
    )

    @api.depends('custody_amount', 'line_ids.amount')
    def _compute_totals(self):
        for record in self:
            spent = sum(record.line_ids.mapped('amount'))
            record.total_spent_amount = spent
            record.balance_remaining = record.custody_amount - spent

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('مسودة كشف سلفة')) == _('مسودة كشف سلفة'):
                vals['name'] = self.env['ir.sequence'].next_by_code('contracting.petty.cash') or _('PC/NEW')
        return super().create(vals_list)

    def action_submit(self):
        for record in self:
            if not record.line_ids:
                raise UserError(_("لا يمكن تقديم كشف سلفة فارغ بدون وصولات صرف!"))
            record.state = 'submitted'

    def action_approve(self):
        for record in self:
            record.state = 'approved'

    def action_settle(self):
        for record in self:
            record.state = 'settled'

    def action_reset_draft(self):
        for record in self:
            record.state = 'draft'


class ContractingPettyCashLine(models.Model):
    _name = 'contracting.petty.cash.line'
    _description = 'سطر مصروف السلفة الموقعية (Petty Cash Expense Item)'
    _order = 'date desc, id desc'

    petty_cash_id = fields.Many2one(
        'contracting.petty.cash',
        string='كشف السلفة النقدية',
        required=True,
        ondelete='cascade'
    )
    project_id = fields.Many2one(
        'project.project',
        related='petty_cash_id.project_id',
        store=True,
        readonly=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='petty_cash_id.currency_id',
        store=True,
        readonly=True
    )
    date = fields.Date(
        string='تاريخ الوصل',
        default=fields.Date.context_today,
        required=True
    )
    receipt_no = fields.Char(
        string='رقم الوصل / الفاتورة الموقعية',
        required=True
    )
    name = fields.Char(
        string='بيان المصروف الموقعي',
        required=True,
        help='مثلاً: شراء وقود مولدة الموقع، أجور تفريغ شحنة طابوق، نثريات ضيافة المهندس المقيم.'
    )
    boq_id = fields.Many2one(
        'contracting.project.boq',
        string='بند جدول الكميات المستفيد',
        domain="[('project_id', '=', project_id)]",
        help='ربط المصروف بالبند الإنشائي المستفيد لتنزيل التكلفة من ميزانيته.'
    )
    cost_element_id = fields.Many2one(
        'contracting.cost.element',
        string='عنصر التكلفة',
        required=True
    )
    amount = fields.Monetary(
        string='مبلغ الوصل',
        currency_field='currency_id',
        required=True,
        default=0.0
    )
    receipt_image = fields.Binary(
        string='صورة الوصل / المستند المرفق',
        attachment=True,
        help='صورة أو مسح ضوئي لوصل الصرف الموقعي.'
    )
