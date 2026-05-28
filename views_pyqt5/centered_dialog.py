# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QDialog, QApplication
from PyQt5.QtCore import Qt

class CenteredDialog(QDialog):
    """حوار يتم تمركزه تلقائياً بالنسبة للنافذة الأم، ويتابع تحركها"""
    def __init__(self, parent=None, flags=Qt.WindowFlags()):
        super().__init__(parent, flags)
        self.setModal(True)
        self._parent_moved_connected = False

    def showEvent(self, event):
        self.center()
        # ربط إشارات النافذة الأم لتحديث التمركز عند تحركها
        if self.parent() and not self._parent_moved_connected:
            self.parent().installEventFilter(self)
            self._parent_moved_connected = True
        super().showEvent(event)

    def eventFilter(self, obj, event):
        if obj == self.parent() and event.type() in (event.Move, event.Resize):
            self.center()
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        # إزالة مرشح الأحداث عند الإغلاق
        if self.parent() and self._parent_moved_connected:
            self.parent().removeEventFilter(self)
            self._parent_moved_connected = False
        super().closeEvent(event)

    def center(self):
        """إعادة حساب المركز بناءً على النافذة الأم أو الشاشة"""
        parent = self.parent()
        if parent:
            parent_geometry = parent.geometry()
            dialog_geometry = self.geometry()
            x = parent_geometry.x() + (parent_geometry.width() - dialog_geometry.width()) // 2
            y = parent_geometry.y() + (parent_geometry.height() - dialog_geometry.height()) // 2
            self.move(x, y)
        else:
            screen = QApplication.primaryScreen().geometry()
            dialog_geometry = self.geometry()
            x = (screen.width() - dialog_geometry.width()) // 2
            y = (screen.height() - dialog_geometry.height()) // 2
            self.move(x, y)
