# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt5.QtCore import Qt, pyqtSignal

class KPICard(QFrame):
    clicked = pyqtSignal()
    def __init__(self, title, value, icon, color="#3b82f6", trend=None, trend_value=None):
        super().__init__()
        self.setObjectName("KPICard")
        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            #KPICard {{
                background-color: white;
                border-radius: 16px;
                border: 1px solid #e2e8f0;
                padding: 16px;
            }}
            #KPICard:hover {{
                background-color: #f8fafc;
                border-color: {color};
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        top_layout = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #475569;")
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"font-size: 24px;")
        top_layout.addWidget(title_label)
        top_layout.addStretch()
        top_layout.addWidget(icon_label)
        layout.addLayout(top_layout)

        self.value_label = QLabel(str(value))
        self.value_label.setStyleSheet(f"font-size: 28px; font-weight: 800; color: {color};")
        layout.addWidget(self.value_label)

        if trend:
            trend_layout = QHBoxLayout()
            trend_icon = QLabel("▲" if trend == "up" else "▼")
            trend_icon.setStyleSheet(f"color: {'#10b981' if trend == 'up' else '#ef4444'}; font-size: 12px;")
            trend_label = QLabel(trend_value)
            trend_label.setStyleSheet(f"color: {'#10b981' if trend == 'up' else '#ef4444'}; font-size: 12px; font-weight: 500;")
            trend_layout.addWidget(trend_icon)
            trend_layout.addWidget(trend_label)
            trend_layout.addStretch()
            layout.addLayout(trend_layout)

    def set_value(self, value):
        self.value_label.setText(str(value))

    def mouseReleaseEvent(self, event):
        self.clicked.emit()
        super().mouseReleaseEvent(event)

class KPICardsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)
        self.cards = []
        self.layout = layout

    def add_card(self, title, value, icon, color="#3b82f6", trend=None, trend_value=None, callback=None):
        card = KPICard(title, value, icon, color, trend, trend_value)
        if callback:
            card.clicked.connect(callback)
        self.layout.addWidget(card)
        self.cards.append(card)
        return card

    def update_card(self, index, value):
        if 0 <= index < len(self.cards):
            self.cards[index].set_value(str(value))

    def clear(self):
        for card in self.cards:
            card.deleteLater()
        self.cards.clear()
