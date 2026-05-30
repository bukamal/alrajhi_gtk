import re
from database import reporting_dao
from utils_pyqt5 import format_currency
from views_pyqt5.reports.base_report import BaseReport, clean_text

class TrialBalanceReport(BaseReport):
    def generate(self, start_date=None, end_date=None):
        trial = reporting_dao.get_trial_balance_filtered(start_date, end_date)
        html = """<html dir="rtl"><head><meta charset="UTF-8"></head><body>
        <div style="text-align: center;"><h2>ميزان المراجعة</h2><hr></div>
        <table style="width:100%; border-collapse:collapse;"><thead><tr style="background-color:#34495e; color:white;">
        <th style="padding:8px;">الحساب</th><th style="padding:8px;">مدين</th><th style="padding:8px;">دائن</th> <tr></thead><tbody>"""
        total_debit = 0
        total_credit = 0
        for row in trial:
            if row['debit'] == 0 and row['credit'] == 0:
                continue
            name = clean_text(row['name'])
            debit = row['debit']
            credit = row['credit']
            total_debit += debit
            total_credit += credit
            html += f"<tr><td style='padding:8px;'>{name}浏<td style='padding:8px; text-align:center;'>{format_currency(debit)}浏<td style='padding:8px; text-align:center;'>{format_currency(credit)}浏</tr>"
        html += f"<tr style='background-color:#ecf0f1; font-weight:bold;'><td style='padding:8px;'>الإجمالي浏<td style='padding:8px; text-align:center;'>{format_currency(total_debit)}浏<td style='padding:8px; text-align:center;'>{format_currency(total_credit)}浏</tr>"
        html += "</tbody></table></body></html>"
        self.html = html
        return self
