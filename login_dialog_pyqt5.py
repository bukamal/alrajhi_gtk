# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, QCheckBox
from PyQt5.QtCore import Qt, QSettings
from database import user_dao, Session
from views_pyqt5.centered_dialog import CenteredDialog

class LoginDialog(CenteredDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("تسجيل الدخول")
        self.setModal(True)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setFixedSize(420, 320)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20,20,20,20)

        logo = QLabel("🔐")
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet("font-size: 48px;")
        layout.addWidget(logo)

        title = QLabel("نظام الراجحي للمحاسبة")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        self.username = QLineEdit()
        self.username.setPlaceholderText("اسم المستخدم")
        layout.addWidget(self.username)

        pwd_layout = QHBoxLayout()
        self.password = QLineEdit()
        self.password.setPlaceholderText("كلمة المرور")
        self.password.setEchoMode(QLineEdit.Password)
        self.password.returnPressed.connect(self.do_login)
        self.toggle_pwd_btn = QPushButton("👁️")
        self.toggle_pwd_btn.setFixedSize(30, 30)
        self.toggle_pwd_btn.setCheckable(True)
        self.toggle_pwd_btn.toggled.connect(self.toggle_password_visibility)
        pwd_layout.addWidget(self.password)
        pwd_layout.addWidget(self.toggle_pwd_btn)
        layout.addLayout(pwd_layout)

        self.remember_check = QCheckBox("تذكر اسم المستخدم")
        layout.addWidget(self.remember_check)

        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: red;")
        layout.addWidget(self.error_label)

        btn_login = QPushButton("دخول")
        btn_login.clicked.connect(self.do_login)
        btn_cancel = QPushButton("إلغاء")
        btn_cancel.clicked.connect(self.reject)
        layout.addWidget(btn_login)
        layout.addWidget(btn_cancel)

        self.settings = QSettings("Alrajhi", "Accounting")
        saved_username = self.settings.value("login/username", "")
        if saved_username:
            self.username.setText(saved_username)
            self.remember_check.setChecked(True)
            self.password.setFocus()

    def toggle_password_visibility(self, checked):
        if checked:
            self.password.setEchoMode(QLineEdit.Normal)
            self.toggle_pwd_btn.setText("🙈")
        else:
            self.password.setEchoMode(QLineEdit.Password)
            self.toggle_pwd_btn.setText("👁️")

    def do_login(self):
        user = self.username.text().strip()
        pwd = self.password.text()
        if not user or not pwd:
            self.error_label.setText("يرجى إدخال اسم المستخدم وكلمة المرور")
            return
        if user_dao.login(user, pwd):
            if self.remember_check.isChecked():
                self.settings.setValue("login/username", user)
            else:
                self.settings.remove("login/username")
            self.accept()
        else:
            self.error_label.setText("اسم المستخدم أو كلمة المرور غير صحيحة")
            self.password.clear()
            self.password.setFocus()
