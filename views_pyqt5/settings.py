# views_pyqt5/settings.py
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton,
                             QGroupBox, QFileDialog, QMessageBox, QCheckBox, QComboBox, QLabel,
                             QHBoxLayout, QDoubleSpinBox, QTabWidget, QTableView, QHeaderView,
                             QDialog, QDialogButtonBox, QSpinBox, QApplication)
from PyQt5.QtCore import Qt, QSettings, QAbstractTableModel, QModelIndex
from database import exchange_rate_dao, reporting_dao
from database.connection import DatabaseConnection
from config import get_currency_settings, save_currency_settings, get_currency_symbol, refresh_currency_settings
from utils_pyqt5 import show_toast
from worker_threads import ExportWorker, ImportWorker
from views_pyqt5.centered_dialog import CenteredDialog, show_centered_messagebox
import os, sys

class ExchangeRatesModel(QAbstractTableModel):
    def __init__(self, data, headers):
        super().__init__()
        self._data = data
        self._headers = headers
    def rowCount(self, parent=QModelIndex()): return len(self._data)
    def columnCount(self, parent=QModelIndex()): return len(self._headers)
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid(): return None
        if role == Qt.DisplayRole:
            return str(self._data[index.row()][index.column()])
        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter
        return None
    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]
        return None
    def update_data(self, new_data):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()

