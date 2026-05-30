# views_pyqt5/global_search.py
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QLabel
from PyQt5.QtCore import Qt, QTimer
from database import item_dao, customer_dao, supplier_dao, invoice_dao
from utils_pyqt5 import format_currency
from views_pyqt5.centered_dialog import CenteredDialog

class GlobalSearchDialog(CenteredDialog):
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
        items = item_dao.get_items(search=text)
        for item in items:
            self.add_result("مادة", item.name, 'items', item.id)
        # بحث في العملاء
        customers = customer_dao.get_all(search=text)
        for c in customers:
            self.add_result("عميل", c.name, 'customers', c.id)
        # بحث في الموردين
        suppliers = supplier_dao.get_all(search=text)
        for s in suppliers:
            self.add_result("مورد", s.name, 'suppliers', s.id)
        # بحث في الفواتير
        invoices = invoice_dao.get_all(search=text)
        for inv in invoices:
            ref = inv.reference
            customer_name = inv.customer_name or ''
            supplier_name = inv.supplier_name or ''
            display = f"{ref} - {format_currency(inv.total)}"
            self.add_result("فاتورة", display, 'invoices', inv.id)

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
