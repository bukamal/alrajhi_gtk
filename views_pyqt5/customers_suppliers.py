# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QTableView,
                             QHeaderView, QMessageBox, QDialog, QFormLayout, QLabel)
from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex
from database import db
from utils_pyqt5 import format_currency, show_toast

class EntityTableModel(QAbstractTableModel):
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

class CustomersSuppliersWidget(QWidget):
    def __init__(self, parent=None, entity_type='customer'):
        super().__init__(parent)
        self.entity_type = entity_type
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(6)
        self.layout.setContentsMargins(6,6,6,6)

        top = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("بحث...")
        self.search_edit.textChanged.connect(self.refresh)
        top.addWidget(self.search_edit)

        self.add_btn = QPushButton("➕ إضافة")
        self.add_btn.setObjectName("primary")
        self.add_btn.clicked.connect(self.add_entity)
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
        self.table.doubleClicked.connect(self.edit_entity)
        self.layout.addWidget(self.table)
        self.refresh()

    def refresh(self):
        search = self.search_edit.text().strip().lower()
        entities = db.get_customers() if self.entity_type=='customer' else db.get_suppliers()
        if search:
            entities = [e for e in entities if search in e['name'].lower() or search in e.get('phone','').lower()]
        data = []
        for e in entities:
            data.append([e['id'], e['name'], e.get('phone',''), e.get('address',''), format_currency(e['balance'])])
        headers = ["#", "الاسم", "الهاتف", "العنوان", "الرصيد"]
        self.model = EntityTableModel(data, headers)
        self.table.setModel(self.model)
        self.table.setColumnHidden(0, True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.resizeRowsToContents()
        self.delete_btn.setEnabled(False)
        self.table.selectionModel().selectionChanged.connect(self.on_selection_changed)

    def on_selection_changed(self, selected, deselected):
        self.delete_btn.setEnabled(len(self.table.selectionModel().selectedRows()) > 0)

    def add_entity(self):
        self.open_entity_dialog()

    def edit_entity(self, index):
        row = index.row()
        eid = self.model._data[row][0]
        self.open_entity_dialog(is_edit=True, eid=eid)

    def delete_selected(self):
        selection = self.table.selectionModel().selectedRows()
        if not selection:
            return
        row = selection[0].row()
        eid = self.model._data[row][0]
        reply = QMessageBox.question(self, "تأكيد الحذف", f"هل تريد حذف هذا {self.entity_type}؟", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                if self.entity_type == 'customer':
                    db.delete_customer(eid)
                else:
                    db.delete_supplier(eid)
                show_toast("تم الحذف", "success", self)
                self.refresh()
            except Exception as e:
                show_toast(str(e), "error", self)

    def open_entity_dialog(self, is_edit=False, eid=None):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"تعديل {self.entity_type}" if is_edit else f"إضافة {self.entity_type}")
        dialog.setModal(True)
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
