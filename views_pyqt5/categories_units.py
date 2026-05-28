# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QTableView,
                             QHeaderView, QMessageBox, QDialog, QFormLayout, QLabel)
from PyQt5.QtCore import Qt
from database import db
from utils_pyqt5 import show_toast
from views_pyqt5.base_table_model import BaseTableModel
from views_pyqt5.centered_dialog import CenteredDialog

class CategoriesUnitsWidget(QWidget):
    def __init__(self, parent=None, entity_type='category'):
        super().__init__(parent)
        self.entity_type = 'category'
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(6)
        self.layout.setContentsMargins(6,6,6,6)

        top = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("بحث...")
        self.search_edit.textChanged.connect(self.refresh)
        top.addWidget(self.search_edit)

        self.add_btn = QPushButton("➕ إضافة تصنيف")
        self.add_btn.setObjectName("primary")
        self.add_btn.clicked.connect(self.add_item)
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
        self.table.doubleClicked.connect(self.edit_item)
        self.layout.addWidget(self.table)
        self.refresh()

    def refresh(self):
        search = self.search_edit.text().strip().lower()
        items = db.get_categories()
        if search:
            items = [i for i in items if search in i['name'].lower()]
        data = [[i['id'], i['name']] for i in items]
        headers = ["#", "الاسم"]
        self.model = BaseTableModel(data, headers)
        self.table.setModel(self.model)
        self.table.setColumnHidden(0, True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.delete_btn.setEnabled(False)
        self.table.selectionModel().selectionChanged.connect(self.on_selection_changed)

    def on_selection_changed(self, selected, deselected):
        self.delete_btn.setEnabled(len(self.table.selectionModel().selectedRows()) > 0)

    def add_item(self):
        self.open_dialog()

    def edit_item(self, index):
        row = index.row()
        iid = self.model._data[row][0]
        self.open_dialog(is_edit=True, iid=iid)

    def delete_selected(self):
        selection = self.table.selectionModel().selectedRows()
        if not selection:
            return
        row = selection[0].row()
        cid = self.model._data[row][0]
        reply = QMessageBox.question(self, "تأكيد الحذف", "هل تريد حذف هذا التصنيف؟", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                db.delete_category(cid)
                show_toast("تم الحذف", "success", self)
                self.refresh()
            except Exception as e:
                show_toast(str(e), "error", self)

    def open_dialog(self, is_edit=False, iid=None):
        dialog = CenteredDialog(self)
        dialog.setWindowTitle(f"تعديل تصنيف" if is_edit else "إضافة تصنيف")
        dialog.setLayoutDirection(Qt.RightToLeft)
        dialog.resize(320, 140)
        layout = QFormLayout(dialog)
        name_edit = QLineEdit()
        layout.addRow("الاسم:", name_edit)
        if is_edit and iid:
            items = db.get_categories()
            item = next((i for i in items if i['id']==iid), None)
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
                show_toast("الاسم مطلوب", "error", dialog)
                return
            try:
                if is_edit:
                    db.update_category(iid, name)
                    show_toast("تم التحديث", "success", dialog)
                else:
                    db.add_category(name)
                    show_toast("تمت الإضافة", "success", dialog)
                dialog.accept()
                self.refresh()
            except Exception as e:
                show_toast(str(e), "error", dialog)
        save_btn.clicked.connect(on_save)
        cancel_btn.clicked.connect(dialog.reject)
        dialog.exec()
