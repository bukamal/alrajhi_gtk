# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QTableView,
                             QHeaderView, QMessageBox, QDialog, QLabel, QListWidget)
from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex
from database import db
from utils_pyqt5 import format_currency, show_toast
from views_pyqt5.invoice_dialog import InvoiceDialog
import traceback

class InvoicesTableModel(QAbstractTableModel):
    def __init__(self, data, headers):
        super().__init__()
        self._data = data if data is not None else []
        self._headers = headers if headers is not None else []

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            try:
                row = index.row()
                col = index.column()
                if 0 <= row < len(self._data) and 0 <= col < len(self._data[row]):
                    value = self._data[row][col]
                    return str(value) if value is not None else ""
            except Exception:
                return ""
        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter
        return None

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            try:
                if 0 <= section < len(self._headers):
                    return self._headers[section]
            except Exception:
                return ""
        return None

    def update_data(self, new_data):
        self.beginResetModel()
        self._data = new_data if new_data is not None else []
        self.endResetModel()

class InvoicesWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.refresh()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(6,6,6,6)

        btn_layout = QHBoxLayout()
        self.sale_btn = QPushButton("💰 فاتورة بيع جديدة")
        self.sale_btn.setObjectName("primary")
        self.sale_btn.clicked.connect(lambda: self.create_invoice('sale'))
        self.purchase_btn = QPushButton("📦 فاتورة شراء جديدة")
        self.purchase_btn.setObjectName("success")
        self.purchase_btn.clicked.connect(lambda: self.create_invoice('purchase'))

        self.delete_btn = QPushButton("🗑 حذف الفاتورة المحددة")
        self.delete_btn.setObjectName("danger")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self.delete_selected_invoice)

        btn_layout.addWidget(self.sale_btn)
        btn_layout.addWidget(self.purchase_btn)
        btn_layout.addWidget(self.delete_btn)
        layout.addLayout(btn_layout)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("بحث عن فاتورة...")
        self.search_edit.textChanged.connect(self.refresh)
        layout.addWidget(self.search_edit)

        self.table = QTableView()
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(self.view_invoice)
        layout.addWidget(self.table)

    def refresh(self):
        try:
            search = self.search_edit.text().strip().lower()
            invoices = db.get_invoices()
            if not invoices:
                invoices = []
            if search:
                invoices = [i for i in invoices if search in (i.get('reference','')+i.get('customer_name','')+i.get('supplier_name','')).lower()]
            data = []
            for inv in invoices:
                typ = "بيع" if inv.get('type') == 'sale' else "شراء"
                data.append([
                    inv.get('id', ''),
                    typ,
                    inv.get('reference', ''),
                    inv.get('date', ''),
                    format_currency(inv.get('total', 0)),
                    format_currency(inv.get('total', 0) - inv.get('paid', 0))
                ])
            headers = ["#", "النوع", "المرجع", "التاريخ", "الإجمالي", "المتبقي"]
            self.model = InvoicesTableModel(data, headers)
            self.table.setModel(self.model)
            self.table.setColumnHidden(0, True)
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.delete_btn.setEnabled(False)
            self.table.selectionModel().selectionChanged.connect(self.on_selection_changed)
        except Exception as e:
            show_toast(f"خطأ في تحديث الفواتير: {str(e)}", "error", self)

    def on_selection_changed(self, selected, deselected):
        self.delete_btn.setEnabled(len(self.table.selectionModel().selectedRows()) > 0)

    def create_invoice(self, inv_type):
        try:
            dialog = InvoiceDialog(inv_type, self)
            if dialog.exec() == QDialog.Accepted:
                self.refresh()
        except Exception as e:
            show_toast(f"خطأ في إنشاء الفاتورة: {str(e)}", "error", self)

    def delete_selected_invoice(self):
        selection = self.table.selectionModel().selectedRows()
        if not selection:
            return
        row = selection[0].row()
        inv_id = self.model._data[row][0]
        reply = QMessageBox.question(self, "تأكيد الحذف", "هل تريد حذف هذه الفاتورة؟", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                db.delete_invoice(inv_id)
                show_toast("تم حذف الفاتورة", "success", self)
                self.refresh()
            except Exception as e:
                show_toast(str(e), "error", self)

    def view_invoice(self, index):
        try:
            row = index.row()
            if row < 0 or not hasattr(self, 'model') or row >= len(self.model._data):
                return
            inv_id = self.model._data[row][0]
            invoices = db.get_invoices()
            inv = next((i for i in invoices if i.get('id') == inv_id), None)
            if not inv:
                show_toast("الفاتورة غير موجودة", "error", self)
                return
            self.show_invoice_detail(inv)
        except Exception as e:
            show_toast(f"خطأ في عرض الفاتورة: {str(e)}", "error", self)

    def show_invoice_detail(self, inv):
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle(f"فاتورة {inv.get('reference', '')}")
            dialog.setModal(True)
            dialog.setLayoutDirection(Qt.RightToLeft)
            dialog.resize(600, 500)
            layout = QVBoxLayout(dialog)

            inv_type = inv.get('type', '')
            customer_name = inv.get('customer_name', 'نقدي') if inv_type == 'sale' else ''
            supplier_name = inv.get('supplier_name', 'نقدي') if inv_type == 'purchase' else ''
            entity_text = f"<b>{'العميل' if inv_type == 'sale' else 'المورد'}:</b> {customer_name if inv_type == 'sale' else supplier_name}<br>" if (customer_name or supplier_name) else ""

            info_text = f"""
            <b>التاريخ:</b> {inv.get('date', '')}<br>
            <b>الإجمالي:</b> {format_currency(inv.get('total', 0))}<br>
            <b>المدفوع:</b> {format_currency(inv.get('paid', 0))}<br>
            <b>المتبقي:</b> {format_currency(inv.get('total', 0) - inv.get('paid', 0))}<br>
            {entity_text}
            <b>ملاحظات:</b> {inv.get('notes', '')}
            """
            label = QLabel(info_text)
            label.setWordWrap(True)
            layout.addWidget(label)

            lines_list = QListWidget()
            lines = inv.get('lines', [])
            if not lines:
                lines_list.addItem("لا توجد بنود")
            else:
                for line in lines:
                    item_name = line.get('item_name', 'مادة غير معروفة')
                    qty = line.get('quantity', 0)
                    unit = line.get('unit', '')
                    price = line.get('unit_price', 0)
                    total = line.get('total', 0)
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
