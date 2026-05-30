import re
from database import reporting_dao
from utils_pyqt5 import format_currency
from views_pyqt5.reports.base_report import BaseReport, clean_text

class SupplierStatementReport(BaseReport):
    def __init__(self, supplier_id, supplier_name):
        super().__init__()
        self.supplier_id = supplier_id
        self.supplier_name = supplier_name

    def generate(self, start_date=None, end_date=None):
        lines = reporting_dao.get_supplier_statement(self.supplier_id)
        if not lines:
            self.html = f"<div style='text-align: center;'><h3>لا توجد حركات لهذا المورد</h3></div>"
            return self
        html = f"""
        <html dir="rtl"><head><meta charset="UTF-8"></head><body>
        <div style="text-align: center;"><h2>كشف حساب مورد</h2><h3>{clean_text(self.supplier_name)}</h3><hr></div>
        <table style="width:100%; border-collapse:collapse;"><thead><tr style="background-color:#34495e; color:white;">
        <th>التاريخ</th><th>الوصف</th><th>مدين</th><th>دائن</th><th>الرصيد</th></td></thead><tbody>"""
        for l in lines:
            desc = clean_text(l['description'])
            html += f"<tr><td style='padding:8px;'>{l['date']}浏<td style='padding:8px;'>{desc}浏<td style='text-align:center;'>{format_currency(l['debit'])}浏<td style='text-align:center;'>{format_currency(l['credit'])}浏<td style='text-align:center;'>{format_currency(l['balance'])}浏</tr>"
        html += "</tbody></td></body></html>"
        self.html = html
        return self
