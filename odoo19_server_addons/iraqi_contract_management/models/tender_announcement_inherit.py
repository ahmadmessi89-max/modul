from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class IraqiTenderAnnouncement(models.Model):
    _inherit = 'iraqi.tender.announcement'

    contract_ids = fields.One2many(
        'direct.supply.contract',
        'tender_id',
        string='عقود التجهيز المبرمة'
    )
    contract_count = fields.Integer(
        string='عدد العقود المبرمة',
        compute='_compute_contract_count'
    )

    @api.depends('contract_ids')
    def _compute_contract_count(self):
        for record in self:
            record.contract_count = len(record.contract_ids)

    def action_generate_contract(self):
        self.ensure_one()
        if self.contract_ids:
            return self.action_view_contracts()

        contract_lines = []
        for tline in self.line_ids:
            contract_lines.append((0, 0, {
                'name': tline.name or (tline.product_id.name if tline.product_id else 'بند تجهيز'),
                'product_id': tline.product_id.id if tline.product_id else False,
                'quantity': tline.quantity,
                'uom_id': tline.uom_id.id if tline.uom_id else False,
                'unit_price': tline.unit_price,
                'notes': tline.notes or '',
            }))

        contract_vals = {
            'tender_id': self.id,
            'contract_number': self.tender_number or (_('عقد-') + (self.name or '')),
            'contract_subject': self.tender_title or '',
            'beneficiary_id': self.beneficiary_id.id if self.beneficiary_id else False,
            'vendor_id': self.company_id.partner_id.id if self.company_id.partner_id else (self.beneficiary_id.id if self.beneficiary_id else False),
            'department_id': self.department_id.id if self.department_id else False,
            'responsible_user_id': self.responsible_user_id.id if self.responsible_user_id else self.env.uid,
            'currency_id': self.currency_id.id if self.currency_id else self.env.company.currency_id.id,
            'contract_date': self.award_letter_date or fields.Date.context_today(self),
            'expected_delivery_date': self.submission_deadline.date() if self.submission_deadline else fields.Date.context_today(self),
            'contract_tender_value': self.awarded_amount or self.total_bid_amount,
            'line_ids': contract_lines,
            'state': 'draft',
        }

        contract = self.env['direct.supply.contract'].create(contract_vals)
        self.write({'state': 'contracted'})

        return {
            'name': _('عقد التجهيز والمقاولة المبرم'),
            'type': 'ir.actions.act_window',
            'res_model': 'direct.supply.contract',
            'res_id': contract.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_contracts(self):
        self.ensure_one()
        contracts = self.contract_ids
        if len(contracts) == 1:
            return {
                'name': _('عقد التجهيز المبرم'),
                'type': 'ir.actions.act_window',
                'res_model': 'direct.supply.contract',
                'res_id': contracts[0].id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            return {
                'name': _('عقود التجهيز المبرمة'),
                'type': 'ir.actions.act_window',
                'res_model': 'direct.supply.contract',
                'view_mode': 'list,form',
                'domain': [('tender_id', '=', self.id)],
                'context': {'default_tender_id': self.id},
            }
