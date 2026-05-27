# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QTimer, QRect

class ToastNotification(QWidget):
    def __init__(self, message, msg_type="info", parent=None, duration=3000):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(350)
        self.setFixedHeight(70)
        self.duration = duration

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        self.setStyleSheet(self.get_style(msg_type))

        icon_label = QLabel(self.get_icon(msg_type))
        icon_label.setStyleSheet("font-size: 24px;")
        layout.addWidget(icon_label)

        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("color: #1e293b; font-weight: 500;")
        layout.addWidget(msg_label)

        self.close_btn = QLabel("✕")
        self.close_btn.setStyleSheet("color: #94a3b8; font-size: 14px;")
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.mousePressEvent = self.close
        layout.addWidget(self.close_btn)

    def get_style(self, msg_type):
        colors = {
            "success": "#dcfce7",
            "error": "#fee2e2",
            "warning": "#fef3c7",
            "info": "#dbeafe"
        }
        bg = colors.get(msg_type, "#dbeafe")
        return f"""
            QWidget {{
                background-color: {bg};
                border-radius: 12px;
                border: 1px solid #cbd5e1;
            }}
        """

    def get_icon(self, msg_type):
        icons = {
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️"
        }
        return icons.get(msg_type, "ℹ️")

    def show_toast(self):
        parent_rect = self.parent().geometry() if self.parent() else QRect(0, 0, 800, 600)
        x = parent_rect.right() - self.width() - 20
        y = parent_rect.top() + 20
        self.move(x, y)
        self.show()
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(300)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation.start()
        QTimer.singleShot(self.duration, self.close)

    def close(self, event=None):
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(300)
        self.animation.setStartValue(1)
        self.animation.setEndValue(0)
        self.animation.finished.connect(self.deleteLater)
        self.animation.start()
