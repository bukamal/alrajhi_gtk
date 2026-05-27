# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QSplashScreen, QLabel, QProgressBar, QVBoxLayout, QWidget, QApplication
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QPixmap, QColor

class ModernSplashScreen(QSplashScreen):
    def __init__(self):
        self.splash_width = 500
        self.splash_height = 350
        pixmap = QPixmap(self.splash_width, self.splash_height)
        pixmap.fill(QColor(30, 30, 46, 255))
        super().__init__(pixmap)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.widget = QWidget(self)
        self.widget.setGeometry(0, 0, self.splash_width, self.splash_height)
        self.widget.setStyleSheet("""
            QWidget {
                background-color: #1e1e2e;
                border-radius: 15px;
            }
            QLabel {
                color: #cbd5e1;
                font-family: 'Tajawal';
            }
            QProgressBar {
                border: none;
                background-color: #334155;
                border-radius: 5px;
                height: 6px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 5px;
            }
        """)
        
        layout = QVBoxLayout(self.widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        logo_label = QLabel()
        try:
            pix = QPixmap("alrajhi_logo.png").scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(pix)
        except:
            logo_label.setText("🔐")
            logo_label.setStyleSheet("font-size: 48px;")
        logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo_label)
        
        title = QLabel("نظام الراجحي للمحاسبة")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #f1f5f9;")
        layout.addWidget(title)
        
        self.message_label = QLabel("جاري تهيئة النظام...")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setStyleSheet("font-size: 13px; color: #94a3b8;")
        layout.addWidget(self.message_label)
        
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)
        
        layout.addStretch()
        
        self.opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_anim.setDuration(500)
        self.opacity_anim.setStartValue(0)
        self.opacity_anim.setEndValue(1)
        self.opacity_anim.setEasingCurve(QEasingCurve.InOutQuad)
        
    def showEvent(self, event):
        self.opacity_anim.start()
        super().showEvent(event)
        
    def set_progress(self, value, message=None):
        self.progress.setValue(value)
        if message:
            self.message_label.setText(message)
        QApplication.processEvents()
        
    def finish_splash(self, main_window):
        self.opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_anim.setDuration(300)
        self.opacity_anim.setStartValue(1)
        self.opacity_anim.setEndValue(0)
        self.opacity_anim.finished.connect(self.close)
        self.opacity_anim.start()
        QTimer.singleShot(300, lambda: main_window.show())
