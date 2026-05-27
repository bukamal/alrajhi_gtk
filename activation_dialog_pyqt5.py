import sys, os
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QProgressBar, QApplication, QMessageBox
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QClipboard
from activation import online_activate

class ActivationThread(QThread):
    finished = pyqtSignal(bool, str)
    def __init__(self, key):
        super().__init__()
        self.key = key
    def run(self):
        try:
            online_activate(self.key)
            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))

class ActivationDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("تفعيل النظام")
        self.setModal(True)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setFixedSize(450, 300)
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

        paste_btn = QPushButton("📋 لصق")
        paste_btn.clicked.connect(self.paste_from_clipboard)
        layout.addWidget(paste_btn)

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

    def activate(self):
        key = self.key_entry.text().strip()
        if not key:
            self.status_label.setText("يرجى إدخال مفتاح الترخيص")
            return
        self.activate_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.status_label.setText("جاري الاتصال بالخادم...")
        self.thread = ActivationThread(key)
        self.thread.finished.connect(self.on_finished)
        self.thread.start()

    def on_finished(self, success, error_msg):
        self.progress.setVisible(False)
        self.activate_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "نجاح", "تم التفعيل بنجاح! سيتم إعادة تشغيل التطبيق.")
            self.accept()
            os.execl(sys.executable, sys.executable, *sys.argv)
        else:
            self.status_label.setText(f"خطأ: {error_msg}")
