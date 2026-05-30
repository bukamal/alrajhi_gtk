# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QFrame, QProgressBar, QApplication, QCheckBox
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QSettings
from PyQt5.QtGui import QPixmap
from utils_pyqt5 import format_currency
from views_pyqt5.centered_dialog import CenteredDialog
from database import reporting_dao

class WelcomeScreen(CenteredDialog):
    def __init__(self, user_data, summary_data, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.summary_data = summary_data
        self.settings = QSettings("Alrajhi", "Accounting")
        if self.settings.value("welcome/skip", False, type=bool):
            self.accept()
            return
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self.resize(520, 450)

        main_frame = QFrame(self)
        main_frame.setGeometry(0, 0, 520, 450)
        main_frame.setStyleSheet("""
            QFrame {
                background-color: #1e1e2e;
                border-radius: 20px;
                border: 1px solid #334155;
            }
            QLabel {
                color: #cbd5e1;
                font-family: 'Tajawal';
            }
            QPushButton {
                background-color: #3b82f6;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QCheckBox {
                color: #cbd5e1;
            }
        """)

        layout = QVBoxLayout(main_frame)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignCenter)
        try:
            pix = QPixmap("alrajhi_logo.png").scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_label.setPixmap(pix)
        except:
            icon_label.setText("👋")
            icon_label.setStyleSheet("font-size: 48px;")
        layout.addWidget(icon_label)

        name = user_data.get('full_name') or user_data.get('username')
        role_text = "مدير" if user_data.get('role') == 'admin' else "مستخدم"
        welcome_label = QLabel(f"مرحباً {name}")
        welcome_label.setAlignment(Qt.AlignCenter)
        welcome_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #f1f5f9;")
        layout.addWidget(welcome_label)

        role_label = QLabel(f"الدور: {role_text}")
        role_label.setAlignment(Qt.AlignCenter)
        role_label.setStyleSheet("font-size: 14px; color: #94a3b8;")
        layout.addWidget(role_label)

        summary_frame = QFrame()
        summary_frame.setStyleSheet("background-color: #0f1724; border-radius: 12px; padding: 10px;")
        summary_layout = QVBoxLayout(summary_frame)

        # الأرقام تبدأ مخفية (***)
        self.values_hidden = True
        self.cash_value = summary_data.get('cash_balance', 0)
        self.sales_value = summary_data.get('total_sales', 0)
        self.profit_value = summary_data.get('net_profit', 0)

        self.cash_label = QLabel(f"💰 رصيد الصندوق: ***")
        self.sales_label = QLabel(f"📈 إجمالي المبيعات: ***")
        self.profit_label = QLabel(f"📊 صافي الربح: ***")

        summary_layout.addWidget(self.cash_label)
        summary_layout.addWidget(self.sales_label)
        summary_layout.addWidget(self.profit_label)

        self.toggle_btn = QPushButton("👁️ إظهار الأرقام")
        self.toggle_btn.setObjectName("secondary")
        self.toggle_btn.setStyleSheet("background-color: #334155;")
        self.toggle_btn.clicked.connect(self.toggle_values)
        summary_layout.addWidget(self.toggle_btn)

        layout.addWidget(summary_frame)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("QProgressBar { border: none; background-color: #334155; border-radius: 5px; height: 4px; } QProgressBar::chunk { background-color: #3b82f6; border-radius: 5px; }")
        layout.addWidget(self.progress)

        self.skip_check = QCheckBox("لا تظهر هذه الشاشة مرة أخرى")
        layout.addWidget(self.skip_check)

        self.btn_continue = QPushButton("بدء العمل")
        self.btn_continue.clicked.connect(self.start_loading)
        layout.addWidget(self.btn_continue)

        self.opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_anim.setDuration(400)
        self.opacity_anim.setStartValue(0)
        self.opacity_anim.setEndValue(1)
        self.opacity_anim.start()

    def format_hidden_value(self, val):
        if self.values_hidden:
            return "***"
        else:
            return format_currency(val)

    def toggle_values(self):
        self.values_hidden = not self.values_hidden
        self.cash_label.setText(f"💰 رصيد الصندوق: {self.format_hidden_value(self.cash_value)}")
        self.sales_label.setText(f"📈 إجمالي المبيعات: {self.format_hidden_value(self.sales_value)}")
        self.profit_label.setText(f"📊 صافي الربح: {self.format_hidden_value(self.profit_value)}")
        self.toggle_btn.setText("🙈 إخفاء الأرقام" if not self.values_hidden else "👁️ إظهار الأرقام")

    def start_loading(self):
        self.btn_continue.setEnabled(False)
        if self.skip_check.isChecked():
            self.settings.setValue("welcome/skip", True)
        for i in range(0, 101, 10):
            QTimer.singleShot(i * 5, lambda v=i: self.progress.setValue(v))
        QTimer.singleShot(600, self.accept)
