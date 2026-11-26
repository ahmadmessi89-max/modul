# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class AccountMove(models.Model):
    _inherit = 'account.move'

    state = fields.Selection(
        selection_add=[
            ('waiting_accountant', 'بانتظار موافقة المحاسب'),
            ('waiting_financial_manager', 'بانتظار موافقة المدير المالي'),
            ('waiting_auditor', 'بانتظار موافقة المدقق'),
            ('waiting_managing_director', 'بانتظار موافقة المدير المفوض'),
        ],
        ondelete={
            'waiting_accountant': 'cascade',
            'waiting_financial_manager': 'cascade',
            'waiting_auditor': 'cascade',
            'waiting_managing_director': 'cascade',
        }
    )

    status_in_payment = fields.Selection(
        selection_add=[
            ('waiting_accountant', 'بانتظار موافقة المحاسب'),
            ('waiting_financial_manager', 'بانتظار موافقة المدير المالي'),
            ('waiting_auditor', 'بانتظار موافقة المدقق'),
            ('waiting_managing_director', 'بانتظار موافقة المدير المفوض'),
        ],
        ondelete={
            'waiting_accountant': 'cascade',
            'waiting_financial_manager': 'cascade',
            'waiting_auditor': 'cascade',
            'waiting_managing_director': 'cascade',
        }
    )

    is_approvals_enabled = fields.Boolean(
        string='دورة الموافقات مفعلة',
        compute='_compute_is_approvals_enabled',
        store=False
    )

    def _compute_status_in_payment(self):
        super()._compute_status_in_payment()
        for move in self:
            if move.state in ['waiting_accountant', 'waiting_financial_manager', 'waiting_auditor', 'waiting_managing_director']:
                move.status_in_payment = move.state

    @api.model
    def _is_invoice_approvals_enabled(self):
        param_obj = self.env['ir.config_parameter'].sudo()
        val = param_obj.get_param('codex_invoice_approvals.invoice_approval', default=None)
        if val is None:
            val = param_obj.get_param('codex_invoice_approvals.enable_invoice_approvals', default='False')
        return str(val).lower() in ['true', '1', 't', 'yes']

    def _compute_is_approvals_enabled(self):
        is_on = self._is_invoice_approvals_enabled()
        for move in self:
            move.is_approvals_enabled = is_on

    def action_request_approval(self):
        for move in self:
            if move.state != 'draft':
                raise ValidationError(_("يمكن طلب الموافقة فقط للفواتير في حالة المسوّدة."))
            is_fin_manager = self.env.user.has_group('codex_invoice_approvals.group_approval_financial_manager')
            if is_fin_manager:
                move.state = 'waiting_auditor'
                move.status_in_payment = 'waiting_auditor'
            else:
                move.state = 'waiting_accountant'
                move.status_in_payment = 'waiting_accountant'

    def action_approve_accountant(self):
        for move in self:
            is_accountant = self.env.user.has_group('codex_invoice_approvals.group_approval_accountant') or self.env.user.has_group('codex_invoice_approvals.group_approval_financial_manager')
            if not is_accountant:
                raise ValidationError(_("عذراً! لا تمتلك صلاحية موافقة المحاسب."))
            if move.state != 'waiting_accountant':
                raise ValidationError(_("الفاتورة ليست في حالة بانتظار موافقة المحاسب."))
            move.state = 'waiting_financial_manager'
            move.status_in_payment = 'waiting_financial_manager'

    def action_approve_financial_manager(self):
        for move in self:
            is_fin_manager = self.env.user.has_group('codex_invoice_approvals.group_approval_financial_manager')
            if not is_fin_manager:
                raise ValidationError(_("عذراً! لا تمتلك صلاحية موافقة المدير المالي."))
            if move.state not in ['waiting_accountant', 'waiting_financial_manager']:
                raise ValidationError(_("الفاتورة ليست في مرحلة تتطلب موافقة المدير المالي."))
            move.state = 'waiting_auditor'
            move.status_in_payment = 'waiting_auditor'

    def action_approve_auditor(self):
        for move in self:
            is_auditor = self.env.user.has_group('codex_invoice_approvals.group_approval_auditor')
            if not is_auditor:
                raise ValidationError(_("عذراً! لا تمتلك صلاحية موافقة المدقق."))
            if move.state != 'waiting_auditor':
                raise ValidationError(_("الفاتورة ليست في حالة بانتظار موافقة المدقق."))
            move.sudo().state = 'waiting_managing_director'
            move.sudo().status_in_payment = 'waiting_managing_director'

    def action_approve_managing_director(self):
        for move in self:
            is_director = self.env.user.has_group('codex_invoice_approvals.group_approval_managing_director')
            if not is_director:
                raise ValidationError(_("عذراً! لا تمتلك صلاحية موافقة المدير المفوض للترحيل والاعتماد النهائي."))
            if move.state != 'waiting_managing_director':
                raise ValidationError(_("الفاتورة ليست في حالة بانتظار موافقة المدير المفوض."))
            super(AccountMove, move.sudo()).action_post()

    def action_reject(self):
        custom_states = ['waiting_accountant', 'waiting_financial_manager', 'waiting_auditor', 'waiting_managing_director']
        for move in self:
            if move.state in custom_states:
                # Direct SQL update to bypass Odoo's button_draft() constraint
                self.env.cr.execute(
                    "UPDATE account_move SET state = 'draft' WHERE id = %s",
                    (move.id,)
                )
                move.invalidate_recordset()
            elif move.state in ['posted', 'cancel']:
                move.sudo().button_draft()

    def action_post(self):
        if self._is_invoice_approvals_enabled():
            for move in self:
                if move.state not in ['draft', 'posted', 'cancel']:
                    if move.state == 'waiting_managing_director':
                        is_director = self.env.user.has_group('codex_invoice_approvals.group_approval_managing_director')
                        if is_director:
                            continue
                    raise ValidationError(_("نظام الموافقات المتسلسلة مفعل. يرجى الضغط على زر 'طلب موافقة' للبدء بدورة الموافقات أو التواصل مع المسؤول."))
                elif move.state == 'draft':
                    raise ValidationError(_("نظام الموافقات المتسلسلة مفعل. يرجى الضغط على زر 'طلب موافقة' للبدء بدورة الموافقات أو التواصل مع المسؤول."))
        return super().action_post()
