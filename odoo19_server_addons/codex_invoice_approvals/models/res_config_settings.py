# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    invoice_approval = fields.Boolean(
        string="تفعيل دورة الموافقات المتسلسلة للفواتير",
        help="عند تفعيل هذا الخيار تمر الفواتير بالدورات المتسلسلة التالية: المحاسب -> المدير المالي -> المدقق -> المدير المفوض ثم الترحيل."
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        param_obj = self.env['ir.config_parameter'].sudo()
        val = param_obj.get_param('codex_invoice_approvals.invoice_approval', default=None)
        if val is None:
            val = param_obj.get_param('codex_invoice_approvals.enable_invoice_approvals', default='False')
        res['invoice_approval'] = (str(val).lower() in ['true', '1', 't', 'yes'])
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        val_str = 'True' if self.invoice_approval else 'False'
        self.env['ir.config_parameter'].sudo().set_param(
            'codex_invoice_approvals.invoice_approval',
            val_str
        )
        self.env['ir.config_parameter'].sudo().set_param(
            'codex_invoice_approvals.enable_invoice_approvals',
            val_str
        )
