import re
from database import reporting_dao
from utils_pyqt5 import format_currency
from views_pyqt5.reports.base_report import BaseReport, clean_text

class BalanceSheetReport(BaseReport):
    def generate(self, start_date=None, end_date=None):
        bs = reporting_dao.get_balance_sheet_filtered(start_date, end_date)
        html = """<html dir="rtl"><head><meta charset="UTF-8"></head><body>
        <div style="text-align: center;"><h2>الميزانية العمومية</h2><hr></div>
        <h3>الأصول</h3><table style="width:100%; border-collapse:collapse;"><thead><tr style="background-color:#3498db; color:white;"><th>الحساب</th><th>الرصيد</th></tr></thead><tbody>"""
        for a in bs['assets']:
            html += f"<tr><td style='padding:8px;'>{clean_text(a['name'])}浏<td style='text-align:center;'>{format_currency(a['debit'])}浏</tr>"
        html += f"<tr style='background-color:#ecf0f1; font-weight:bold;'><td>إجمالي الأصول浏<td style='text-align:center;'>{format_currency(bs['total_assets'])}浏</tr>"
        html += "</tbody></table><h3>الخصوم</h3><table style='width:100%; border-collapse:collapse;'><thead><tr style='background-color:#f39c12; color:white;'><th>الحساب</th><th>الرصيد</th><tr></thead><tbody>"
        for l in bs['liabilities']:
            html += f"<tr><td style='padding:8px;'>{clean_text(l['name'])}浏<td style='text-align:center;'>{format_currency(l['credit'])}浏<tr>"
        html += f"<tr style='background-color:#ecf0f1; font-weight:bold;'><td>إجمالي الخصوم浏<td style='text-align:center;'>{format_currency(bs['total_liabilities'])}浏</tr>"
        html += "</tbody></table><h3>حقوق الملكية</h3><table style='width:100%; border-collapse:collapse;'><thead><tr style='background-color:#2ecc71; color:white;'><th>الحساب</th><th>الرصيد</th></tr></thead><tbody>"
        for e in bs['equity']:
            html += f"<tr><td style='padding:8px;'>{clean_text(e['name'])}浏<td style='text-align:center;'>{format_currency(e['credit'])}浏</tr>"
        html += f"<tr style='background-color:#ecf0f1; font-weight:bold;'><td>إجمالي حقوق الملكية浏<td style='text-align:center;'>{format_currency(bs['total_equity'])}浏</tr>"
        html += "</tbody></table></body></html>"
        self.html = html
        return self
