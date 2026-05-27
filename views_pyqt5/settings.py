# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox, QPushButton,
                             QGroupBox, QFileDialog, QMessageBox, QCheckBox, QComboBox)
from PyQt5.QtCore import Qt, QSettings
from database import db
from config import get_currency_settings, save_currency_settings
from utils_pyqt5 import show_toast
import os, sys

class SettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8,8,8,8)
        self.settings = QSettings("Alrajhi", "Accounting")

        group_currency = QGroupBox("إعدادات العملة")
        form = QFormLayout(group_currency)
        self.symbol_edit = QLineEdit()
        self.decimals_spin = QSpinBox()
        self.decimals_spin.setRange(0,4)
        settings = get_currency_settings()
        self.symbol_edit.setText(settings.get('symbol','$'))
        self.decimals_spin.setValue(settings.get('decimals',2))
        form.addRow("رمز العملة:", self.symbol_edit)
        form.addRow("الخانات العشرية:", self.decimals_spin)
        save_btn = QPushButton("حفظ الإعدادات")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self.save_settings)
        form.addRow(save_btn)
        layout.addWidget(group_currency)

        group_printer = QGroupBox("إعدادات الطابعة الحرارية")
        printer_form = QFormLayout(group_printer)
        self.printer_port = QLineEdit()
        self.printer_port.setPlaceholderText("مثال: COM3 أو /dev/usb/lp0")
        self.printer_port.setText(self.settings.value("printer_port", "COM1"))
        printer_form.addRow("منفذ الطابعة:", self.printer_port)
        self.printer_copies = QSpinBox()
        self.printer_copies.setRange(1,5)
        self.printer_copies.setValue(self.settings.value("printer_copies", 1, type=int))
        printer_form.addRow("عدد النسخ:", self.printer_copies)
        save_printer_btn = QPushButton("حفظ إعدادات الطابعة")
        save_printer_btn.clicked.connect(self.save_printer_settings)
        printer_form.addRow(save_printer_btn)
        layout.addWidget(group_printer)

        group_ui = QGroupBox("إعدادات الواجهة")
        ui_form = QFormLayout(group_ui)
        self.touch_mode = QCheckBox("تفعيل الوضع اللمسي (أزرار أكبر)")
        self.touch_mode.setChecked(self.settings.value("touch_mode", False, type=bool))
        self.touch_mode.toggled.connect(self.toggle_touch_mode)
        ui_form.addRow(self.touch_mode)
        self.auto_theme = QCheckBox("الثيم التلقائي حسب وقت النظام")
        self.auto_theme.setChecked(self.settings.value("auto_theme", False, type=bool))
        ui_form.addRow(self.auto_theme)
        layout.addWidget(group_ui)

        group_backup = QGroupBox("النسخ الاحتياطي والاستعادة")
        vbox = QVBoxLayout(group_backup)
        export_btn = QPushButton("📤 تصدير البيانات (JSON)")
        export_btn.clicked.connect(self.export_db)
        import_btn = QPushButton("📥 استيراد بيانات (JSON)")
        import_btn.clicked.connect(self.import_db)
        reset_btn = QPushButton("⚠️ إعادة تعيين قاعدة البيانات")
        reset_btn.setObjectName("danger")
        reset_btn.clicked.connect(self.reset_db)
        logout_btn = QPushButton("🚪 تسجيل الخروج")
        logout_btn.setObjectName("danger")
        logout_btn.clicked.connect(self.logout)
        vbox.addWidget(export_btn)
        vbox.addWidget(import_btn)
        vbox.addWidget(reset_btn)
        vbox.addWidget(logout_btn)
        layout.addWidget(group_backup)
        layout.addStretch()

    def save_settings(self):
        save_currency_settings({
            'symbol': self.symbol_edit.text().strip(),
            'decimals': self.decimals_spin.value(),
            'number_format': 'western'
        })
        show_toast("تم حفظ إعدادات العملة", "success", self)

    def save_printer_settings(self):
        self.settings.setValue("printer_port", self.printer_port.text())
        self.settings.setValue("printer_copies", self.printer_copies.value())
        show_toast("تم حفظ إعدادات الطابعة", "success", self)

    def toggle_touch_mode(self, checked):
        self.settings.setValue("touch_mode", checked)
        show_toast("سيتم تطبيق الوضع اللمسي بعد إعادة التشغيل", "info", self)

    def export_db(self):
        try:
            data = db.export_full_database()
            filename, _ = QFileDialog.getSaveFileName(self, "حفظ النسخة الاحتياطية", "alrajhi_backup.json", "JSON (*.json)")
            if filename:
                with open(filename, 'wb') as f:
                    f.write(data)
                show_toast("تم التصدير", "success", self)
        except Exception as e:
            show_toast(f"خطأ في التصدير: {str(e)}", "error", self)

    def import_db(self):
        filename, _ = QFileDialog.getOpenFileName(self, "اختر ملف النسخة الاحتياطية", "", "JSON (*.json)")
        if filename:
            with open(filename, 'rb') as f:
                data = f.read()
            reply = QMessageBox.question(self, "تأكيد الاستيراد", "سيتم استبدال جميع البيانات الحالية. هل أنت متأكد?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                try:
                    db.import_full_database(data)
                    show_toast("تم الاستيراد، أعد تشغيل البرنامج", "success", self)
                except Exception as e:
                    show_toast(str(e), "error", self)

    def reset_db(self):
        global db
        reply = QMessageBox.warning(self, "إعادة تعيين قاعدة البيانات", "تحذير: سيتم حذف جميع البيانات نهائياً! هل أنت متأكد?",
                                    QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                from database import DB_PATH
                db.close()
                if os.path.exists(DB_PATH):
                    os.remove(DB_PATH)
                from database import Database
                db = Database()
                show_toast("تم إعادة التعيين", "success", self)
                self.parent().switch_page('dashboard')
            except Exception as e:
                show_toast(str(e), "error", self)

    def logout(self):
        reply = QMessageBox.question(self, "تسجيل الخروج", "هل تريد تسجيل الخروج؟", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            from database import clear_current_user
            clear_current_user()
            os.execl(sys.executable, sys.executable, *sys.argv)