class SettingsWidget(QWidget):
    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8,8,8,8)
        self.settings = QSettings("Alrajhi", "Accounting")

        tabs = QTabWidget()
        layout.addWidget(tabs)

        # تبويب العملات
        currency_tab = QWidget()
        currency_layout = QVBoxLayout(currency_tab)
        form = QFormLayout()
        self.base_currency_combo = QComboBox()
        self.display_currency_combo = QComboBox()
        self.symbol_pos_combo = QComboBox()
        self.symbol_pos_combo.addItems(["بعد الرقم (مثال: 100 $)", "قبل الرقم (مثال: $ 100)"])
        self.use_conversion_check = QCheckBox("تحويل القيم إلى العملة المعروضة تلقائياً")
        form.addRow("العملة الأساسية (للتخزين):", self.base_currency_combo)
        form.addRow("العملة المعروضة:", self.display_currency_combo)
        form.addRow(self.use_conversion_check)
        form.addRow("موضع رمز العملة:", self.symbol_pos_combo)
        currency_layout.addLayout(form)

        rates_group = QGroupBox("أسعار الصرف")
        rates_layout = QVBoxLayout(rates_group)
        self.rates_table = QTableView()
        self.rates_table.setSelectionBehavior(QTableView.SelectRows)
        self.rates_table.setAlternatingRowColors(True)
        rates_layout.addWidget(self.rates_table)
        btn_layout = QHBoxLayout()
        add_rate_btn = QPushButton("➕ إضافة عملة")
        add_rate_btn.clicked.connect(self.add_currency)
        edit_rate_btn = QPushButton("✏️ تعديل السعر")
        edit_rate_btn.clicked.connect(self.edit_rate)
        delete_rate_btn = QPushButton("🗑 حذف عملة")
        delete_rate_btn.clicked.connect(self.delete_currency)
        refresh_rates_btn = QPushButton("🔄 تحديث من الإنترنت")
        refresh_rates_btn.clicked.connect(self.fetch_online_rates)
        btn_layout.addWidget(add_rate_btn)
        btn_layout.addWidget(edit_rate_btn)
        btn_layout.addWidget(delete_rate_btn)
        btn_layout.addWidget(refresh_rates_btn)
        rates_layout.addLayout(btn_layout)
        currency_layout.addWidget(rates_group)
        save_currency_btn = QPushButton("حفظ إعدادات العملة")
        save_currency_btn.setObjectName("primary")
        save_currency_btn.clicked.connect(self.save_currency_settings)
        currency_layout.addWidget(save_currency_btn)
        currency_layout.addStretch()
        tabs.addTab(currency_tab, "💰 العملات")

        # تبويب الطابعة
        printer_tab = QWidget()
        printer_layout = QVBoxLayout(printer_tab)
        printer_form = QFormLayout()
        self.printer_port = QLineEdit()
        self.printer_port.setPlaceholderText("مثال: COM3 أو /dev/usb/lp0")
        self.printer_port.setText(self.settings.value("printer_port", "COM1"))
        self.printer_copies = QSpinBox()
        self.printer_copies.setRange(1,5)
        self.printer_copies.setValue(self.settings.value("printer_copies", 1, type=int))
        printer_form.addRow("منفذ الطابعة:", self.printer_port)
        printer_form.addRow("عدد النسخ:", self.printer_copies)

        self.printer_combo = QComboBox()
        printer_form.addRow("الطابعة الافتراضية:", self.printer_combo)

        save_printer_btn = QPushButton("حفظ إعدادات الطابعة")
        save_printer_btn.clicked.connect(self.save_printer_settings)
        printer_form.addRow(save_printer_btn)
        printer_layout.addLayout(printer_form)
        printer_layout.addStretch()
        tabs.addTab(printer_tab, "🖨️ الطابعة")

        # تبويب الواجهة
        ui_tab = QWidget()
        ui_layout = QVBoxLayout(ui_tab)
        ui_form = QFormLayout()
        self.touch_mode = QCheckBox("تفعيل الوضع اللمسي (أزرار أكبر)")
        self.touch_mode.setChecked(self.settings.value("touch_mode", False, type=bool))
        self.touch_mode.toggled.connect(self.toggle_touch_mode)
        self.auto_theme = QCheckBox("الثيم التلقائي حسب وقت النظام")
        self.auto_theme.setChecked(self.settings.value("auto_theme", False, type=bool))
        ui_form.addRow(self.touch_mode)
        ui_form.addRow(self.auto_theme)
        ui_layout.addLayout(ui_form)
        ui_layout.addStretch()
        tabs.addTab(ui_tab, "🎨 الواجهة")

        # تبويب النسخ الاحتياطي
        backup_tab = QWidget()
        backup_layout = QVBoxLayout(backup_tab)
        self.export_btn = QPushButton("📤 تصدير البيانات (JSON)")
        self.export_btn.clicked.connect(self.export_db)
        self.import_btn = QPushButton("📥 استيراد بيانات (JSON)")
        self.import_btn.clicked.connect(self.import_db)
        self.reset_btn = QPushButton("⚠️ إعادة تعيين قاعدة البيانات")
        self.reset_btn.setObjectName("danger")
        self.reset_btn.clicked.connect(self.reset_db)
        self.logout_btn = QPushButton("🚪 تسجيل الخروج")
        self.logout_btn.setObjectName("danger")
        self.logout_btn.clicked.connect(self.logout)
        backup_layout.addWidget(self.export_btn)
        backup_layout.addWidget(self.import_btn)
        backup_layout.addWidget(self.reset_btn)
        backup_layout.addWidget(self.logout_btn)

        backup_settings_group = QGroupBox("النسخ الاحتياطي التلقائي")
        backup_settings_layout = QFormLayout(backup_settings_group)
        self.backup_interval = QSpinBox()
        self.backup_interval.setRange(1, 30)
        self.backup_interval.setValue(self.settings.value("backup_interval", 1, type=int))
        self.backup_interval.setSuffix(" يوم")
        backup_settings_layout.addRow("النسخ الاحتياطي التلقائي كل:", self.backup_interval)
        save_backup_btn = QPushButton("حفظ إعدادات النسخ الاحتياطي")
        save_backup_btn.clicked.connect(self.save_backup_settings)
        backup_settings_layout.addRow(save_backup_btn)
        backup_layout.addWidget(backup_settings_group)

        backup_layout.addStretch()
        tabs.addTab(backup_tab, "💾 نسخ احتياطي")

        # تبويب قوالب الباركود
        label_tab = QWidget()
        label_layout = QVBoxLayout(label_tab)
        edit_template_btn = QPushButton("🎨 تحرير القوالب")
        edit_template_btn.clicked.connect(self.open_label_designer)
        label_layout.addWidget(edit_template_btn)
        label_layout.addStretch()
        tabs.addTab(label_tab, "🏷️ قوالب الباركود")

        self.load_currency_settings()
        self.load_exchange_rates()
        self.load_printer_settings()

    def load_currency_settings(self):
        settings = get_currency_settings()
        rates = exchange_rate_dao.get_all()
        currencies = [r['currency_code'] for r in rates]
        self.base_currency_combo.clear()
        self.display_currency_combo.clear()
        for c in currencies:
            self.base_currency_combo.addItem(f"{c} - {get_currency_symbol(c)}", c)
            self.display_currency_combo.addItem(f"{c} - {get_currency_symbol(c)}", c)
        idx = self.base_currency_combo.findData(settings.get('base_currency', 'USD'))
        if idx >= 0: self.base_currency_combo.setCurrentIndex(idx)
        idx = self.display_currency_combo.findData(settings.get('display_currency', 'USD'))
        if idx >= 0: self.display_currency_combo.setCurrentIndex(idx)
        self.use_conversion_check.setChecked(settings.get('use_conversion', False))
        self.symbol_pos_combo.setCurrentIndex(0 if settings.get('symbol_position', 'after') == 'after' else 1)

    def load_exchange_rates(self):
        rates = exchange_rate_dao.get_all()
        data = []
        for r in rates:
            rate_display = 1.0 / float(r['rate_to_usd']) if r['rate_to_usd'] != 0 else 0
            data.append([r['currency_code'], rate_display, r['updated_at'][:10] if r['updated_at'] else ''])
        headers = ["العملة", "السعر (1 دولار = ?)", "آخر تحديث"]
        self.rates_model = ExchangeRatesModel(data, headers)
        self.rates_table.setModel(self.rates_model)
        self.rates_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.rates_table.setColumnHidden(0, False)

    def save_currency_settings(self):
        base_curr = self.base_currency_combo.currentData()
        display_curr = self.display_currency_combo.currentData()
        use_conversion = self.use_conversion_check.isChecked()
        symbol_position = 'after' if self.symbol_pos_combo.currentIndex() == 0 else 'before'
        settings = {
            'base_currency': base_curr,
            'display_currency': display_curr,
            'use_conversion': use_conversion,
            'symbol_position': symbol_position
        }
        save_currency_settings(settings)
        show_toast("تم حفظ إعدادات العملة", "success", self)

    def add_currency(self):
        dialog = CenteredDialog(self)
        dialog.setWindowTitle("إضافة عملة جديدة")
        dialog.setLayoutDirection(Qt.RightToLeft)
        layout = QFormLayout(dialog)
        code_edit = QLineEdit()
        code_edit.setPlaceholderText("مثال: IQD")
        rate_edit = QDoubleSpinBox()
        rate_edit.setRange(0.000001, 1000000)
        rate_edit.setDecimals(6)
        rate_edit.setValue(1.0)
        layout.addRow("رمز العملة:", code_edit)
        layout.addRow("سعر الصرف (1 دولار = ?):", rate_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        if dialog.exec():
            code = code_edit.text().strip().upper()
            rate = rate_edit.value()
            if not code:
                show_centered_messagebox(dialog, "خطأ", "رمز العملة مطلوب", QMessageBox.Warning)
                return
            try:
                exchange_rate_dao.add(code, 1.0 / rate if rate != 0 else 0)
                self.load_exchange_rates()
                self.load_currency_settings()
                show_toast("تمت إضافة العملة", "success", self)
            except Exception as e:
                show_centered_messagebox(dialog, "خطأ", str(e), QMessageBox.Critical)

    def edit_rate(self):
        selection = self.rates_table.selectionModel().selectedRows()
        if not selection:
            show_centered_messagebox(self, "تنبيه", "اختر عملة أولاً", QMessageBox.Warning)
            return
        row = selection[0].row()
        code = self.rates_model._data[row][0]
        current_rate = self.rates_model._data[row][1]
        dialog = CenteredDialog(self)
        dialog.setWindowTitle(f"تعديل سعر الصرف لـ {code}")
        dialog.setLayoutDirection(Qt.RightToLeft)
        layout = QFormLayout(dialog)
        rate_edit = QDoubleSpinBox()
        rate_edit.setRange(0.000001, 1000000)
        rate_edit.setDecimals(6)
        rate_edit.setValue(current_rate)
        layout.addRow("سعر الصرف (1 دولار = ?):", rate_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        if dialog.exec():
            new_rate = rate_edit.value()
            try:
                exchange_rate_dao.update(code, 1.0 / new_rate if new_rate != 0 else 0)
                self.load_exchange_rates()
                show_toast("تم تحديث السعر", "success", self)
            except Exception as e:
                show_centered_messagebox(dialog, "خطأ", str(e), QMessageBox.Critical)

    def delete_currency(self):
        selection = self.rates_table.selectionModel().selectedRows()
        if not selection:
            show_centered_messagebox(self, "تنبيه", "اختر عملة أولاً", QMessageBox.Warning)
            return
        row = selection[0].row()
        code = self.rates_model._data[row][0]
        if code == 'USD':
            show_centered_messagebox(self, "خطأ", "لا يمكن حذف الدولار الأمريكي", QMessageBox.Warning)
            return
        reply = show_centered_messagebox(self, "تأكيد الحذف", f"هل تريد حذف العملة {code}؟", QMessageBox.Question, QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                exchange_rate_dao.delete(code)
                self.load_exchange_rates()
                self.load_currency_settings()
                show_toast("تم حذف العملة", "success", self)
            except Exception as e:
                show_centered_messagebox(self, "خطأ", str(e), QMessageBox.Critical)

    def fetch_online_rates(self):
        show_toast("سيتم إضافة هذه الميزة قريباً", "info", self)

    def save_printer_settings(self):
        self.settings.setValue("printer_port", self.printer_port.text())
        self.settings.setValue("printer_copies", self.printer_copies.value())
        printer_id = self.printer_combo.currentData()
        if printer_id:
            from printer_manager import PrinterManager
            pm = PrinterManager()
            pm.save_default_printer(printer_id)
        show_toast("تم حفظ إعدادات الطابعة", "success", self)

    def load_printer_settings(self):
        from printer_manager import PrinterManager
        self.printer_manager = PrinterManager()
        self.printer_manager.load_default_printer()
        self.printer_combo.clear()
        for p in self.printer_manager.printers:
            self.printer_combo.addItem(p.name, p.id)
        default = self.printer_manager.get_default_printer()
        if default:
            idx = self.printer_combo.findData(default.id)
            if idx >= 0:
                self.printer_combo.setCurrentIndex(idx)

    def toggle_touch_mode(self, checked):
        self.settings.setValue("touch_mode", checked)
        show_toast("سيتم تطبيق الوضع اللمسي بعد إعادة التشغيل", "info", self)

    def save_backup_settings(self):
        self.settings.setValue("backup_interval", self.backup_interval.value())
        if self.main_window and hasattr(self.main_window, "restart_backup_timer"):
            self.main_window.restart_backup_timer()
        show_toast("تم حفظ إعدادات النسخ الاحتياطي", "success", self)

    def export_db(self):
        filename, _ = QFileDialog.getSaveFileName(self, "حفظ النسخة الاحتياطية", "alrajhi_backup.json", "JSON (*.json)")
        if not filename:
            return
        self.export_btn.setEnabled(False)
        show_toast("جاري تصدير البيانات...", "info", self)
        self.worker = ExportWorker()
        self.worker.finished.connect(lambda data: self._save_export_data(data, filename))
        self.worker.error.connect(self._on_export_error)
        self.worker.start()

    def _save_export_data(self, data, filename):
        try:
            with open(filename, 'wb') as f:
                f.write(data)
            show_toast("تم التصدير بنجاح", "success", self)
        except Exception as e:
            show_centered_messagebox(self, "خطأ", str(e), QMessageBox.Critical)
        finally:
            self.export_btn.setEnabled(True)

    def _on_export_error(self, msg):
        show_centered_messagebox(self, "خطأ", f"خطأ في التصدير: {msg}", QMessageBox.Critical)
        self.export_btn.setEnabled(True)

    def import_db(self):
        filename, _ = QFileDialog.getOpenFileName(self, "اختر ملف النسخة الاحتياطية", "", "JSON (*.json)")
        if not filename:
            return
        with open(filename, 'rb') as f:
            data = f.read()
        reply = show_centered_messagebox(self, "تأكيد الاستيراد", "سيتم استبدال جميع البيانات الحالية. هل أنت متأكد?", QMessageBox.Question, QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        self.import_btn.setEnabled(False)
        show_toast("جاري استيراد البيانات...", "info", self)
        self.worker = ImportWorker(data)
        self.worker.finished.connect(self._on_import_finished)
        self.worker.error.connect(self._on_import_error)
        self.worker.start()

    def _on_import_finished(self):
        show_toast("تم الاستيراد، أعد تشغيل البرنامج", "success", self)
        self.import_btn.setEnabled(True)

    def _on_import_error(self, msg):
        show_centered_messagebox(self, "خطأ", f"خطأ في الاستيراد: {msg}", QMessageBox.Critical)
        self.import_btn.setEnabled(True)

    def reset_db(self):
        reply = show_centered_messagebox(self, "إعادة تعيين قاعدة البيانات", 
                                         "تحذير: سيتم حذف جميع البيانات نهائياً! هل أنت متأكد?", 
                                         QMessageBox.Warning, QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                from database.connection import DB_PATH
                db_conn = DatabaseConnection()
                db_conn.close()
                if os.path.exists(DB_PATH):
                    os.remove(DB_PATH)
                # إنشاء اتصال جديد وإعادة تهيئة الجداول
                new_conn = DatabaseConnection()
                # إجبار إعادة التهيئة يدوياً (للتأكد)
                new_conn.init_tables()
                new_conn._run_migrations()
                new_conn._add_indexes()
                # إعادة تعيين الـ session المحلي
                from database.session import UserSession
                # الاحتفاظ بمعرف المستخدم الحالي إن أمكن
                current_uid = UserSession.get_current_user_id()
                if current_uid:
                    # إعادة إنشاء المستخدم admin الافتراضي إذا لم يكن موجوداً
                    new_conn.check_default_admin_password()
                show_toast("تم إعادة تعيين قاعدة البيانات بنجاح", "success", self)
                if self.main_window:
                    # تحديث جميع الصفحات
                    for page in self.main_window.pages.values():
                        if hasattr(page, 'refresh'):
                            page.refresh()
                    self.main_window.switch_page('dashboard')
            except Exception as e:
                show_centered_messagebox(self, "خطأ", f"فشل إعادة التعيين: {str(e)}", QMessageBox.Critical)

    def logout(self):
        reply = show_centered_messagebox(self, "تسجيل الخروج", "هل تريد تسجيل الخروج؟", QMessageBox.Question, QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            from database.session import UserSession
            UserSession.clear_current_user()
            os.execl(sys.executable, sys.executable, *sys.argv)

    def open_label_designer(self):
        from label_designer import LabelDesigner
        dialog = LabelDesigner(self)
        dialog.exec()
