import re
from database import reporting_dao
from utils_pyqt5 import format_currency
from views_pyqt5.reports.base_report import BaseReport, clean_text

class CustomerStatementReport(BaseReport):
    def __init__(self, customer_id, customer_name):
        super().__init__()
        self.customer_id = customer_id
        self.customer_name = customer_name

    def generate(self, start_date=None, end_date=None):
        lines = reporting_dao.get_customer_statement(self.customer_id)
        if not lines:
            self.html = f"<div style='text-align: center;'><h3>لا توجد حركات لهذا العميل</h3></div>"
            return self
        html = f"""
        <html dir="rtl"><head><meta charset="UTF-8"></head><body>
        <div style="text-align: center;"><h2>كشف حساب عميل</h2><h3>{clean_text(self.customer_name)}</h3><hr></div>
        <table style="width:100%; border-collapse:collapse;"><thead><tr style="background-color:#34495e; color:white;">
        <th>التاريخ</th><th>الوصف</th><th>مدين</th><th>دائن</th><th>الرصيد</th></tr></thead><tbody>"""
        for l in lines:
            desc = clean_text(l['description'])
            html += f"<tr><td style='padding:8px;'>{l['date']}浏<td style='padding:8px;'>{desc}浏<td style='text-align:center;'>{format_currency(l['debit'])}浏<td style='text-align:center;'>{format_currency(l['credit'])}浏<td style='text-align:center;'>{format_currency(l['balance'])}浏</tr>"
        html += "</tbody></table></body></html>"
        self.html = html
        return self
