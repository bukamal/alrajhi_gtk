# views_pyqt5/customers_suppliers.py
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from database import customer_dao, supplier_dao, invoice_dao, reporting_dao
from utils_pyqt5 import format_currency, show_toast
from views_pyqt5.base_table_model import BaseTableModel
from views_pyqt5.centered_dialog import CenteredDialog
from views_pyqt5.modern_table import ModernTableView
from views_pyqt5.invoice_dialog import InvoiceDialog
from views_pyqt5.base_widget import BaseWidget


class CustomersSuppliersWidget(BaseWidget):
    entity_name = "عميل"
    search_placeholder = "بحث..."
    headers = ["#", "الاسم", "الهاتف", "العنوان", "الرصيد"]
    has_export = True
    has_print = True
    has_pagination = True
    page_size = 50
    extra_buttons = [
        ("📄 كشف حساب", "show_statement", "btn_statement"),
        ("🧾 معاملة سريعة", "quick_transaction", "btn_quick"),
    ]

    def __init__(self, parent=None, entity_type='customer'):
        self.entity_type = entity_type
        self.entity_name = "عميل" if entity_type == 'customer' else "مورد"
        self.balance_filter = QComboBox()
        self.phone_filter = QComboBox()
        self.current_entity_id = None
        self.current_entity_name = None
        super().__init__(parent)
        self.init_filters()

    def init_filters(self):
        filter_layout = QHBoxLayout()
        self.balance_filter.addItem("جميع الأرصدة", None)
        self.balance_filter.addItem("رصيد موجب (>0)", "positive")
        self.balance_filter.addItem("رصيد سالب (<0)", "negative")
        self.balance_filter.addItem("رصيد صفر", "zero")
        self.balance_filter.currentIndexChanged.connect(self.refresh)
        filter_layout.addWidget(QLabel("فلتر:"))
        filter_layout.addWidget(self.balance_filter)

        self.phone_filter.addItem("الكل", None)
        self.phone_filter.addItem("لديه هاتف", "has_phone")
        self.phone_filter.addItem("لا يوجد هاتف", "no_phone")
        self.phone_filter.currentIndexChanged.connect(self.refresh)
        filter_layout.addWidget(self.phone_filter)
        filter_layout.addStretch()
        self.layout.insertLayout(2, filter_layout)

    def get_total_count(self, search=None):
        if self.entity_type == 'customer':
            return customer_dao.get_count(search)
        else:
            return supplier_dao.get_count(search)

    def fetch_data(self, search=None, limit=None, offset=None):
        if self.entity_type == 'customer':
            entities = customer_dao.get_all(search=search, limit=limit, offset=offset)
        else:
            entities = supplier_dao.get_all(search=search, limit=limit, offset=offset)
        if entities is None:
            return []
        balance_filter = self.balance_filter.currentData()
        phone_filter = self.phone_filter.currentData()
        filtered = []
        for e in entities:
            balance = e.balance
            if balance_filter == 'positive' and balance <= 0:
                continue
            if balance_filter == 'negative' and balance >= 0:
                continue
            if balance_filter == 'zero' and balance != 0:
                continue
            phone = e.phone or ''
            if phone_filter == 'has_phone' and not phone:
                continue
            if phone_filter == 'no_phone' and phone:
                continue
            filtered.append(e)
        return filtered

    def prepare_table_data(self, items):
        data = []
        for e in items:
            data.append([
                e.id,
                e.name,
                e.phone or '',
                e.address or '',
                e.balance
            ])
        return data

    def custom_data(self, index, role):
        if role == Qt.ForegroundRole and index.column() == 4:
            balance = self.model._data[index.row()][4]
            if balance < 0:
                return QColor(239, 68, 68)
            elif balance > 0:
                return QColor(34, 197, 94)
        return None

    def on_selection_changed(self, selected, deselected):
        super().on_selection_changed(selected, deselected)
        self.current_entity_id = self.current_id
        self.current_entity_name = self.current_name

    def delete_item(self, item_id):
        if self.entity_type == 'customer':
            customer_dao.delete(item_id)
        else:
            supplier_dao.delete(item_id)

    def show_statement(self):
        if not self.current_id:
            show_toast("لم يتم تحديد عنصر", "error", self)
            return
        dialog = CenteredDialog(self)
        dialog.setWindowTitle(f"كشف حساب {self.entity_name} - {self.current_name}")
        dialog.resize(700, 500)
        layout = QVBoxLayout(dialog)

        if self.entity_type == 'customer':
            lines = reporting_dao.get_customer_statement(self.current_id)
        else:
            lines = reporting_dao.get_supplier_statement(self.current_id)

        if not lines:
            label = QLabel("لا توجد حركات لهذا الحساب")
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)
        else:
            html = f"""
            <div style="text-align: center;">
                <h3>كشف حساب {self.entity_name}</h3>
                <h4>{self.current_name}</h4>
                <hr>
            </div>
            <table style="width:100%; border-collapse:collapse;">
                <thead>
                    <tr style="background-color:#34495e; color:white;">
                        <th style="padding:8px;">التاريخ</th>
                        <th style="padding:8px;">الوصف</th>
                        <th style="padding:8px;">مدين</th>
                        <th style="padding:8px;">دائن</th>
                        <th style="padding:8px;">الرصيد</th>
                    </tr>
                </thead>
                <tbody>
            """
            for l in lines:
                html += f"""
                    <tr style="border-bottom:1px solid #ddd;">
                        <td style="padding:8px;">{l['date']}浏
                        <td style="padding:8px;">{l['description']}浏
                        <td style="text-align:center;">{format_currency(l['debit'])}浏
                        <td style="text-align:center;">{format_currency(l['credit'])}浏
                        <td style="text-align:center;">{format_currency(l['balance'])}浏
                    </tr>
                """
            html += "</tbody></table>"
            text_edit = QLabel(html)
            text_edit.setWordWrap(True)
            text_edit.setTextFormat(Qt.RichText)
            layout.addWidget(text_edit)

        close_btn = QPushButton("إغلاق")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        dialog.exec()

    def quick_transaction(self):
        if not self.current_id:
            show_toast("لم يتم تحديد عنصر", "error", self)
            return
        menu = QMessageBox(self)
        menu.setWindowTitle("اختر نوع المعاملة")
        menu.setText(f"اختر نوع المعاملة لـ {self.current_name}")
        if self.entity_type == 'customer':
            sale_btn = menu.addButton("فاتورة بيع", QMessageBox.YesRole)
            receipt_btn = menu.addButton("سند قبض", QMessageBox.ActionRole)
            cancel_btn = menu.addButton("إلغاء", QMessageBox.RejectRole)
            menu.exec()
            if menu.clickedButton() == sale_btn:
                dialog = InvoiceDialog('sale', self)
                from PyQt5.QtCore import QTimer
                def set_customer():
                    idx = dialog.entity_combo.findData(self.current_id)
                    if idx >= 0:
                        dialog.entity_combo.setCurrentIndex(idx)
                QTimer.singleShot(100, set_customer)
                dialog.exec()
                self.refresh()
            elif menu.clickedButton() == receipt_btn:
                show_toast("سيتم فتح نافذة إضافة سند، يرجى اختيار العميل يدوياً", "info", self)
                from views_pyqt5.vouchers import VouchersWidget
                voucher_widget = VouchersWidget()
                voucher_widget.add_voucher()
        else:
            purchase_btn = menu.addButton("فاتورة شراء", QMessageBox.YesRole)
            payment_btn = menu.addButton("سند دفع", QMessageBox.ActionRole)
            cancel_btn = menu.addButton("إلغاء", QMessageBox.RejectRole)
            menu.exec()
            if menu.clickedButton() == purchase_btn:
                dialog = InvoiceDialog('purchase', self)
                from PyQt5.QtCore import QTimer
                def set_supplier():
                    idx = dialog.entity_combo.findData(self.current_id)
                    if idx >= 0:
                        dialog.entity_combo.setCurrentIndex(idx)
                QTimer.singleShot(100, set_supplier)
                dialog.exec()
                self.refresh()
            elif menu.clickedButton() == payment_btn:
                show_toast("سيتم فتح نافذة إضافة سند دفع، يرجى اختيار المورد يدوياً", "info", self)
                from views_pyqt5.vouchers import VouchersWidget
                voucher_widget = VouchersWidget()
                voucher_widget.add_voucher()

    def open_dialog(self, is_edit=False, item_id=None, dialog_parent=None):
        parent_for_dialog = dialog_parent if dialog_parent else self
        dialog = CenteredDialog(parent_for_dialog)
        dialog.setWindowTitle(f"تعديل {self.entity_name}" if is_edit else f"إضافة {self.entity_name}")
        dialog.setLayoutDirection(Qt.RightToLeft)
        dialog.resize(380, 240)
        layout = QFormLayout(dialog)
        name_edit = QLineEdit()
        phone_edit = QLineEdit()
        addr_edit = QLineEdit()
        layout.addRow("الاسم:", name_edit)
        layout.addRow("الهاتف:", phone_edit)
        layout.addRow("العنوان:", addr_edit)

        if is_edit and item_id:
            if self.entity_type == 'customer':
                entity = customer_dao.get_by_id(item_id)
            else:
                entity = supplier_dao.get_by_id(item_id)
            if entity:
                name_edit.setText(entity.name)
                phone_edit.setText(entity.phone or '')
                addr_edit.setText(entity.address or '')

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("حفظ")
        save_btn.setObjectName("primary")
        cancel_btn = QPushButton("إلغاء")
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

        def on_save():
            name = name_edit.text().strip()
            if not name:
                show_centered_messagebox(dialog, "خطأ", "الاسم مطلوب", QMessageBox.Warning)
                return
            phone = phone_edit.text().strip()
            addr = addr_edit.text().strip()
            try:
                if is_edit:
                    if self.entity_type == 'customer':
                        customer_dao.update(item_id, name, phone, addr)
                    else:
                        supplier_dao.update(item_id, name, phone, addr)
                    show_toast("تم التحديث", "success", dialog)
                else:
                    if self.entity_type == 'customer':
                        customer_dao.add(name, phone, addr)
                    else:
                        supplier_dao.add(name, phone, addr)
                    show_toast("تمت الإضافة", "success", dialog)
                dialog.accept()
                self.refresh()
            except Exception as e:
                show_centered_messagebox(dialog, "خطأ", str(e), QMessageBox.Critical)

        save_btn.clicked.connect(on_save)
        cancel_btn.clicked.connect(dialog.reject)
        dialog.exec()
