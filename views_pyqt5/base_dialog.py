# views_pyqt5/base_dialog.py
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import QDialog, QHBoxLayout, QPushButton, QVBoxLayout, QFormLayout, QWidget
from PyQt5.QtCore import Qt
from views_pyqt5.centered_dialog import CenteredDialog, show_centered_messagebox
from utils_pyqt5 import show_toast

class BaseDialog(CenteredDialog):
    """كلاس أساسي لجميع حوارات الإضافة/التعديل"""
    
    def __init__(self, parent=None, title="", is_edit=False):
        super().__init__(parent)
        self.is_edit = is_edit
        self.setWindowTitle(title)
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(400, 300)
        
        self.main_layout = QVBoxLayout(self)
        self.form_widget = QWidget()
        self.form_layout = QFormLayout(self.form_widget)
        self.main_layout.addWidget(self.form_widget)
        
        self.btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("حفظ")
        self.save_btn.setObjectName("primary")
        self.cancel_btn = QPushButton("إلغاء")
        self.btn_layout.addWidget(self.save_btn)
        self.btn_layout.addWidget(self.cancel_btn)
        self.main_layout.addLayout(self.btn_layout)
        
        self.save_btn.clicked.connect(self.on_save)
        self.cancel_btn.clicked.connect(self.reject)
    
    def on_save(self):
        """يتم تجاوزها في الكلاس الفرعي"""
        raise NotImplementedError
