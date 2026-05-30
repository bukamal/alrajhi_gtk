import re
from database import reporting_dao
from utils_pyqt5 import format_currency
from views_pyqt5.reports.base_report import BaseReport, clean_text

class IncomeStatementReport(BaseReport):
    def generate(self, start_date=None, end_date=None):
        stmt = reporting_dao.get_income_statement_filtered(start_date, end_date)
        html = """<html dir="rtl"><head><meta charset="UTF-8"></head><body>
        <div style="text-align: center;"><h2>قائمة الدخل</h2><hr></div>
        <h3>الإيرادات</h3><table style="width:100%; border-collapse:collapse;"><thead><tr style="background-color:#2ecc71; color:white;"><th>الحساب</th><th>الرصيد</th></tr></thead><tbody>"""
        for inc in stmt['income']:
            html += f"<tr><td style='padding:8px;'>{clean_text(inc['name'])}浏<td style='text-align:center;'>{format_currency(inc['balance'])}浏</tr>"
        html += f"<tr style='background-color:#ecf0f1; font-weight:bold;'><td>إجمالي الإيرادات浏<td style='text-align:center;'>{format_currency(stmt['total_income'])}浏<tr>"
        html += "</tbody><table><h3>المصروفات</h3><table style='width:100%; border-collapse:collapse;'><thead><tr style='background-color:#f39c12; color:white;'><th>الحساب</th><th>الرصيد</th><tr></thead><tbody>"
        for exp in stmt['expenses']:
            html += f"<tr><td style='padding:8px;'>{clean_text(exp['name'])}浏<td style='text-align:center;'>{format_currency(exp['balance'])}浏</tr>"
        html += f"<tr style='background-color:#ecf0f1; font-weight:bold;'><td>إجمالي المصروفات浏<td style='text-align:center;'>{format_currency(stmt['total_expenses'])}浏</tr>"
        html += f"<tr style='background-color:#3498db; color:white; font-weight:bold;'><td>صافي الربح浏<td style='text-align:center;'>{format_currency(stmt['net_profit'])}浏</tr>"
        html += "</tbody></table></body></html>"
        self.html = html
        return self
