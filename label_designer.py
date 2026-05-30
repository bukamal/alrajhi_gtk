# -*- coding: utf-8 -*-
"""
"""

import os
import json
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QFileDialog, QMessageBox, QLabel, QComboBox
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QFont
from views_pyqt5.centered_dialog import CenteredDialog
from utils_pyqt5 import show_toast

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'data', 'barcode_templates')
os.makedirs(TEMPLATES_DIR, exist_ok=True)

class LabelDesigner(CenteredDialog):
    """محرر قوالب الملصقات"""
    
    DEFAULT_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
    body {
        font-family: Arial, sans-serif;
        text-align: center;
        width: 60mm;
        margin: 0 auto;
        padding: 5mm;
    }
    .company-name {
        font-weight: bold;
        font-size: 12pt;
        margin-bottom: 3pt;
    }
    .item-name {
        font-weight: bold;
        font-size: 11pt;
        margin-bottom: 5pt;
    }
    .barcode-img {
        width: 50mm;
        height: auto;
        margin: 5pt 0;
    }
    .barcode-text {
        font-size: 9pt;
        font-family: monospace;
        margin-bottom: 3pt;
    }
    .price {
        font-size: 10pt;
        font-weight: bold;
        color: #d32f2f;
    }
</style>
</head>
<body>
    <div class="company-name">{{company_name}}</div>
    <div class="item-name">{{item_name}}</div>
    <img class="barcode-img" src="data:image/png;base64,{{barcode_image}}" alt="barcode">
    <div class="barcode-text">{{barcode}}</div>
    <div class="price">{{price_label}} {{price}}</div>
</body>
</html>"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("محرر قوالب الباركود")
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(700, 600)
        self.settings = QSettings("Alrajhi", "Accounting")
        self.current_template_name = self.settings.value("barcode_template", "default")
        
        layout = QVBoxLayout(self)
        
        # شريط القوالب
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("القالب:"))
        self.template_combo = QComboBox()
        self.template_combo.currentTextChanged.connect(self.load_template_by_name)
        toolbar.addWidget(self.template_combo)
        self.save_btn = QPushButton("💾 حفظ")
        self.save_btn.clicked.connect(self.save_current_template)
        toolbar.addWidget(self.save_btn)
        self.save_as_btn = QPushButton("📄 حفظ باسم")
        self.save_as_btn.clicked.connect(self.save_template_as)
        toolbar.addWidget(self.save_as_btn)
        self.delete_btn = QPushButton("🗑 حذف")
        self.delete_btn.clicked.connect(self.delete_current_template)
        toolbar.addWidget(self.delete_btn)
        layout.addLayout(toolbar)
        
        # محرر HTML
        self.editor = QTextEdit()
        self.editor.setFont(QFont("Courier New", 10))
        layout.addWidget(self.editor)
        
        # أزرار التحكم
        btn_layout = QHBoxLayout()
        preview_btn = QPushButton("👁️ معاينة")
        preview_btn.clicked.connect(self.preview_template)
        btn_layout.addWidget(preview_btn)
        reset_btn = QPushButton("🔄 إعادة ضبط")
        reset_btn.clicked.connect(self.reset_to_default)
        btn_layout.addWidget(reset_btn)
        close_btn = QPushButton("إغلاق")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
        
        self.load_templates_list()
        self.load_template_by_name(self.current_template_name)
    
    def load_templates_list(self):
        """تحميل قائمة القوالب المتاحة"""
        self.template_combo.clear()
        templates = ['default']
        for f in os.listdir(TEMPLATES_DIR):
            if f.endswith('.html') and f != 'default.html':
                templates.append(f[:-5])
        for t in templates:
            self.template_combo.addItem(t)
        idx = self.template_combo.findText(self.current_template_name)
        if idx >= 0:
            self.template_combo.setCurrentIndex(idx)
    
    def load_template_by_name(self, name):
        """تحميل قالب باسم معين"""
        self.current_template_name = name
        if name == 'default':
            content = self.DEFAULT_TEMPLATE
        else:
            path = os.path.join(TEMPLATES_DIR, f"{name}.html")
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
            else:
                content = self.DEFAULT_TEMPLATE
        self.editor.setPlainText(content)
    
    def save_current_template(self):
        """حفظ القالب الحالي (نفس الاسم)"""
        if self.current_template_name == 'default':
            QMessageBox.warning(self, "تنبيه", "لا يمكن تعديل القالب الافتراضي. استخدم 'حفظ باسم'.")
            return
        self._save_template(self.current_template_name)
    
    def save_template_as(self):
        """حفظ القالب الحالي باسم جديد"""
        name, ok = QInputDialog.getText(self, "حفظ القالب", "اسم القالب:")
        if ok and name.strip():
            name = name.strip().replace(' ', '_')
            self._save_template(name)
            self.load_templates_list()
            idx = self.template_combo.findText(name)
            if idx >= 0:
                self.template_combo.setCurrentIndex(idx)
    
    def _save_template(self, name):
        path = os.path.join(TEMPLATES_DIR, f"{name}.html")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(self.editor.toPlainText())
        self.settings.setValue("barcode_template", name)
        show_toast(f"تم حفظ القالب '{name}'", "success", self)
    
    def delete_current_template(self):
        if self.current_template_name == 'default':
            QMessageBox.warning(self, "تنبيه", "لا يمكن حذف القالب الافتراضي.")
            return
        reply = QMessageBox.question(self, "تأكيد الحذف", f"هل تريد حذف القالب '{self.current_template_name}'؟",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            path = os.path.join(TEMPLATES_DIR, f"{self.current_template_name}.html")
            if os.path.exists(path):
                os.remove(path)
            self.load_templates_list()
            self.template_combo.setCurrentText('default')
            show_toast("تم حذف القالب", "success", self)
    
    def reset_to_default(self):
        self.editor.setPlainText(self.DEFAULT_TEMPLATE)
    
    def preview_template(self):
        """فتح نافذة معاينة للقالب (بيانات وهمية)"""
        from PyQt5.QtWidgets import QTextBrowser
        preview_dialog = CenteredDialog(self)
        preview_dialog.setWindowTitle("معاينة القالب")
        preview_dialog.resize(400, 500)
        layout = QVBoxLayout(preview_dialog)
        browser = QTextBrowser()
        # استخدام بيانات وهمية للمعاينة
        html = self.editor.toPlainText()
        # ملاحظة: لا يمكن عرض الصورة في المعاينة لأنها بيانات وهمية، لكن النص يظهر
        browser.setHtml(html.replace("{{company_name}}", "الراجحي")
                              .replace("{{item_name}}", "مادة تجريبية")
                              .replace("{{barcode_image}}", "")
                              .replace("{{barcode}}", "123456789012")
                              .replace("{{price_label}}", "السعر:")
                              .replace("{{price}}", "100.00"))
        layout.addWidget(browser)
        close_btn = QPushButton("إغلاق")
        close_btn.clicked.connect(preview_dialog.accept)
        layout.addWidget(close_btn)
        preview_dialog.exec()

# دالة مساعدة للحصول على القالب الحالي
def get_current_template() -> str:
    settings = QSettings("Alrajhi", "Accounting")
    template_name = settings.value("barcode_template", "default")
    if template_name == 'default':
        return LabelDesigner.DEFAULT_TEMPLATE
    path = os.path.join(TEMPLATES_DIR, f"{template_name}.html")
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    return LabelDesigner.DEFAULT_TEMPLATE

from PyQt5.QtWidgets import QInputDialog
