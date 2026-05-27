# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QPushButton, QLabel, QFrame,
                             QToolButton, QMenu, QSizePolicy, QApplication)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon
import qtawesome as qta

class TopBarButton(QPushButton):
    """ زر الشريط العلوي المخصص """
    def __init__(self, text, icon_name, badge_count=0, parent=None):
        super().__init__(parent)
        self.setObjectName("TopBarButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(50)
        self.setMinimumWidth(70)
        self.setIcon(qta.icon(f'fa5s.{icon_name}'))
        self.setIconSize(QSize(24, 24))
        self.setText(text)
        self.setToolTip(text)
        self.setLayoutDirection(Qt.RightToLeft)

        # Badge (إشعار)
        self.badge = QLabel(str(badge_count) if badge_count > 0 else "")
        self.badge.setStyleSheet("""
            background-color: #ef4444;
            color: white;
            border-radius: 12px;
            padding: 2px 6px;
            font-size: 10px;
            font-weight: bold;
            margin-left: 4px;
        """)
        self.badge.setVisible(badge_count > 0)
        self.badge.move(self.width() - 20, 5)

    def resizeEvent(self, event):
        # تحديث موضع الشارة عند تغيير حجم الزر
        self.badge.move(self.width() - 25, 5)
        super().resizeEvent(event)

    def set_badge(self, count):
        self.badge.setText(str(count) if count > 0 else "")
        self.badge.setVisible(count > 0)

    def set_icon_only(self, icon_only):
        if icon_only:
            self.setText("")
            self.setToolTip(self.original_text)
        else:
            self.setText(self.original_text)
            self.setToolTip("")
        self.setMinimumWidth(50 if icon_only else 70)

    def set_text(self, text):
        self.original_text = text
        self.setText(text)

class ModernTopBar(QWidget):
    """ شريط علوي حديث يحتوي على أزرار التحكم الرئيسية """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ModernTopBar")
        self.setFixedHeight(60)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.init_ui()
        self.setup_responsive_behavior()
        self.buttons = {}

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 5, 15, 5)
        layout.setSpacing(8)

        # زر القائمة (هامبرغر) لفتح شريط جانبي اختياري (يمكن إخفاؤه)
        self.menu_btn = QToolButton()
        self.menu_btn.setIcon(qta.icon('fa5s.bars'))
        self.menu_btn.setIconSize(QSize(28, 28))
        self.menu_btn.setCursor(Qt.PointingHandCursor)
        self.menu_btn.setToolTip("القائمة")
        self.menu_btn.clicked.connect(self.toggle_sidebar)
        layout.addWidget(self.menu_btn)

        # شعار التطبيق
        self.logo_label = QLabel("الراجحي")
        self.logo_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.logo_label.setAlignment(Qt.AlignRight)
        layout.addWidget(self.logo_label)

        # مساحة مرنة تفصل بين الشعار والأزرار (حتى تبقى الأزرار في اليمين)
        layout.addStretch()

        # الحاوية الرئيسية للأزرار (تضاف ديناميكياً)
        self.buttons_container = QHBoxLayout()
        self.buttons_container.setSpacing(8)
        layout.addLayout(self.buttons_container)

        # قائمة منسدلة للمساحات الضيقة (اختياري)
        self.more_menu = QMenu(self)
        self.more_btn = QToolButton()
        self.more_btn.setIcon(qta.icon('fa5s.ellipsis-h'))
        self.more_btn.setIconSize(QSize(28, 28))
        self.more_btn.setMenu(self.more_menu)
        self.more_btn.setPopupMode(QToolButton.InstantPopup)
        self.more_btn.setVisible(False)
        layout.addWidget(self.more_btn)

    def add_button(self, name, icon_name, callback, badge_count=0):
        btn = TopBarButton(name, icon_name, badge_count, self)
        btn.set_text(name)
        btn.clicked.connect(callback)
        self.buttons_container.addWidget(btn)
        self.buttons[name] = btn
        # إضافة نفس الزر إلى القائمة المنسدلة (للمساحات الضيقة)
        action = self.more_menu.addAction(qta.icon(f'fa5s.{icon_name}'), name)
        action.triggered.connect(callback)
        return btn

    def set_badge(self, name, count):
        if name in self.buttons:
            self.buttons[name].set_badge(count)

    def toggle_sidebar(self):
        # إشارة لتوسيع شريط جانبي (إذا أردت الاحتفاظ به كخيار مخفي)
        self.parent().toggle_sidebar() if hasattr(self.parent(), 'toggle_sidebar') else None
        # يمكن إخفاء زر القائمة إذا لم يكن هناك شريط جانبي

    def setup_responsive_behavior(self):
        """ إخفاء النصوص تلقائياً عندما تصغر النافذة """
        def check_width():
            if not self.parent():
                return
            width = self.parent().width()
            icon_only = width < 1000
            for btn in self.buttons.values():
                btn.set_icon_only(icon_only)
            # إظهار زر "المزيد" إذا كانت المساحة ضيقة جداً
            total_btns_width = sum(btn.width() for btn in self.buttons.values())
            self.more_btn.setVisible(width < 800 and len(self.buttons) > 4)
        # ربط الحدث بتغيير حجم النافذة الأم
        parent = self.parent()
        if parent:
            parent.resizeEvent = lambda event: check_width()
            QTimer.singleShot(100, check_width)

    def apply_styles(self):
        self.setStyleSheet("""
            #ModernTopBar {
                background-color: #1e293b;
                border-bottom: 2px solid #0f172a;
            }
            #TopBarButton {
                background-color: transparent;
                border: none;
                border-radius: 8px;
                color: #cbd5e1;
                font-weight: bold;
                font-size: 12px;
                padding: 0 6px;
            }
            #TopBarButton:hover {
                background-color: #334155;
            }
            #TopBarButton:pressed {
                background-color: #3b82f6;
            }
            QToolButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }
            QToolButton:hover {
                background-color: #334155;
            }
        """)
