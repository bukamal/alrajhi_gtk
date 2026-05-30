# views_pyqt5/centered_dialog.py
# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QDialog, QApplication, QMessageBox
from PyQt5.QtCore import Qt, QEvent

class CenteredDialog(QDialog):
    """حوار يتم تمركزه تلقائياً بالنسبة للنافذة العليا، ويتابع تحركها"""
    def __init__(self, parent=None, flags=Qt.WindowFlags()):
        super().__init__(parent, flags)
        self.setModal(True)
        self._parent_moved_connected = False
        # العثور على النافذة العليا (main window) بدلاً من الوالد المباشر
        self._top_window = parent.window() if parent else None
        if self.size().width() == 100 and self.size().height() == 30:
            self.resize(400, 300)

    def showEvent(self, event):
        self.center()
        # تتبع حركة النافذة العليا فقط
        if self._top_window and not self._parent_moved_connected:
            self._top_window.installEventFilter(self)
            self._parent_moved_connected = True
        super().showEvent(event)

    def eventFilter(self, obj, event):
        if obj == self._top_window and event.type() in (QEvent.Move, QEvent.Resize):
            self.center()
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        if self._top_window and self._parent_moved_connected:
            self._top_window.removeEventFilter(self)
            self._parent_moved_connected = False
        super().closeEvent(event)

    def center(self):
        """إعادة حساب المركز بناءً على النافذة العليا أو الشاشة"""
        if self._top_window and self._top_window.isVisible():
            parent_geometry = self._top_window.geometry()
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

def show_centered_messagebox(parent, title, text, icon=QMessageBox.Information, buttons=QMessageBox.Ok):
    """عرض رسالة منبثقة متمركزة بالنسبة للنافذة العليا"""
    # الحصول على النافذة العليا إذا أمكن
    top_window = parent.window() if parent else None
    msg = QMessageBox(top_window if top_window else parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setIcon(icon)
    msg.setStandardButtons(buttons)
    msg.setLayoutDirection(Qt.RightToLeft)
    msg.show()
    if top_window:
        parent_geom = top_window.geometry()
        msg_geom = msg.geometry()
        x = parent_geom.x() + (parent_geom.width() - msg_geom.width()) // 2
        y = parent_geom.y() + (parent_geom.height() - msg_geom.height()) // 2
        msg.move(x, y)
    return msg.exec()
