from odoo import models, fields, api, _


class IraqiTenderCompetitor(models.Model):
    _name = 'iraqi.tender.competitor'
    _description = 'عطاء منافس عند فتح المظاريف (Competitor Bid)'
    _order = 'bid_amount asc, id desc'

    tender_id = fields.Many2one(
        'iraqi.tender.announcement',
        string='المناقصة المرتبطة',
        required=True,
        ondelete='cascade',
        index=True
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='الشركة المنافسة',
        required=True
    )
    bid_amount = fields.Monetary(
        string='مبلغ العطاء المقدم من المنافس',
        currency_field='currency_id',
        required=True
    )
    financial_rank = fields.Integer(string='الترتيب المالي')
    is_awarded = fields.Boolean(string='تمت الإحالة على هذه الشركة')
    has_bid_bond = fields.Boolean(string='مقدم كفالة مصرفية', default=True)
    technical_compliance = fields.Selection([
        ('compliant', 'مطابق للمواصفات'),
        ('partially_compliant', 'مطابق جزئياً مع تحفظات'),
        ('non_compliant', 'مستبعد / غير مطابق فندياً')
    ], string='الموقف الفني', default='compliant')
    notes = fields.Char(string='ملاحظات / أسباب الاستبعاد أو التفوق')
    currency_id = fields.Many2one(
        'res.currency',
        string='العملة',
        related='tender_id.currency_id',
        store=True,
        readonly=True
    )
