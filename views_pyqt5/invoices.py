# views_pyqt5/invoices.py
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QTableView,
                             QHeaderView, QMessageBox, QDialog, QLabel, QListWidget, QComboBox, QDateEdit)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor
from database import invoice_dao, customer_dao, supplier_dao
from utils_pyqt5 import format_currency, show_toast
from views_pyqt5.invoice_dialog import InvoiceDialog
from views_pyqt5.base_table_model import BaseTableModel
from views_pyqt5.modern_table import ModernTableView
from views_pyqt5.base_widget import BaseWidget
from views_pyqt5.centered_dialog import CenteredDialog
import traceback

class InvoicesWidget(BaseWidget):
    entity_name = "الفاتورة"
    search_placeholder = "بحث عن فاتورة..."
    headers = ["#", "النوع", "المرجع", "التاريخ", "الإجمالي", "المتبقي"]
    has_delete = True
    has_add = False
    has_export = True
    has_print = True
    has_pagination = True
    page_size = 50

    def __init__(self, parent=None):
        self.type_filter = QComboBox()
        self.start_date = QDateEdit()
        self.end_date = QDateEdit()
        self.entity_filter = QComboBox()
        super().__init__(parent)
        self.init_filters()
        self.load_customers_suppliers()
        self.add_custom_buttons()

    def add_custom_buttons(self):
        self.sale_btn = QPushButton("💰 فاتورة بيع جديدة")
        self.sale_btn.setObjectName("primary")
        self.sale_btn.clicked.connect(lambda: self.create_invoice('sale'))

        self.purchase_btn = QPushButton("📦 فاتورة شراء جديدة")
        self.purchase_btn.setObjectName("success")
        self.purchase_btn.clicked.connect(lambda: self.create_invoice('purchase'))

        if hasattr(self, 'delete_btn') and self.delete_btn:
            index = self.btn_layout.indexOf(self.delete_btn)
            self.btn_layout.insertWidget(index + 1, self.sale_btn)
            self.btn_layout.insertWidget(index + 2, self.purchase_btn)
        else:
            self.btn_layout.insertWidget(0, self.sale_btn)
            self.btn_layout.insertWidget(1, self.purchase_btn)

    def init_filters(self):
        filter_layout = QHBoxLayout()
        self.type_filter.addItem("الكل", "")
        self.type_filter.addItem("بيع", "sale")
        self.type_filter.addItem("شراء", "purchase")
        self.type_filter.currentIndexChanged.connect(self.refresh)
        filter_layout.addWidget(QLabel("النوع:"))
        filter_layout.addWidget(self.type_filter)

        filter_layout.addWidget(QLabel("من تاريخ:"))
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.start_date.setCalendarPopup(True)
        self.start_date.dateChanged.connect(self.refresh)
        filter_layout.addWidget(self.start_date)

        filter_layout.addWidget(QLabel("إلى تاريخ:"))
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        self.end_date.dateChanged.connect(self.refresh)
        filter_layout.addWidget(self.end_date)

        filter_layout.addWidget(QLabel("عميل/مورد:"))
        self.entity_filter.addItem("الكل", None)
        filter_layout.addWidget(self.entity_filter)

        filter_layout.addStretch()
        self.layout.insertLayout(2, filter_layout)

    def load_customers_suppliers(self):
        customers = customer_dao.get_all()
        suppliers = supplier_dao.get_all()
        self.entity_filter.clear()
        self.entity_filter.addItem("الكل", None)
        for c in customers:
            self.entity_filter.addItem(f"عميل: {c.name}", ('customer', c.id))
        for s in suppliers:
            self.entity_filter.addItem(f"مورد: {s.name}", ('supplier', s.id))

    def get_total_count(self, search=None):
        inv_type = self.type_filter.currentData()
        start_date = self.start_date.date().toString("yyyy-MM-dd")
        end_date = self.end_date.date().toString("yyyy-MM-dd")
        entity = self.entity_filter.currentData()
        entity_id = entity[1] if entity else None
        entity_type = entity[0] if entity else None
        invoices = invoice_dao.get_all(
            search=search if search else None,
            inv_type=inv_type if inv_type else None,
            start_date=start_date,
            end_date=end_date,
            customer_id=entity_id if entity_type == 'customer' else None,
            supplier_id=entity_id if entity_type == 'supplier' else None
        )
        return len(invoices) if invoices else 0

    def fetch_data(self, search=None, limit=None, offset=None):
        inv_type = self.type_filter.currentData()
        start_date = self.start_date.date().toString("yyyy-MM-dd")
        end_date = self.end_date.date().toString("yyyy-MM-dd")
        entity = self.entity_filter.currentData()
        entity_id = entity[1] if entity else None
        entity_type = entity[0] if entity else None

        invoices = invoice_dao.get_all(
            search=search if search else None,
            inv_type=inv_type if inv_type else None,
            start_date=start_date,
            end_date=end_date,
            customer_id=entity_id if entity_type == 'customer' else None,
            supplier_id=entity_id if entity_type == 'supplier' else None
        )
        if invoices is None:
            return []
        if limit is not None and offset is not None:
            return invoices[offset:offset+limit]
        return invoices

    def prepare_table_data(self, items):
        data = []
        self.row_colors = []
        for inv in items:
            typ = "بيع" if inv.type == 'sale' else "شراء"
            total = inv.total
            paid = inv.paid
            remaining = total - paid
            data.append([
                inv.id,
                typ,
                inv.reference,
                inv.date,
                format_currency(total),
                format_currency(remaining)
            ])
            self.row_colors.append(remaining > 0)
        return data

    def after_refresh(self):
        for row, is_overdue in enumerate(self.row_colors):
            if is_overdue:
                self.model.set_row_background(row, QColor(255, 240, 240))

    def delete_item(self, item_id):
        invoice_dao.delete_invoice(item_id)

    def create_invoice(self, inv_type):
        try:
            dialog = InvoiceDialog(inv_type, self)
            if dialog.exec() == QDialog.Accepted:
                self.refresh()
        except Exception as e:
            show_toast(f"خطأ في إنشاء الفاتورة: {str(e)}", "error", self)

    def on_double_click(self, index):
        row = index.row()
        if row < 0 or not hasattr(self, 'model') or row >= len(self.model._data):
            return
        inv_id = self.model._data[row][0]
        inv = invoice_dao.get_by_id(inv_id)
        if not inv:
            show_toast("الفاتورة غير موجودة", "error", self)
            return
        self.show_invoice_detail(inv)

    def show_invoice_detail(self, inv):
        try:
            dialog = CenteredDialog(self)
            dialog.setWindowTitle(f"فاتورة {inv.reference}")
            dialog.setModal(True)
            dialog.setLayoutDirection(Qt.RightToLeft)
            dialog.resize(600, 500)
            layout = QVBoxLayout(dialog)

            inv_type = inv.type
            customer_name = inv.customer_name or 'نقدي' if inv_type == 'sale' else ''
            supplier_name = inv.supplier_name or 'نقدي' if inv_type == 'purchase' else ''
            entity_text = f"<b>{'العميل' if inv_type == 'sale' else 'المورد'}:</b> {customer_name if inv_type == 'sale' else supplier_name}<br>" if (customer_name or supplier_name) else ""

            info_text = f"""
            <b>التاريخ:</b> {inv.date}<br>
            <b>الإجمالي:</b> {format_currency(inv.total)}<br>
            <b>المدفوع:</b> {format_currency(inv.paid)}<br>
            <b>المتبقي:</b> {format_currency(inv.total - inv.paid)}<br>
            {entity_text}
            <b>ملاحظات:</b> {inv.notes}
            """
            label = QLabel(info_text)
            label.setWordWrap(True)
            layout.addWidget(label)

            lines_list = QListWidget()
            lines = inv.lines
            if not lines:
                lines_list.addItem("لا توجد بنود")
            else:
                for line in lines:
                    item_name = line.item_name or 'مادة غير معروفة'
                    qty = line.quantity
                    unit = line.unit or ''
                    price = line.unit_price
                    total = line.total
                    unit_display = f" ({unit})" if unit else ""
                    lines_list.addItem(f"{item_name}{unit_display} - {qty} × {format_currency(price)} = {format_currency(total)}")
            layout.addWidget(lines_list)

            btn_layout = QHBoxLayout()
            close_btn = QPushButton("إغلاق")
            close_btn.clicked.connect(dialog.accept)
            btn_layout.addWidget(close_btn)
            layout.addLayout(btn_layout)

            dialog.exec()
        except Exception as e:
            error_details = traceback.format_exc()
            show_toast(f"خطأ في عرض التفاصيل: {str(e)}\n{error_details[:200]}", "error", self)
