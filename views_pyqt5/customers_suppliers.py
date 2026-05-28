# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QTableView,
                             QHeaderView, QMessageBox, QDialog, QFormLayout, QLabel, QApplication,
                             QComboBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from database import db
from utils_pyqt5 import format_currency, show_toast
from views_pyqt5.base_table_model import BaseTableModel
from views_pyqt5.centered_dialog import CenteredDialog
from views_pyqt5.modern_table import ModernTableView
from views_pyqt5.invoice_dialog import InvoiceDialog

class CustomersSuppliersWidget(QWidget):
    def __init__(self, parent=None, entity_type='customer'):
        super().__init__(parent)
        self.entity_type = entity_type
        self.current_entity_id = None
        self.current_entity_name = None
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(6)
        self.layout.setContentsMargins(6,6,6,6)

        # شريط الأزرار العلوي
        top = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("بحث...")
        self.search_edit.textChanged.connect(self.refresh)
        top.addWidget(self.search_edit)

        # فلتر الرصيد
        self.balance_filter = QComboBox()
        self.balance_filter.addItem("جميع الأرصدة", None)
        self.balance_filter.addItem("رصيد موجب (>0)", "positive")
        self.balance_filter.addItem("رصيد سالب (<0)", "negative")
        self.balance_filter.addItem("رصيد صفر", "zero")
        self.balance_filter.currentIndexChanged.connect(self.refresh)
        top.addWidget(QLabel("فلتر:"))
        top.addWidget(self.balance_filter)

        # فلتر الهاتف
        self.phone_filter = QComboBox()
        self.phone_filter.addItem("الكل", None)
        self.phone_filter.addItem("لديه هاتف", "has_phone")
        self.phone_filter.addItem("لا يوجد هاتف", "no_phone")
        self.phone_filter.currentIndexChanged.connect(self.refresh)
        top.addWidget(self.phone_filter)

        self.add_btn = QPushButton("➕ إضافة")
        self.add_btn.setObjectName("primary")
        self.add_btn.clicked.connect(self.add_entity)
        top.addWidget(self.add_btn)

        self.delete_btn = QPushButton("🗑 حذف المحدد")
        self.delete_btn.setObjectName("danger")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self.delete_selected)
        top.addWidget(self.delete_btn)

        # أزرار الإجراءات السريعة
        self.statement_btn = QPushButton("📄 كشف حساب")
        self.statement_btn.setEnabled(False)
        self.statement_btn.clicked.connect(self.show_statement)
        top.addWidget(self.statement_btn)

        self.quick_invoice_btn = QPushButton("🧾 معاملة سريعة")
        self.quick_invoice_btn.setEnabled(False)
        self.quick_invoice_btn.clicked.connect(self.quick_transaction)
        top.addWidget(self.quick_invoice_btn)

        self.refresh_btn = QPushButton("🔄 تحديث")
        self.refresh_btn.clicked.connect(self.refresh)
        top.addWidget(self.refresh_btn)

        self.export_excel_btn = QPushButton("📊 Excel")
        self.export_excel_btn.clicked.connect(self.export_to_excel)
        top.addWidget(self.export_excel_btn)

        self.print_btn = QPushButton("🖨️ طباعة")
        self.print_btn.clicked.connect(self.print_list)
        top.addWidget(self.print_btn)

        self.layout.addLayout(top)

        # الجدول
        self.table = ModernTableView()
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(self.edit_entity)
        # لا نربط selectionChanged هنا لأنه سيكون None بعد
        self.layout.addWidget(self.table)

        # شريط الحالة
        self.status_label = QLabel()
        self.layout.addWidget(self.status_label)

        self.refresh()

    def refresh(self):
        search = self.search_edit.text().strip().lower() if self.search_edit.text() else None
        if self.entity_type == 'customer':
            entities = db.get_customers(search=search)
        else:
            entities = db.get_suppliers(search=search)
        
        # تطبيق الفلاتر الإضافية
        balance_filter = self.balance_filter.currentData()
        phone_filter = self.phone_filter.currentData()
        filtered = []
        for e in entities:
            balance = e['balance']
            if balance_filter == 'positive' and balance <= 0:
                continue
            if balance_filter == 'negative' and balance >= 0:
                continue
            if balance_filter == 'zero' and balance != 0:
                continue
            phone = e.get('phone', '')
            if phone_filter == 'has_phone' and not phone:
                continue
            if phone_filter == 'no_phone' and phone:
                continue
            filtered.append(e)
        
        data = []
        for e in filtered:
            data.append([e['id'], e['name'], e.get('phone',''), e.get('address',''), e['balance']])
        
        headers = ["#", "الاسم", "الهاتف", "العنوان", "الرصيد"]
        self.model = BaseTableModel(data, headers)
        
        def custom_data(index, role):
            if role == Qt.ForegroundRole and index.column() == 4:
                balance = self.model._data[index.row()][4]
                if balance < 0:
                    return QColor(239, 68, 68)
                elif balance > 0:
                    return QColor(34, 197, 94)
                else:
                    return QColor(100, 116, 139)
            return None
        self.model.custom_data = custom_data
        
        self.table.setModel(self.model)
        self.table.setColumnHidden(0, True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.resizeRowsToContents()

        # ربط إشارة تحديد الصف بعد تعيين النموذج
        if self.table.selectionModel():
            try:
                self.table.selectionModel().selectionChanged.disconnect()
            except:
                pass
            self.table.selectionModel().selectionChanged.connect(self.on_selection_changed)

        # تعطيل الأزرار حتى يتم تحديد صف
        self.statement_btn.setEnabled(False)
        self.quick_invoice_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.current_entity_id = None
        self.current_entity_name = None
        self.status_label.setText(f"إجمالي السجلات: {len(filtered)}")

    def on_selection_changed(self, selected, deselected):
        rows = self.table.selectionModel().selectedRows()
        if rows:
            row = rows[0].row()
            self.current_entity_id = self.model._data[row][0]
            self.current_entity_name = self.model._data[row][1]
            self.statement_btn.setEnabled(True)
            self.quick_invoice_btn.setEnabled(True)
            self.delete_btn.setEnabled(True)
        else:
            self.current_entity_id = None
            self.current_entity_name = None
            self.statement_btn.setEnabled(False)
            self.quick_invoice_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)

    def add_entity(self):
        self.open_entity_dialog()

    def edit_entity(self, index):
        row = index.row()
        eid = self.model._data[row][0]
        self.open_entity_dialog(is_edit=True, eid=eid)

    def delete_selected(self):
        if not self.current_entity_id:
            return
        reply = QMessageBox.question(self, "تأكيد الحذف", f"هل تريد حذف هذا {self.entity_type}؟", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                if self.entity_type == 'customer':
                    db.delete_customer(self.current_entity_id)
                else:
                    db.delete_supplier(self.current_entity_id)
                show_toast("تم الحذف", "success", self)
                self.refresh()
            except Exception as e:
                show_toast(str(e), "error", self)

    def show_statement(self):
        if not self.current_entity_id:
            return
        dialog = CenteredDialog(self)
        dialog.setWindowTitle(f"كشف حساب {self.entity_type} - {self.current_entity_name}")
        dialog.resize(700, 500)
        layout = QVBoxLayout(dialog)
        
        from utils_pyqt5 import format_currency
        if self.entity_type == 'customer':
            lines = db.get_customer_statement(self.current_entity_id)
        else:
            lines = db.get_supplier_statement(self.current_entity_id)
        
        if not lines:
            label = QLabel("لا توجد حركات لهذا الحساب")
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)
        else:
            html = f"""
            <div style="text-align: center;">
                <h3>كشف حساب {self.entity_type}</h3>
                <h4>{self.current_entity_name}</h4>
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
        if not self.current_entity_id:
            return
        menu = QMessageBox(self)
        menu.setWindowTitle("اختر نوع المعاملة")
        menu.setText(f"اختر نوع المعاملة لـ {self.current_entity_name}")
        if self.entity_type == 'customer':
            sale_btn = menu.addButton("فاتورة بيع", QMessageBox.YesRole)
            receipt_btn = menu.addButton("سند قبض", QMessageBox.ActionRole)
            cancel_btn = menu.addButton("إلغاء", QMessageBox.RejectRole)
            menu.exec()
            if menu.clickedButton() == sale_btn:
                dialog = InvoiceDialog('sale', self)
                from PyQt5.QtCore import QTimer
                def set_customer():
                    idx = dialog.entity_combo.findData(self.current_entity_id)
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
        else:  # مورد
            purchase_btn = menu.addButton("فاتورة شراء", QMessageBox.YesRole)
            payment_btn = menu.addButton("سند دفع", QMessageBox.ActionRole)
            cancel_btn = menu.addButton("إلغاء", QMessageBox.RejectRole)
            menu.exec()
            if menu.clickedButton() == purchase_btn:
                dialog = InvoiceDialog('purchase', self)
                from PyQt5.QtCore import QTimer
                def set_supplier():
                    idx = dialog.entity_combo.findData(self.current_entity_id)
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

    def open_entity_dialog(self, is_edit=False, eid=None):
        dialog = CenteredDialog(self)
        dialog.setWindowTitle(f"تعديل {self.entity_type}" if is_edit else f"إضافة {self.entity_type}")
        dialog.setLayoutDirection(Qt.RightToLeft)
        dialog.resize(380, 240)
        layout = QFormLayout(dialog)
        name_edit = QLineEdit()
        phone_edit = QLineEdit()
        addr_edit = QLineEdit()
        layout.addRow("الاسم:", name_edit)
        layout.addRow("الهاتف:", phone_edit)
        layout.addRow("العنوان:", addr_edit)
        if is_edit and eid:
            entities = db.get_customers() if self.entity_type=='customer' else db.get_suppliers()
            ent = next((e for e in entities if e['id']==eid), None)
            if ent:
                name_edit.setText(ent['name'])
                phone_edit.setText(ent.get('phone',''))
                addr_edit.setText(ent.get('address',''))
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
                show_toast("الاسم مطلوب", "error", dialog)
                return
            phone = phone_edit.text().strip()
            addr = addr_edit.text().strip()
            try:
                if is_edit:
                    if self.entity_type=='customer':
                        db.update_customer(eid, name, phone, addr)
                    else:
                        db.update_supplier(eid, name, phone, addr)
                    show_toast("تم التحديث", "success", dialog)
                else:
                    if self.entity_type=='customer':
                        db.add_customer(name, phone, addr)
                    else:
                        db.add_supplier(name, phone, addr)
                    show_toast("تمت الإضافة", "success", dialog)
                dialog.accept()
                self.refresh()
            except Exception as e:
                show_toast(str(e), "error", dialog)
        save_btn.clicked.connect(on_save)
        cancel_btn.clicked.connect(dialog.reject)
        dialog.exec()

    def export_to_excel(self):
        if hasattr(self.table, 'export_to_excel'):
            self.table.export_to_excel()
        else:
            show_toast("هذه الميزة غير متوفرة حالياً", "error", self)

    def print_list(self):
        if hasattr(self.table, 'print_table'):
            self.table.print_table()
        else:
            show_toast("هذه الميزة غير متوفرة حالياً", "error", self)
