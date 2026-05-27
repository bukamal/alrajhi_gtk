# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, QFrame,
                             QScrollArea, QHBoxLayout, QSizePolicy)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal, QSize
from PyQt5.QtGui import QFont
import qtawesome as qta

# ================================
# زر القائمة الجانبية (مع أيقونة ونص)
# ================================
class SidebarButton(QPushButton):
    def __init__(self, text, icon_name, badge_count=0, parent=None):
        super().__init__(parent)
        self.setObjectName("SidebarButton")
        self.setFixedHeight(45)
        self.setCursor(Qt.PointingHandCursor)
        self.setIcon(qta.icon(f'fa5s.{icon_name}'))
        self.setIconSize(QSize(22, 22))
        self.setText(text)
        self.setToolTip(text)  # يظهر عند الطي
        self.setLayoutDirection(Qt.RightToLeft)  # RTL
        self.setFont(QFont("Tajawal", 10, QFont.Bold))

        # Badge (لإظهار عدد التنبيهات)
        self.badge = QLabel(str(badge_count) if badge_count > 0 else "")
        self.badge.setStyleSheet("""
            background-color: #ef4444;
            color: white;
            border-radius: 10px;
            padding: 2px 6px;
            font-size: 10px;
            font-weight: bold;
            margin-right: 8px;
        """)
        self.badge.setVisible(badge_count > 0)

        # تخطيط الزر (نص + مرونة + شارة)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.addWidget(self.badge)
        layout.addStretch()

        self.original_text = text

    def set_expanded(self, expanded):
        if expanded:
            self.setText(self.original_text)
            self.setToolTip("")
        else:
            self.setText("")
            self.setToolTip(self.original_text)
        # إظهار الشارة فقط إذا كانت موسعة وقيمتها > 0
        if expanded and self.badge.text().isdigit() and int(self.badge.text()) > 0:
            self.badge.setVisible(True)
        else:
            self.badge.setVisible(False)

    def set_badge(self, count):
        self.badge.setText(str(count) if count > 0 else "")
        if hasattr(self, 'parent_sidebar') and self.parent_sidebar.expanded:
            self.badge.setVisible(count > 0)

# ================================
# قسم قابل للطي (Collapsible Section)
# ================================
class CollapsibleSection(QWidget):
    def __init__(self, title, icon_name, parent=None):
        super().__init__(parent)
        self.setObjectName("CollapsibleSection")
        self.toggle_btn = QPushButton(title)
        self.toggle_btn.setIcon(qta.icon(f'fa5s.{icon_name}'))
        self.toggle_btn.setIconSize(QSize(22, 22))
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(True)
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                font-weight: bold;
                padding: 10px;
                border: none;
                background-color: #334155;
                color: #cbd5e1;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #475569; }
        """)
        self.toggle_btn.setLayoutDirection(Qt.RightToLeft)
        self.toggle_btn.setFont(QFont("Tajawal", 10, QFont.Bold))

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(20, 0, 0, 0)
        self.content_layout.setSpacing(2)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.toggle_btn)
        main_layout.addWidget(self.content)

        self.toggle_btn.toggled.connect(self.content.setVisible)

    def addWidget(self, widget):
        self.content_layout.addWidget(widget)

# ================================
# القائمة الجانبية الرئيسية (مودرن)
# ================================
class ModernSidebar(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ModernSidebar")
        self.expanded_width = 280      # العرض عند التوسيع
        self.collapsed_width = 70      # العرض عند الطي (كافٍ للأيقونة فقط)
        self.setMinimumWidth(self.collapsed_width)
        self.setMaximumWidth(self.expanded_width)
        self.resize(self.expanded_width, self.height())
        self.expanded = True
        self.init_ui()
        self.apply_styles()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ========== رأس القائمة ==========
        self.header = QFrame()
        self.header.setFixedHeight(70)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(10, 0, 10, 0)

        # زر القائمة (لطي/توسيع)
        self.menu_btn = QPushButton()
        self.menu_btn.setIcon(qta.icon('fa5s.bars'))
        self.menu_btn.setIconSize(QSize(24, 24))
        self.menu_btn.setFixedSize(40, 40)
        self.menu_btn.setCursor(Qt.PointingHandCursor)
        self.menu_btn.clicked.connect(self.toggle_sidebar)

        # شعار التطبيق (يظهر فقط عند التوسيع)
        self.logo_label = QLabel("الراجحي")
        self.logo_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.logo_label.setAlignment(Qt.AlignRight)

        header_layout.addWidget(self.menu_btn)
        header_layout.addWidget(self.logo_label)
        layout.addWidget(self.header)

        # ========== منطقة الأزرار والأقسام ==========
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(6)
        self.content_layout.setContentsMargins(8, 8, 8, 8)
        self.content_layout.addStretch()

        self.scroll.setWidget(self.content_widget)
        layout.addWidget(self.scroll)

        # تخزين الأقسام والأزرار للرجوع إليها
        self.sections = {}
        self.buttons = {}

    # إضافة قسم جديد (Collapsible Section)
    def add_section(self, name, icon_name):
        section = CollapsibleSection(name, icon_name, self)
        self.content_layout.insertWidget(self.content_layout.count() - 1, section)
        self.sections[name] = section
        return section

    # إضافة زر داخل القسم أو في القائمة الرئيسية
    def add_button(self, name, icon_name, callback, section=None, badge_count=0):
        btn = SidebarButton(name, icon_name, badge_count, self)
        btn.parent_sidebar = self
        btn.clicked.connect(callback)
        if section and section in self.sections:
            self.sections[section].addWidget(btn)
        else:
            self.content_layout.insertWidget(self.content_layout.count() - 1, btn)
        self.buttons[name] = btn
        return btn

    # تحديث الشارة لزر معين
    def set_badge(self, name, count):
        if name in self.buttons:
            self.buttons[name].set_badge(count)

    # طي / توسيع الشريط الجانبي
    def toggle_sidebar(self):
        self.expanded = not self.expanded
        target_width = self.expanded_width if self.expanded else self.collapsed_width

        # حركة انزلاقية مع تغيير العرض
        self.animation = QPropertyAnimation(self, b"maximumWidth")
        self.animation.setDuration(300)
        self.animation.setStartValue(self.width())
        self.animation.setEndValue(target_width)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation.start()

        # تحديث حالة كل زر (إظهار/إخفاء النص)
        for btn in self.buttons.values():
            btn.set_expanded(self.expanded)

        # تحديث حالة الأقسام
        for section in self.sections.values():
            section.toggle_btn.setVisible(self.expanded)
            if not self.expanded:
                section.content.setVisible(False)
            else:
                section.content.setVisible(section.toggle_btn.isChecked())

        # إظهار/إخفاء شعار التطبيق
        self.logo_label.setVisible(self.expanded)

        # إشارة تغيير الحالة
        self.toggled.emit(self.expanded)

    # تطبيق الأنماط الأساسية (يمكن تخصيصها عبر الثيم)
    def apply_styles(self):
        self.setStyleSheet("""
            #ModernSidebar {
                background-color: #1e293b;
                border-right: 2px solid #0f172a;
            }
            #SidebarButton {
                background-color: transparent;
                border: none;
                text-align: right;
                color: #cbd5e1;
                font-weight: bold;
                padding: 0px;
            }
            #SidebarButton:hover {
                background-color: #334155;
            }
            #SidebarButton:pressed {
                background-color: #3b82f6;
            }
            QPushButton#menu_btn {
                background-color: transparent;
                border: none;
            }
            QPushButton#menu_btn:hover {
                background-color: #334155;
            }
        """)
