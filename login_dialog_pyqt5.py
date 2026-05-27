from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt5.QtCore import Qt
from database import db

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("تسجيل الدخول")
        self.setModal(True)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setFixedSize(400, 280)
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
        self.password = QLineEdit()
        self.password.setPlaceholderText("كلمة المرور")
        self.password.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password)
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: red;")
        layout.addWidget(self.error_label)
        btn_login = QPushButton("دخول")
        btn_login.clicked.connect(self.do_login)
        btn_cancel = QPushButton("إلغاء")
        btn_cancel.clicked.connect(self.reject)
        layout.addWidget(btn_login)
        layout.addWidget(btn_cancel)

    def do_login(self):
        user = self.username.text().strip()
        pwd = self.password.text()
        if not user or not pwd:
            self.error_label.setText("يرجى إدخال اسم المستخدم وكلمة المرور")
            return
        if db.login(user, pwd):
            self.accept()
        else:
            self.error_label.setText("اسم المستخدم أو كلمة المرور غير صحيحة")
            self.password.clear()
