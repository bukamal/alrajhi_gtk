# views_pyqt5/categories_units.py
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QTableView,
                             QHeaderView, QMessageBox, QDialog, QFormLayout, QLabel)
from PyQt5.QtCore import Qt
from database import category_dao
from utils_pyqt5 import show_toast
from views_pyqt5.base_table_model import BaseTableModel
from views_pyqt5.centered_dialog import CenteredDialog, show_centered_messagebox
from views_pyqt5.base_widget import BaseWidget


class CategoriesUnitsWidget(BaseWidget):
    entity_name = "تصنيف"
    search_placeholder = "بحث عن تصنيف..."
    headers = ["#", "الاسم"]
    has_export = True
    has_print = True
    has_add = True
    has_delete = True
    extra_buttons = []

    def __init__(self, parent=None, entity_type='category'):
        self.entity_type = 'category'
        super().__init__(parent)

    def fetch_data(self, search=None, limit=None, offset=None):
        items = category_dao.get_all()
        if search:
            items = [i for i in items if search in i['name'].lower()]
        return items

    def prepare_table_data(self, items):
        return [[i['id'], i['name']] for i in items]

    def delete_item(self, item_id):
        category_dao.delete(item_id)

    def open_dialog(self, is_edit=False, item_id=None, dialog_parent=None):
        parent_for_dialog = dialog_parent if dialog_parent else self
        dialog = CenteredDialog(parent_for_dialog)
        dialog.setWindowTitle(f"تعديل تصنيف" if is_edit else "إضافة تصنيف")
        dialog.setLayoutDirection(Qt.RightToLeft)
        dialog.resize(320, 140)
        layout = QFormLayout(dialog)
        name_edit = QLineEdit()
        layout.addRow("الاسم:", name_edit)

        if is_edit and item_id:
            items = category_dao.get_all()
            item = next((i for i in items if i['id'] == item_id), None)
            if item:
                name_edit.setText(item['name'])

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
            try:
                if is_edit:
                    category_dao.update(item_id, name)
                    show_toast("تم التحديث", "success", dialog)
                else:
                    category_dao.add(name)
                    show_toast("تمت الإضافة", "success", dialog)
                dialog.accept()
                self.refresh()
            except Exception as e:
                show_centered_messagebox(dialog, "خطأ", str(e), QMessageBox.Critical)

        save_btn.clicked.connect(on_save)
        cancel_btn.clicked.connect(dialog.reject)
        dialog.exec()
