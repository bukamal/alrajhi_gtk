# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QTableView,
                             QHeaderView, QMessageBox, QDialog, QFormLayout, QLabel, QComboBox, QDateEdit)
from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, QDate
from database import db
from utils_pyqt5 import format_currency, show_toast, format_date

class VouchersTableModel(QAbstractTableModel):
    def __init__(self, data, headers):
        super().__init__()
        self._data = data
        self._headers = headers

    def rowCount(self, parent=QModelIndex()): return len(self._data)
    def columnCount(self, parent=QModelIndex()): return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid(): return None
        if role == Qt.DisplayRole:
            return str(self._data[index.row()][index.column()])
        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter
        return None

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]
        return None

    def update_data(self, new_data):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()

class VouchersWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(6)
        self.layout.setContentsMargins(6,6,6,6)

        top = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("بحث عن سند...")
        self.search_edit.textChanged.connect(self.refresh)
        top.addWidget(self.search_edit)

        self.add_btn = QPushButton("➕ إضافة سند")
        self.add_btn.setObjectName("primary")
        self.add_btn.clicked.connect(self.add_voucher)
        top.addWidget(self.add_btn)

        self.delete_btn = QPushButton("🗑 حذف المحدد")
        self.delete_btn.setObjectName("danger")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self.delete_selected)
        top.addWidget(self.delete_btn)

        self.layout.addLayout(top)

        self.table = QTableView()
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(self.view_voucher)
        self.layout.addWidget(self.table)
        self.refresh()

    def refresh(self):
        search = self.search_edit.text().strip().lower()
        vouchers = db.get_vouchers()
        customers = {c['id']: c['name'] for c in db.get_customers()}
        suppliers = {s['id']: s['name'] for s in db.get_suppliers()}
        if search:
            vouchers = [v for v in vouchers if search in v.get('description','').lower() or search in v.get('reference','').lower() or
                        (v.get('customer_id') and customers.get(v['customer_id'], '').lower().find(search) != -1) or
                        (v.get('supplier_id') and suppliers.get(v['supplier_id'], '').lower().find(search) != -1)]
        data = []
        for v in vouchers:
            typ = "قبض" if v['type'] == 'receipt' else "دفع" if v['type'] == 'payment' else "مصروف"
            entity = customers.get(v['customer_id']) if v['customer_id'] else (suppliers.get(v['supplier_id']) if v['supplier_id'] else '')
            data.append([v['id'], typ, v['date'], v.get('reference',''), entity, format_currency(v['amount'])])
        headers = ["#", "النوع", "التاريخ", "المرجع", "الجهة", "المبلغ"]
        self.model = VouchersTableModel(data, headers)
        self.table.setModel(self.model)
        self.table.setColumnHidden(0, True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.delete_btn.setEnabled(False)
        self.table.selectionModel().selectionChanged.connect(self.on_selection_changed)

    def on_selection_changed(self, selected, deselected):
        self.delete_btn.setEnabled(len(self.table.selectionModel().selectedRows()) > 0)

    def add_voucher(self):
        self.open_voucher_dialog()

    def view_voucher(self, index):
        row = index.row()
        vid = self.model._data[row][0]
        self.open_voucher_dialog(is_edit=True, voucher_id=vid)

    def delete_selected(self):
        selection = self.table.selectionModel().selectedRows()
        if not selection:
            return
        row = selection[0].row()
        vid = self.model._data[row][0]
        reply = QMessageBox.question(self, "تأكيد الحذف", "هل تريد حذف هذا السند؟", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                db.delete_voucher(vid)
                show_toast("تم حذف السند", "success", self)
                self.refresh()
            except Exception as e:
                show_toast(str(e), "error", self)

    def open_voucher_dialog(self, is_edit=False, voucher_id=None):
        dialog = QDialog(self)
        dialog.setWindowTitle("تعديل سند" if is_edit else "إضافة سند جديد")
        dialog.setModal(True)
        dialog.setLayoutDirection(Qt.RightToLeft)
        dialog.resize(450, 400)
        layout = QFormLayout(dialog)
        layout.setSpacing(8)
        layout.setContentsMargins(12,12,12,12)

        type_combo = QComboBox()
        type_combo.addItems(["قبض", "دفع", "مصروف"])
        layout.addRow("النوع:", type_combo)

        cust_combo = QComboBox()
        cust_combo.addItem("اختر عميل", None)
        customers = db.get_customers()
        for c in customers:
            cust_combo.addItem(f"{c['name']} (الرصيد: {format_currency(c['balance'])})", c['id'])
        supp_combo = QComboBox()
        supp_combo.addItem("اختر مورد", None)
        suppliers = db.get_suppliers()
        for s in suppliers:
            supp_combo.addItem(f"{s['name']} (الرصيد: {format_currency(s['balance'])})", s['id'])

        layout.addRow("العميل:", cust_combo)
        layout.addRow("المورد:", supp_combo)

        invoice_combo = QComboBox()
        invoice_combo.addItem("بدون فاتورة", None)
        layout.addRow("الفاتورة:", invoice_combo)

        amount_edit = QLineEdit()
        amount_edit.setPlaceholderText("المبلغ")
        layout.addRow("المبلغ:", amount_edit)

        date_edit = QDateEdit()
        date_edit.setDate(QDate.currentDate())
        layout.addRow("التاريخ:", date_edit)

        desc_edit = QLineEdit()
        desc_edit.setPlaceholderText("الوصف")
        layout.addRow("الوصف:", desc_edit)

        ref_edit = QLineEdit()
        ref_edit.setPlaceholderText("المرجع (يُترك فارغاً للتوليد التلقائي)")
        layout.addRow("المرجع:", ref_edit)

        warning_label = QLabel()
        warning_label.setStyleSheet("color: #f97316; font-weight: bold;")
        warning_label.setVisible(False)
        layout.addRow(warning_label)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("حفظ")
        save_btn.setObjectName("primary")
        cancel_btn = QPushButton("إلغاء")
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

        def update_entity_visibility():
            typ = type_combo.currentText()
            if typ == "قبض":
                cust_combo.setVisible(True)
                supp_combo.setVisible(False)
                layout.labelForField(cust_combo).setVisible(True)
                layout.labelForField(supp_combo).setVisible(False)
            elif typ == "دفع":
                cust_combo.setVisible(False)
                supp_combo.setVisible(True)
                layout.labelForField(cust_combo).setVisible(False)
                layout.labelForField(supp_combo).setVisible(True)
            else:
                cust_combo.setVisible(False)
                supp_combo.setVisible(False)
                layout.labelForField(cust_combo).setVisible(False)
                layout.labelForField(supp_combo).setVisible(False)

        type_combo.currentTextChanged.connect(update_entity_visibility)
        update_entity_visibility()

        def update_invoice_list():
            typ = type_combo.currentText()
            entity_id = None
            if typ == "قبض":
                entity_id = cust_combo.currentData()
            elif typ == "دفع":
                entity_id = supp_combo.currentData()
            if not entity_id:
                invoice_combo.clear()
                invoice_combo.addItem("بدون فاتورة", None)
                return
            invoices = db.get_invoices()
            filtered = []
            for inv in invoices:
                if typ == "قبض" and inv['customer_id'] == entity_id and inv['type'] == 'sale' and inv['deleted_at'] is None:
                    filtered.append(inv)
                elif typ == "دفع" and inv['supplier_id'] == entity_id and inv['type'] == 'purchase' and inv['deleted_at'] is None:
                    filtered.append(inv)
            invoice_combo.clear()
            invoice_combo.addItem("بدون فاتورة", None)
            for inv in filtered:
                invoice_combo.addItem(f"{'بيع' if inv['type']=='sale' else 'شراء'} {inv.get('reference','')} - {format_currency(inv['total'])} (متبقي: {format_currency(inv['total']-inv['paid'])})", inv['id'])

        cust_combo.currentIndexChanged.connect(update_invoice_list)
        supp_combo.currentIndexChanged.connect(update_invoice_list)
        type_combo.currentTextChanged.connect(update_invoice_list)

        def check_balance():
            typ = type_combo.currentText()
            amount = 0.0
            try:
                amount = float(amount_edit.text())
            except:
                pass
            if amount <= 0:
                warning_label.setVisible(False)
                return
            balance = 0
            entity_name = ""
            if typ == "قبض":
                cust_id = cust_combo.currentData()
                if cust_id:
                    cust = next((c for c in customers if c['id'] == cust_id), None)
                    if cust:
                        balance = cust['balance']
                        entity_name = cust['name']
            elif typ == "دفع":
                supp_id = supp_combo.currentData()
                if supp_id:
                    supp = next((s for s in suppliers if s['id'] == supp_id), None)
                    if supp:
                        balance = supp['balance']
                        entity_name = supp['name']
            if amount > balance:
                warning_label.setText(f"⚠️ المبلغ يتجاوز رصيد {entity_name} الحالي ({format_currency(balance)}). سيتم تسجيل دفعة مقدمة.")
                warning_label.setVisible(True)
            else:
                warning_label.setVisible(False)

        amount_edit.textChanged.connect(check_balance)
        cust_combo.currentIndexChanged.connect(check_balance)
        supp_combo.currentIndexChanged.connect(check_balance)
        type_combo.currentTextChanged.connect(check_balance)

        if is_edit and voucher_id:
            vouchers = db.get_vouchers()
            v = next((v for v in vouchers if v['id'] == voucher_id), None)
            if v:
                type_combo.setCurrentText("قبض" if v['type'] == 'receipt' else "دفع" if v['type'] == 'payment' else "مصروف")
                if v['customer_id']:
                    idx = cust_combo.findData(v['customer_id'])
                    if idx >= 0: cust_combo.setCurrentIndex(idx)
                if v['supplier_id']:
                    idx = supp_combo.findData(v['supplier_id'])
                    if idx >= 0: supp_combo.setCurrentIndex(idx)
                amount_edit.setText(str(v['amount']))
                date_edit.setDate(QDate.fromString(v['date'], "yyyy-MM-dd"))
                desc_edit.setText(v.get('description',''))
                ref_edit.setText(v.get('reference',''))
                if v.get('invoice_id'):
                    update_invoice_list()
                    inv_idx = invoice_combo.findData(v['invoice_id'])
                    if inv_idx >= 0: invoice_combo.setCurrentIndex(inv_idx)

        def on_save():
            typ = type_combo.currentText()
            if typ == "قبض":
                cust_id = cust_combo.currentData()
                if not cust_id:
                    show_toast("يرجى اختيار عميل", "error", dialog)
                    return
                supp_id = None
            elif typ == "دفع":
                supp_id = supp_combo.currentData()
                if not supp_id:
                    show_toast("يرجى اختيار مورد", "error", dialog)
                    return
                cust_id = None
            else:
                cust_id = supp_id = None
            try:
                amount = float(amount_edit.text())
                if amount <= 0:
                    show_toast("المبلغ يجب أن يكون أكبر من صفر", "error", dialog)
                    return
            except:
                show_toast("المبلغ غير صحيح", "error", dialog)
                return
            date_str = date_edit.date().toString("yyyy-MM-dd")
            description = desc_edit.text().strip()
            reference = ref_edit.text().strip()
            invoice_id = invoice_combo.currentData() or None
            voucher_type = 'receipt' if typ == "قبض" else 'payment' if typ == "دفع" else 'expense'
            data = {
                'type': voucher_type,
                'amount': amount,
                'date': date_str,
                'description': description,
                'reference': reference if reference else None,
                'customer_id': cust_id,
                'supplier_id': supp_id,
                'invoice_id': invoice_id
            }
            try:
                if is_edit and voucher_id:
                    db.delete_voucher(voucher_id)
                    db.add_voucher(data)
                    show_toast("تم التعديل بنجاح", "success", dialog)
                else:
                    db.add_voucher(data)
                    show_toast("تمت الإضافة بنجاح", "success", dialog)
                dialog.accept()
                self.refresh()
            except Exception as e:
                show_toast(str(e), "error", dialog)

        save_btn.clicked.connect(on_save)
        cancel_btn.clicked.connect(dialog.reject)
        dialog.exec()
