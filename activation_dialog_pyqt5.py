# -*- coding: utf-8 -*-
import sys, os
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QProgressBar, QApplication, QMessageBox
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QClipboard
from activation import online_activate
from views_pyqt5.centered_dialog import CenteredDialog

class ActivationThread(QThread):
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(int, str)
    def __init__(self, key):
        super().__init__()
        self.key = key
    def run(self):
        try:
            self.progress.emit(30, "جاري الاتصال بالخادم...")
            online_activate(self.key)
            self.progress.emit(100, "تم التفعيل بنجاح")
            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))

class ActivationDialog(CenteredDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("تفعيل النظام")
        self.setModal(True)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setFixedSize(480, 350)
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

        desc = QLabel("أدخل مفتاح الترخيص للتفعيل عبر الإنترنت")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        self.key_entry = QLineEdit()
        self.key_entry.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        layout.addWidget(self.key_entry)

        btn_layout = QHBoxLayout()
        paste_btn = QPushButton("📋 لصق")
        paste_btn.clicked.connect(self.paste_from_clipboard)
        self.test_btn = QPushButton("🌐 اختبار الاتصال")
        self.test_btn.clicked.connect(self.test_connection)
        btn_layout.addWidget(paste_btn)
        btn_layout.addWidget(self.test_btn)
        layout.addLayout(btn_layout)

        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: red;")
        layout.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.activate_btn = QPushButton("تفعيل")
        self.activate_btn.clicked.connect(self.activate)
        self.cancel_btn = QPushButton("إلغاء")
        self.cancel_btn.clicked.connect(self.reject)

        layout.addWidget(self.activate_btn)
        layout.addWidget(self.cancel_btn)

    def paste_from_clipboard(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            self.key_entry.setText(text)

    def test_connection(self):
        import requests
        from activation import SERVER_URL
        self.status_label.setStyleSheet("color: blue;")
        self.status_label.setText("جاري اختبار الاتصال...")
        QApplication.processEvents()
        try:
            response = requests.head(SERVER_URL, timeout=10)
            if response.status_code < 500:
                self.status_label.setStyleSheet("color: green;")
                self.status_label.setText("✓ الخادم متاح")
            else:
                raise Exception("الخادم لا يستجيب")
        except requests.exceptions.ConnectionError:
            self.status_label.setStyleSheet("color: red;")
            self.status_label.setText("✗ فشل الاتصال بالإنترنت أو الخادم")
        except Exception as e:
            self.status_label.setStyleSheet("color: red;")
            self.status_label.setText(f"✗ خطأ: {str(e)[:50]}")

    def activate(self):
        key = self.key_entry.text().strip()
        if not key:
            self.status_label.setStyleSheet("color: red;")
            self.status_label.setText("يرجى إدخال مفتاح الترخيص")
            return
        self.activate_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.test_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.status_label.setStyleSheet("color: blue;")
        self.status_label.setText("جاري الاتصال بالخادم...")
        self.thread = ActivationThread(key)
        self.thread.progress.connect(self.update_progress)
        self.thread.finished.connect(self.on_finished)
        self.thread.start()

    def update_progress(self, value, message):
        self.progress.setValue(value)
        self.status_label.setText(message)
        QApplication.processEvents()

    def on_finished(self, success, error_msg):
        self.progress.setVisible(False)
        self.activate_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        self.test_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "نجاح", "تم التفعيل بنجاح! سيتم إعادة تشغيل التطبيق.")
            self.accept()
            os.execl(sys.executable, sys.executable, *sys.argv)
        else:
            self.status_label.setStyleSheet("color: red;")
            if "ConnectionError" in error_msg or "لا يوجد اتصال" in error_msg:
                self.status_label.setText("✗ لا يوجد اتصال بالإنترنت. يرجى التحقق من الاتصال.")
            elif "Timeout" in error_msg:
                self.status_label.setText("✗ انتهت مهلة الاتصال. حاول مرة أخرى.")
            elif "توقيع غير صالح" in error_msg:
                self.status_label.setText("✗ مفتاح الترخيص غير صالح.")
            else:
                self.status_label.setText(f"✗ خطأ: {error_msg}")
