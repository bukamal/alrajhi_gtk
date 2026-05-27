# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QTableView,
                             QHeaderView, QMessageBox, QDialog, QFormLayout, QLabel, QDateEdit)
from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, QDate
from database import db
from utils_pyqt5 import format_currency, show_toast

class ExpensesTableModel(QAbstractTableModel):
    def __init__(self, data, headers):
        super().__init__()
        self._data = data
        self._headers = headers
    def rowCount(self, parent=QModelIndex()): return len(self._data)
    def columnCount(self, parent=QModelIndex()): return len(self._headers)
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid(): return None
        if role == Qt.DisplayRole: return str(self._data[index.row()][index.column()])
        return None
    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole: return self._headers[section]
        return None
    def update_data(self, new_data):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()

class ExpensesWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(6)
        self.layout.setContentsMargins(6,6,6,6)

        top = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("بحث عن مصروف...")
        self.search_edit.textChanged.connect(self.refresh)
        top.addWidget(self.search_edit)

        self.add_btn = QPushButton("➕ إضافة مصروف")
        self.add_btn.setObjectName("primary")
        self.add_btn.clicked.connect(self.add_expense)
        top.addWidget(self.add_btn)
        self.layout.addLayout(top)

        self.table = QTableView()
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(self.delete_expense)
        self.layout.addWidget(self.table)
        self.refresh()

    def refresh(self):
        search = self.search_edit.text().strip().lower()
        expenses = db.get_expenses()
        if search:
            expenses = [e for e in expenses if search in e.get('description','').lower()]
        data = []
        for e in expenses:
            data.append([e['id'], e['expense_date'], e.get('description',''), format_currency(e['amount'])])
        headers = ["#", "التاريخ", "الوصف", "المبلغ"]
        self.model = ExpensesTableModel(data, headers)
        self.table.setModel(self.model)
        self.table.setColumnHidden(0, True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.resizeRowsToContents()

    def add_expense(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("إضافة مصروف جديد")
        dialog.setModal(True)
        dialog.setLayoutDirection(Qt.RightToLeft)
        dialog.resize(360, 220)
        layout = QFormLayout(dialog)
        amount_edit = QLineEdit()
        layout.addRow("المبلغ:", amount_edit)
        desc_edit = QLineEdit()
        layout.addRow("الوصف:", desc_edit)
        date_edit = QDateEdit()
        date_edit.setDate(QDate.currentDate())
        layout.addRow("التاريخ:", date_edit)
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("حفظ")
        save_btn.setObjectName("primary")
        cancel_btn = QPushButton("إلغاء")
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)
        def on_save():
            try:
                amount = float(amount_edit.text())
                if amount <= 0:
                    show_toast("المبلغ يجب أن يكون أكبر من صفر", "error", dialog)
                    return
                date_str = date_edit.date().toString("yyyy-MM-dd")
                description = desc_edit.text().strip()
                db.add_expense(amount, date_str, description)
                show_toast("تمت الإضافة", "success", dialog)
                dialog.accept()
                self.refresh()
            except:
                show_toast("المبلغ غير صحيح", "error", dialog)
        save_btn.clicked.connect(on_save)
        cancel_btn.clicked.connect(dialog.reject)
        dialog.exec()

    def delete_expense(self, index):
        row = index.row()
        exp_id = self.model._data[row][0]
        reply = QMessageBox.question(self, "تأكيد الحذف", "هل تريد حذف هذا المصروف؟", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                db.delete_expense(exp_id)
                show_toast("تم الحذف", "success")
                self.refresh()
            except Exception as e:
                show_toast(str(e), "error")
