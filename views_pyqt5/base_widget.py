# views_pyqt5/base_widget.py
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QTableView, QMessageBox, QHeaderView, QLabel
from PyQt5.QtCore import Qt
from utils_pyqt5 import show_toast
from views_pyqt5.modern_table import ModernTableView
from views_pyqt5.base_table_model import BaseTableModel
from views_pyqt5.centered_dialog import show_centered_messagebox

class BaseWidget(QWidget):
    entity_name = "العنصر"
    search_placeholder = "بحث..."
    headers = []
    has_delete = True
    has_add = True
    has_export = True
    has_print = True
    has_pagination = False   # تفعيل pagination في الكلاسات الفرعية
    page_size = 50
    extra_buttons = []

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_id = None
        self.current_name = None
        self.model = None
        self.table = None
        self.current_page = 0
        self.total_count = 0
        self.init_base_ui()
        self.refresh()

    def init_base_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(6)
        self.layout.setContentsMargins(6, 6, 6, 6)

        self.btn_layout = QHBoxLayout()
        if self.has_add:
            self.add_btn = QPushButton(f"➕ إضافة {self.entity_name}")
            self.add_btn.setObjectName("primary")
            self.add_btn.clicked.connect(self.add_item)
            self.btn_layout.addWidget(self.add_btn)

        if self.has_delete:
            self.delete_btn = QPushButton(f"🗑 حذف المحدد")
            self.delete_btn.setObjectName("danger")
            self.delete_btn.setEnabled(False)
            self.delete_btn.clicked.connect(self.delete_selected)
            self.btn_layout.addWidget(self.delete_btn)

        for btn_text, callback_name, btn_name in self.extra_buttons:
            btn = QPushButton(btn_text)
            callback = getattr(self, callback_name, None)
            if callback:
                btn.clicked.connect(callback)
            btn.setEnabled(False)
            setattr(self, btn_name, btn)
            self.btn_layout.addWidget(btn)

        if self.has_export:
            self.export_btn = QPushButton("📊 Excel")
            self.export_btn.clicked.connect(self.export_to_excel)
            self.btn_layout.addWidget(self.export_btn)

        if self.has_print:
            self.print_btn = QPushButton("🖨️ طباعة")
            self.print_btn.clicked.connect(self.print_list)
            self.btn_layout.addWidget(self.print_btn)

        self.refresh_btn = QPushButton("🔄 تحديث")
        self.refresh_btn.clicked.connect(self.refresh)
        self.btn_layout.addWidget(self.refresh_btn)
        self.btn_layout.addStretch()
        self.layout.addLayout(self.btn_layout)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(self.search_placeholder)
        self.search_edit.textChanged.connect(self.refresh)
        self.layout.addWidget(self.search_edit)

        self.table = ModernTableView()
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setAlternatingRowColors(True)
        if hasattr(self, 'on_double_click'):
            self.table.doubleClicked.connect(self.on_double_click)
        else:
            self.table.doubleClicked.connect(self.edit_item)
        self.layout.addWidget(self.table)

        if self.has_pagination:
            self.pagination_layout = QHBoxLayout()
            self.prev_btn = QPushButton("السابق")
            self.prev_btn.clicked.connect(self.prev_page)
            self.next_btn = QPushButton("التالي")
            self.next_btn.clicked.connect(self.next_page)
            self.page_label = QLabel()
            self.pagination_layout.addWidget(self.prev_btn)
            self.pagination_layout.addWidget(self.page_label)
            self.pagination_layout.addWidget(self.next_btn)
            self.pagination_layout.addStretch()
            self.layout.addLayout(self.pagination_layout)

        self.status_label = QLabel()
        self.layout.addWidget(self.status_label)

    def fetch_data(self, search: str = None, limit: int = None, offset: int = None):
        raise NotImplementedError

    def get_total_count(self, search: str = None) -> int:
        return 0

    def delete_item(self, item_id):
        raise NotImplementedError

    def open_dialog(self, is_edit=False, item_id=None):
        raise NotImplementedError

    def get_item_name(self, row_data):
        return str(row_data[1]) if len(row_data) > 1 else "العنصر"

    def refresh(self):
        search = self.search_edit.text().strip().lower() or None
        if self.has_pagination:
            self.total_count = self.get_total_count(search)
            offset = self.current_page * self.page_size
            items = self.fetch_data(search, limit=self.page_size, offset=offset)
            total_pages = (self.total_count + self.page_size - 1) // self.page_size
            self.page_label.setText(f"الصفحة {self.current_page + 1} من {total_pages}")
            self.prev_btn.setEnabled(self.current_page > 0)
            self.next_btn.setEnabled(self.current_page + 1 < total_pages)
        else:
            items = self.fetch_data(search)

        if items is None:
            items = []
        data = self.prepare_table_data(items)
        self.model = BaseTableModel(data, self.headers)
        self.table.setModel(self.model)
        self.table.setColumnHidden(0, True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.after_refresh()

        if self.table.selectionModel():
            try:
                self.table.selectionModel().selectionChanged.disconnect()
            except:
                pass
            self.table.selectionModel().selectionChanged.connect(self.on_selection_changed)

        self.set_action_buttons_enabled(False)
        self.current_id = None
        self.current_name = None
        self.status_label.setText(f"إجمالي السجلات: {self.total_count if self.has_pagination else len(items)}")

    def after_refresh(self):
        pass

    def prepare_table_data(self, items):
        return [[item.get('id'), item.get('name', '')] for item in items]

    def on_selection_changed(self, selected, deselected):
        rows = self.table.selectionModel().selectedRows()
        if rows:
            row = rows[0].row()
            self.current_id = self.model._data[row][0]
            self.current_name = self.get_item_name(self.model._data[row])
            self.set_action_buttons_enabled(True)
        else:
            self.current_id = None
            self.current_name = None
            self.set_action_buttons_enabled(False)

    def set_action_buttons_enabled(self, enabled):
        if self.has_delete and hasattr(self, 'delete_btn'):
            self.delete_btn.setEnabled(enabled)
        for _, _, btn_name in self.extra_buttons:
            if hasattr(self, btn_name):
                getattr(self, btn_name).setEnabled(enabled)

    def add_item(self):
        self.open_dialog(is_edit=False)

    def edit_item(self, index):
        row = index.row()
        if row < 0 or not hasattr(self, 'model') or row >= len(self.model._data):
            return
        item_id = self.model._data[row][0]
        self.open_dialog(is_edit=True, item_id=item_id)

    def on_double_click(self, index):
        self.edit_item(index)

    def delete_selected(self):
        if not self.current_id:
            show_toast("لم يتم تحديد عنصر", "error", self)
            return
        reply = show_centered_messagebox(
            self, "تأكيد الحذف",
            f"هل تريد حذف هذا {self.entity_name}؟",
            QMessageBox.Question, QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                self.delete_item(self.current_id)
                show_toast("تم الحذف", "success", self)
                self.refresh()
            except Exception as e:
                show_toast(str(e), "error", self)

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

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.refresh()

    def next_page(self):
        self.current_page += 1
        self.refresh()
