# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QTableView,
                             QHeaderView, QMessageBox, QDialog, QFormLayout, QLabel, QComboBox)
from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex
from database import db
from auth import get_all_users, register_user, delete_user, change_password, is_admin
from utils_pyqt5 import show_toast

class UsersTableModel(QAbstractTableModel):
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

class UsersWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        if not is_admin():
            layout = QVBoxLayout(self)
            layout.addWidget(QLabel("هذه الصفحة متاحة فقط للمدير"))
            return
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(6)
        self.layout.setContentsMargins(6,6,6,6)

        top = QHBoxLayout()
        self.add_btn = QPushButton("➕ إضافة مستخدم")
        self.add_btn.setObjectName("primary")
        self.add_btn.clicked.connect(self.add_user)
        top.addWidget(self.add_btn)

        self.delete_btn = QPushButton("🗑 حذف المستخدم المحدد")
        self.delete_btn.setObjectName("danger")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self.delete_selected)
        top.addWidget(self.delete_btn)

        self.layout.addLayout(top)

        self.table = QTableView()
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(self.edit_user)
        # لا نربط الإشارة هنا (النموذج لم يُنشأ بعد)
        self.layout.addWidget(self.table)
        self.refresh()

    def refresh(self):
        users = get_all_users()
        data = []
        for u in users:
            data.append([u['id'], u['username'], u.get('full_name',''), 'مدير' if u['role']=='admin' else 'مستخدم', u.get('created_at',''), u.get('last_login','')])
        headers = ["#", "اسم المستخدم", "الاسم الكامل", "الصلاحية", "تاريخ التسجيل", "آخر دخول"]
        self.model = UsersTableModel(data, headers)
        self.table.setModel(self.model)
        self.table.setColumnHidden(0, True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.delete_btn.setEnabled(False)
        # ربط الإشارة بعد تعيين النموذج
        self.table.selectionModel().selectionChanged.connect(self.on_selection_changed)

    def on_selection_changed(self, selected, deselected):
        self.delete_btn.setEnabled(len(self.table.selectionModel().selectedRows()) > 0)

    def add_user(self):
        self.open_user_dialog()

    def edit_user(self, index):
        row = index.row()
        uid = self.model._data[row][0]
        self.open_user_dialog(is_edit=True, uid=uid)

    def delete_selected(self):
        selection = self.table.selectionModel().selectedRows()
        if not selection:
            return
        row = selection[0].row()
        uid = self.model._data[row][0]
        reply = QMessageBox.question(self, "تأكيد الحذف", "هل تريد حذف هذا المستخدم؟ سيتم حذف جميع بياناته.", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                if delete_user(uid):
                    show_toast("تم حذف المستخدم", "success", self)
                    self.refresh()
                else:
                    show_toast("لا يمكن حذف المستخدم admin", "error", self)
            except Exception as e:
                show_toast(str(e), "error", self)

    def open_user_dialog(self, is_edit=False, uid=None):
        dialog = QDialog(self)
        dialog.setWindowTitle("تعديل مستخدم" if is_edit else "إضافة مستخدم جديد")
        dialog.setModal(True)
        dialog.setLayoutDirection(Qt.RightToLeft)
        dialog.resize(380, 320)
        layout = QFormLayout(dialog)
        username_edit = QLineEdit()
        if is_edit:
            users = get_all_users()
            user = next((u for u in users if u['id']==uid), None)
            if user:
                username_edit.setText(user['username'])
                username_edit.setEnabled(False)
        layout.addRow("اسم المستخدم:", username_edit)
        fullname_edit = QLineEdit()
        if is_edit and user:
            fullname_edit.setText(user.get('full_name',''))
        layout.addRow("الاسم الكامل:", fullname_edit)
        role_combo = QComboBox()
        role_combo.addItems(["مستخدم", "مدير"])
        if is_edit and user and user['role']=='admin':
            role_combo.setCurrentIndex(1)
        layout.addRow("الصلاحية:", role_combo)
        if not is_edit:
            password_edit = QLineEdit()
            password_edit.setEchoMode(QLineEdit.Password)
            layout.addRow("كلمة المرور:", password_edit)
            confirm_edit = QLineEdit()
            confirm_edit.setEchoMode(QLineEdit.Password)
            layout.addRow("تأكيد كلمة المرور:", confirm_edit)
        else:
            change_pass_btn = QPushButton("تغيير كلمة المرور")
            change_pass_btn.clicked.connect(lambda: self.change_password_dialog(uid, dialog))
            layout.addRow(change_pass_btn)
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("حفظ")
        save_btn.setObjectName("primary")
        cancel_btn = QPushButton("إلغاء")
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)
        def on_save():
            if not is_edit:
                username = username_edit.text().strip()
                password = password_edit.text()
                confirm = confirm_edit.text()
                if not username or not password:
                    show_toast("اسم المستخدم وكلمة المرور مطلوبان", "error", dialog)
                    return
                if password != confirm:
                    show_toast("كلمة المرور غير متطابقة", "error", dialog)
                    return
                role = 'admin' if role_combo.currentText()=='مدير' else 'user'
                full_name = fullname_edit.text().strip()
                if register_user(username, password, full_name, role):
                    show_toast("تمت الإضافة", "success", dialog)
                    dialog.accept()
                    self.refresh()
                else:
                    show_toast("اسم المستخدم موجود مسبقاً", "error", dialog)
            else:
                role = 'admin' if role_combo.currentText()=='مدير' else 'user'
                full_name = fullname_edit.text().strip()
                conn = db.connect()
                cur = conn.cursor()
                cur.execute("UPDATE users SET full_name = ?, role = ? WHERE id = ?", (full_name, role, uid))
                conn.commit()
                show_toast("تم التحديث", "success", dialog)
                dialog.accept()
                self.refresh()
        save_btn.clicked.connect(on_save)
        cancel_btn.clicked.connect(dialog.reject)
        dialog.exec()

    def change_password_dialog(self, uid, parent_dialog):
        from database import get_current_user_id
        dialog = QDialog(parent_dialog)
        dialog.setWindowTitle("تغيير كلمة المرور")
        dialog.setModal(True)
        dialog.setLayoutDirection(Qt.RightToLeft)
        layout = QFormLayout(dialog)
        current_user = get_current_user_id()
        if uid == current_user:
            old_edit = QLineEdit()
            old_edit.setEchoMode(QLineEdit.Password)
            layout.addRow("كلمة المرور الحالية:", old_edit)
        new_edit = QLineEdit()
        new_edit.setEchoMode(QLineEdit.Password)
        confirm_edit = QLineEdit()
        confirm_edit.setEchoMode(QLineEdit.Password)
        layout.addRow("كلمة المرور الجديدة:", new_edit)
        layout.addRow("تأكيد كلمة المرور:", confirm_edit)
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("تغيير")
        cancel_btn = QPushButton("إلغاء")
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)
        def on_save():
            new = new_edit.text()
            confirm = confirm_edit.text()
            if not new or new != confirm:
                show_toast("كلمة المرور غير متطابقة", "error", dialog)
                return
            if uid == current_user:
                old = old_edit.text()
                if not old:
                    show_toast("كلمة المرور الحالية مطلوبة", "error", dialog)
                    return
                if change_password(uid, old, new):
                    show_toast("تم تغيير كلمة المرور", "success", dialog)
                    dialog.accept()
                else:
                    show_toast("كلمة المرور الحالية غير صحيحة", "error", dialog)
            else:
                from auth import hash_password
                new_hash = hash_password(new)
                cur = db.connect().cursor()
                cur.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, uid))
                db.connect().commit()
                show_toast("تم تغيير كلمة المرور", "success", dialog)
                dialog.accept()
        save_btn.clicked.connect(on_save)
        cancel_btn.clicked.connect(dialog.reject)
        dialog.exec()
