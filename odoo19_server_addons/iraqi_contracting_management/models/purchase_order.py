# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    project_id = fields.Many2one(
        'project.project',
        string='المشروع الإنشائي',
        help='ربط أمر الشراء بالمشروع الإنشائي لضبط ومراقبة ميزانية بنود جدول الكميات.'
    )

    def button_confirm(self):
        """Enforce strict Iraqi budget validation against contracting BOQ lines upon PO confirmation."""
        for order in self:
            for line in order.order_line:
                if line.boq_id:
                    boq = line.boq_id
                    # Calculate line amount in project/company currency
                    line_amount = line.price_subtotal
                    if order.currency_id != boq.currency_id:
                        line_amount = order.currency_id._convert(
                            line.price_subtotal,
                            boq.currency_id,
                            order.company_id,
                            order.date_order or fields.Date.today()
                        )

                    # Check remaining budget
                    if boq.total_estimated_budget > 0 and line_amount > boq.remaining_budget:
                        currency_symbol = boq.currency_id.symbol or boq.currency_id.name or ''
                        raise UserError(
                            _(
                                "تنبيه رقابي: تجاوزت القيمة المتبقية من ميزانية جدول الكميات لهذا البند. "
                                "يرجى مراجعة المهندس المقيم أو استخراج (أمر غيار) معتمد.\n\n"
                                "تفاصيل الرقابة:\n"
                                "- رقم الفقرة: %s\n"
                                "- وصف البند: %s\n"
                                "- إجمالي موازنة التكلفة التقديرية: %s %s\n"
                                "- إجمالي المنفق والمحجوز سابقاً: %s %s\n"
                                "- الرصيد المتبقي المتاح: %s %s\n"
                                "- القيمة المطلوبة في أمر الشراء الحالي: %s %s"
                            ) % (
                                boq.item_no,
                                boq.name[:100],
                                "{:,.2f}".format(boq.total_estimated_budget), currency_symbol,
                                "{:,.2f}".format(boq.total_incurred_cost), currency_symbol,
                                "{:,.2f}".format(boq.remaining_budget), currency_symbol,
                                "{:,.2f}".format(line_amount), currency_symbol
                            )
                        )
        return super().button_confirm()


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    project_id = fields.Many2one(
        'project.project',
        string='المشروع الإنشائي',
        related='order_id.project_id',
        store=True,
        readonly=False
    )
    boq_id = fields.Many2one(
        'contracting.project.boq',
        string='بند جدول الكميات والتسعير',
        domain="[('project_id', '=', project_id)]",
        help='الفقرة المرتبطة من جدول الكميات والتسعير لخصم وتتبع الموازنة.'
    )
    package_id = fields.Many2one(
        'contracting.boq.package',
        string='حزمة العمل',
        related='boq_id.package_id',
        store=True,
        readonly=True
    )
    cost_element_id = fields.Many2one(
        'contracting.cost.element',
        string='عنصر التكلفة (مواد / مقاول باطن / آليات / أجور)',
        help='التبويب التحليلي لنوع المصروف الإنشائي.'
    )

    @api.onchange('boq_id', 'cost_element_id', 'project_id')
    def _onchange_contracting_analytic_distribution(self):
        """Automatically construct 3D analytic distribution (Project, BOQ Package, Cost Element)."""
        distribution = {}
        if self.project_id and self.project_id.analytic_account_id:
            distribution[str(self.project_id.analytic_account_id.id)] = 100.0
        if self.boq_id and self.boq_id.package_id and self.boq_id.package_id.analytic_account_id:
            distribution[str(self.boq_id.package_id.analytic_account_id.id)] = 100.0
        if self.cost_element_id and self.cost_element_id.analytic_account_id:
            distribution[str(self.cost_element_id.analytic_account_id.id)] = 100.0

        if distribution:
            self.analytic_distribution = distribution
