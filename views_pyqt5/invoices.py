# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QTableView,
                             QHeaderView, QMessageBox, QDialog, QLabel, QListWidget, QComboBox, QDateEdit)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor, QBrush
from database import db
from utils_pyqt5 import format_currency, show_toast
from views_pyqt5.invoice_dialog import InvoiceDialog
from views_pyqt5.base_table_model import BaseTableModel
from views_pyqt5.modern_table import ModernTableView
import traceback

class InvoicesWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.refresh()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(6,6,6,6)

        # شريط الأزرار العلوي
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

        self.refresh_btn = QPushButton("🔄 تحديث")
        self.refresh_btn.setObjectName("secondary")
        self.refresh_btn.clicked.connect(self.refresh)

        # أزرار التصدير
        self.export_excel_btn = QPushButton("📊 تصدير Excel")
        self.export_excel_btn.clicked.connect(self.export_to_excel)
        self.export_pdf_btn = QPushButton("📄 طباعة القائمة")
        self.export_pdf_btn.clicked.connect(self.print_list)

        btn_layout.addWidget(self.sale_btn)
        btn_layout.addWidget(self.purchase_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(self.export_excel_btn)
        btn_layout.addWidget(self.export_pdf_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # شريط الفلاتر
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("النوع:"))
        self.type_combo = QComboBox()
        self.type_combo.addItem("الكل", "")
        self.type_combo.addItem("بيع", "sale")
        self.type_combo.addItem("شراء", "purchase")
        self.type_combo.currentIndexChanged.connect(self.refresh)

        filter_layout.addWidget(QLabel("من تاريخ:"))
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.start_date.setCalendarPopup(True)
        self.start_date.dateChanged.connect(self.refresh)

        filter_layout.addWidget(QLabel("إلى تاريخ:"))
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        self.end_date.dateChanged.connect(self.refresh)

        filter_layout.addWidget(QLabel("عميل/مورد:"))
        self.customer_supplier_combo = QComboBox()
        self.customer_supplier_combo.addItem("الكل", None)
        filter_layout.addWidget(self.customer_supplier_combo)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # شريط البحث
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("بحث عن فاتورة...")
        self.search_edit.textChanged.connect(self.refresh)
        layout.addWidget(self.search_edit)

        # الجدول (استخدام ModernTableView لدعم التصدير)
        self.table = ModernTableView()
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(self.view_invoice)
        layout.addWidget(self.table)

    def refresh(self):
        try:
            search = self.search_edit.text().strip().lower()
            inv_type = self.type_combo.currentData()
            start_date = self.start_date.date().toString("yyyy-MM-dd")
            end_date = self.end_date.date().toString("yyyy-MM-dd")
            entity_id = self.customer_supplier_combo.currentData()

            # تعبئة قائمة العملاء/الموردين
            if self.customer_supplier_combo.count() == 1:
                customers = db.get_customers()
                suppliers = db.get_suppliers()
                for c in customers:
                    self.customer_supplier_combo.addItem(f"عميل: {c['name']}", ('customer', c['id']))
                for s in suppliers:
                    self.customer_supplier_combo.addItem(f"مورد: {s['name']}", ('supplier', s['id']))

            # استخدام دالة الفلترة المحسنة إذا كانت موجودة
            if hasattr(db, 'get_invoices_filtered'):
                invoices = db.get_invoices_filtered(
                    search=search if search else None,
                    inv_type=inv_type if inv_type else None,
                    start_date=start_date,
                    end_date=end_date,
                    customer_id=entity_id[1] if entity_id and entity_id[0]=='customer' else None,
                    supplier_id=entity_id[1] if entity_id and entity_id[0]=='supplier' else None
                )
            else:
                # الرجوع إلى الطريقة القديمة
                invoices = db.get_invoices()
                if search:
                    invoices = [i for i in invoices if search in (i.get('reference','')+i.get('customer_name','')+i.get('supplier_name','')).lower()]
                if inv_type:
                    invoices = [i for i in invoices if i.get('type') == inv_type]
                invoices = [i for i in invoices if start_date <= i.get('date', '') <= end_date]
                if entity_id:
                    if entity_id[0] == 'customer':
                        invoices = [i for i in invoices if i.get('customer_id') == entity_id[1]]
                    else:
                        invoices = [i for i in invoices if i.get('supplier_id') == entity_id[1]]

            data = []
            self.row_colors = []
            for inv in invoices:
                typ = "بيع" if inv.get('type') == 'sale' else "شراء"
                total = inv.get('total', 0)
                paid = inv.get('paid', 0)
                remaining = total - paid
                data.append([
                    inv.get('id', ''),
                    typ,
                    inv.get('reference', ''),
                    inv.get('date', ''),
                    format_currency(total),
                    format_currency(remaining)
                ])
                self.row_colors.append(remaining > 0)
            headers = ["#", "النوع", "المرجع", "التاريخ", "الإجمالي", "المتبقي"]
            self.model = BaseTableModel(data, headers)
            self.table.setModel(self.model)
            self.table.setColumnHidden(0, True)
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.delete_btn.setEnabled(False)
            self.table.selectionModel().selectionChanged.connect(self.on_selection_changed)

            # تلوين الصفوف غير المسددة
            for row in range(self.model.rowCount()):
                if self.row_colors[row]:
                    self.model.set_row_background(row, QColor(255, 240, 240))
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
