# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal

def format_large_number(value):
    try:
        num = float(value)
        if num >= 1_000_000_000:
            return f"{num/1_000_000_000:.1f}B"
        elif num >= 1_000_000:
            return f"{num/1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num/1_000:.1f}K"
        else:
            return f"{num:.0f}"
    except:
        return str(value)

class KPICard(QFrame):
    clicked = pyqtSignal()
    def __init__(self, title, original_value, icon, color="#3b82f6", trend=None, trend_value=None):
        super().__init__()
        self.original_value = original_value
        self.hidden = True
        self.color = color
        self.trend = trend
        self.trend_value = trend_value

        self.setObjectName("KPICard")
        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            #KPICard {{
                background-color: white;
                border-radius: 16px;
                border: 1px solid #e2e8f0;
                padding: 16px;
                min-width: 180px;
                max-width: 220px;
            }}
            #KPICard:hover {{
                background-color: #f8fafc;
                border-color: {color};
            }}
            QPushButton#eye_btn {{
                background-color: transparent;
                border: none;
                font-size: 16px;
                cursor: pointer;
                padding: 0;
                margin: 0;
                color: #64748b;
            }}
            QPushButton#eye_btn:hover {{
                color: {color};
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        top_layout = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #475569;")
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"font-size: 24px;")
        self.eye_btn = QPushButton("👁️")
        self.eye_btn.setObjectName("eye_btn")
        self.eye_btn.setFixedSize(24, 24)
        self.eye_btn.clicked.connect(self.toggle_value)
        top_layout.addWidget(title_label)
        top_layout.addStretch()
        top_layout.addWidget(icon_label)
        top_layout.addWidget(self.eye_btn)
        layout.addLayout(top_layout)

        self.value_label = QLabel()
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setWordWrap(True)
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

        self.update_display()

    def toggle_value(self):
        self.hidden = not self.hidden
        self.update_display()

    def update_display(self):
        if self.hidden:
            display_value = "***"
            self.value_label.setStyleSheet(f"font-size: 28px; font-weight: 800; color: {self.color}; letter-spacing: 4px;")
        else:
            val = self.original_value
            if isinstance(val, str) and (len(val) > 8 or (' ' in val and len(val.split()[0]) > 6)):
                try:
                    parts = val.split()
                    num_part = parts[0].replace(',', '').replace('$', '').replace('ل.س', '')
                    num_val = float(num_part)
                    short_num = format_large_number(num_val)
                    symbol = parts[1] if len(parts) > 1 else ''
                    val = f"{short_num} {symbol}".strip()
                except:
                    pass
            elif isinstance(val, (int, float)):
                val = format_large_number(val)
            display_value = str(val)
            if len(display_value) > 8:
                self.value_label.setStyleSheet(f"font-size: 22px; font-weight: 800; color: {self.color};")
            else:
                self.value_label.setStyleSheet(f"font-size: 28px; font-weight: 800; color: {self.color};")
        self.value_label.setText(display_value)

    def set_value(self, new_value):
        self.original_value = new_value
        if not self.hidden:
            self.update_display()

    def mouseReleaseEvent(self, event):
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
            self.cards[index].set_value(value)

    def clear(self):
        for card in self.cards:
            card.deleteLater()
        self.cards.clear()

    def refresh_all_values(self, new_values_list):
        for idx, new_val in enumerate(new_values_list):
            if idx < len(self.cards):
                self.cards[idx].set_value(new_val)
