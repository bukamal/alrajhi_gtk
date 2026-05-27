# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QLabel
from PyQt5.QtCore import Qt, QTimer
from database import db
from utils_pyqt5 import format_currency

class GlobalSearchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("بحث شامل (Ctrl+K)")
        self.setModal(True)
        self.setFixedSize(500, 400)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8,8,8,8)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("ابحث عن مادة، عميل، فاتورة، مستخدم...")
        self.search_edit.setStyleSheet("padding: 8px; font-size: 14px; border-radius: 8px;")
        self.search_edit.textChanged.connect(self.perform_search)
        layout.addWidget(self.search_edit)
        self.results_list = QListWidget()
        self.results_list.setStyleSheet("border: none;")
        self.results_list.itemClicked.connect(self.on_item_clicked)
        layout.addWidget(self.results_list)
        self.search_edit.setFocus()

    def perform_search(self):
        text = self.search_edit.text().strip().lower()
        self.results_list.clear()
        if len(text) < 2:
            return
        # بحث في المواد
        items = db.get_items()
        for item in items:
            if text in item['name'].lower():
                self.add_result("مادة", item['name'], 'items', item['id'])
        # بحث في العملاء
        customers = db.get_customers()
        for c in customers:
            if text in c['name'].lower() or text in c.get('phone','').lower():
                self.add_result("عميل", c['name'], 'customers', c['id'])
        # بحث في الموردين
        suppliers = db.get_suppliers()
        for s in suppliers:
            if text in s['name'].lower() or text in s.get('phone','').lower():
                self.add_result("مورد", s['name'], 'suppliers', s['id'])
        # بحث في الفواتير
        invoices = db.get_invoices()
        for inv in invoices:
            if text in inv.get('reference','').lower() or text in inv.get('customer_name','').lower() or text in inv.get('supplier_name','').lower():
                self.add_result("فاتورة", f"{inv['reference']} - {format_currency(inv['total'])}", 'invoices', inv['id'])

    def add_result(self, category, title, page, id_val):
        item = QListWidgetItem(f"{category}: {title}")
        item.setData(Qt.UserRole, (page, id_val))
        self.results_list.addItem(item)

    def on_item_clicked(self, item):
        page, id_val = item.data(Qt.UserRole)
        if self.parent:
            self.parent.switch_page(page)
            if page == 'items' and hasattr(self.parent.pages['items'], 'edit_item_by_id'):
                self.parent.pages['items'].edit_item_by_id(id_val)
            elif page == 'customers' and hasattr(self.parent.pages['customers'], 'edit_entity_by_id'):
                self.parent.pages['customers'].edit_entity_by_id(id_val)
            elif page == 'suppliers' and hasattr(self.parent.pages['suppliers'], 'edit_entity_by_id'):
                self.parent.pages['suppliers'].edit_entity_by_id(id_val)
            elif page == 'invoices' and hasattr(self.parent.pages['invoices'], 'view_invoice_by_id'):
                self.parent.pages['invoices'].view_invoice_by_id(id_val)
        self.accept()
