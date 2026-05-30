# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QFormLayout, QLineEdit, QPushButton, QHBoxLayout, QMessageBox
from PyQt5.QtCore import Qt
from views_pyqt5.centered_dialog import CenteredDialog, show_centered_messagebox
from auth import change_password
from database.connection import DatabaseConnection

class ChangePasswordDialog(CenteredDialog):
    def __init__(self, user_id, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.setWindowTitle("تغيير كلمة المرور")
        self.setModal(True)
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(400, 220)
        # جعل النافذة تظهر دائماً في المقدمة
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        layout = QFormLayout(self)

        self.old_password_edit = QLineEdit()
        self.old_password_edit.setEchoMode(QLineEdit.Password)
        layout.addRow("كلمة المرور الحالية:", self.old_password_edit)

        self.new_password_edit = QLineEdit()
        self.new_password_edit.setEchoMode(QLineEdit.Password)
        layout.addRow("كلمة المرور الجديدة:", self.new_password_edit)

        self.confirm_edit = QLineEdit()
        self.confirm_edit.setEchoMode(QLineEdit.Password)
        layout.addRow("تأكيد كلمة المرور:", self.confirm_edit)

        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("تغيير")
        self.save_btn.setObjectName("primary")
        self.save_btn.clicked.connect(self.on_save)
        self.cancel_btn = QPushButton("إلغاء")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addRow(btn_layout)
        self.raise_()  # رفع النافذة للأمام

    def on_save(self):
        old = self.old_password_edit.text()
        new = self.new_password_edit.text()
        confirm = self.confirm_edit.text()
        if not old or not new:
            show_centered_messagebox(self, "خطأ", "جميع الحقول مطلوبة", QMessageBox.Warning)
            return
        if new != confirm:
            show_centered_messagebox(self, "خطأ", "كلمتا المرور غير متطابقتين", QMessageBox.Warning)
            return
        if change_password(self.user_id, old, new):
            show_centered_messagebox(self, "نجاح", "تم تغيير كلمة المرور بنجاح", QMessageBox.Information)
            self.accept()
        else:
            show_centered_messagebox(self, "خطأ", "كلمة المرور الحالية غير صحيحة", QMessageBox.Warning)


class ChangeAdminPasswordDialog(CenteredDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("تغيير كلمة مرور المسؤول")
        self.setModal(True)
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(400, 200)
        # جعل النافذة تظهر دائماً في المقدمة
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        layout = QFormLayout(self)

        self.new_password_edit = QLineEdit()
        self.new_password_edit.setEchoMode(QLineEdit.Password)
        layout.addRow("كلمة المرور الجديدة:", self.new_password_edit)

        self.confirm_edit = QLineEdit()
        self.confirm_edit.setEchoMode(QLineEdit.Password)
        layout.addRow("تأكيد كلمة المرور:", self.confirm_edit)

        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("حفظ")
        self.save_btn.setObjectName("primary")
        self.save_btn.clicked.connect(self.on_save)
        self.cancel_btn = QPushButton("إلغاء")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addRow(btn_layout)
        self.raise_()

    def on_save(self):
        new_pwd = self.new_password_edit.text()
        confirm = self.confirm_edit.text()
        if not new_pwd:
            show_centered_messagebox(self, "خطأ", "كلمة المرور مطلوبة", QMessageBox.Warning)
            return
        if new_pwd != confirm:
            show_centered_messagebox(self, "خطأ", "كلمتا المرور غير متطابقتين", QMessageBox.Warning)
            return
        db_conn = DatabaseConnection()
        db_conn.change_admin_password(new_pwd)
        show_centered_messagebox(self, "نجاح", "تم تغيير كلمة مرور المسؤول", QMessageBox.Information)
        self.accept()
