#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ========== Fix for OpenCV Qt plugin conflict ==========
import os
import sys

# ========== Fix for Qt platform plugin (Windows vs Linux) ==========
if sys.platform == 'win32':
    os.environ["QT_QPA_PLATFORM"] = "windows"
elif sys.platform.startswith('linux'):
    os.environ["QT_QPA_PLATFORM"] = "xcb"
else:
    os.environ["QT_QPA_PLATFORM"] = "windows"

os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = ""
os.environ["OPENCV_OPENCL_RUNTIME"] = ""
os.environ["OPENCV_QT_PLUGIN_PATH"] = ""
os.environ["PYTHONWARNINGS"] = "ignore"
os.environ["QT_DEBUG_PLUGINS"] = "0"

from PyQt5.QtWidgets import (QApplication, QMainWindow, QStackedWidget, QVBoxLayout, QHBoxLayout,
                             QWidget, QPushButton, QLabel, QFrame, QMenuBar, QAction,
                             QStatusBar, QShortcut, QDialog, QSystemTrayIcon, QMenu)
from PyQt5.QtGui import QFont, QKeySequence, QIcon, QPixmap
from PyQt5.QtCore import Qt, QSettings, QPoint, QSize, QTimer
from datetime import datetime, timedelta

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

if os.environ.get('TERMUX_VERSION') or os.path.exists('/data/data/com.termux'):
    os.environ['QT_QPA_PLATFORM'] = 'xcb'
    os.environ['QT_QPA_PLATFORMTHEME'] = 'gtk2'
    os.environ['QT_QPA_NO_NATIVE_DIALOGS'] = '1'

try:
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
except:
    pass
try:
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
except:
    pass

import qt_material
import qtawesome as qta

from database import reporting_dao, invoice_dao, customer_dao, supplier_dao, item_dao, voucher_dao, expense_dao, exchange_rate_dao, Session
from database.connection import DatabaseConnection
from activation import check_activation
from auth import is_admin, get_current_user
from splash_screen import ModernSplashScreen
from welcome_screen import WelcomeScreen

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("الراجحي للمحاسبة")
        self.setWindowIcon(QIcon(resource_path("alrajhi_icon.ico")))
        self.setMinimumSize(1200, 700)
        self.resize(1400, 900)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.load_settings()
        self.drag_pos = None

        central_widget = QWidget()
        central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(central_widget)
        main_vlayout = QVBoxLayout(central_widget)
        main_vlayout.setContentsMargins(0,0,0,0)
        main_vlayout.setSpacing(0)

        self.title_bar = QFrame()
        self.title_bar.setObjectName("TitleBar")
        self.title_bar.setFixedHeight(40)
        self.title_bar.setStyleSheet("""
            #TitleBar {
                background-color: #2c3e50;
                border-bottom: 1px solid #1a2632;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #34495e;
            }
            QPushButton#close_btn:hover {
                background-color: #e74c3c;
            }
            QLabel {
                color: white;
                font-size: 14px;
                padding: 0 10px;
            }
        """)
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(5, 0, 5, 0)

        self.menu_toggle_btn = QPushButton()
        self.menu_toggle_btn.setIcon(qta.icon('fa5s.bars'))
        self.menu_toggle_btn.setIconSize(QSize(24,24))
        self.menu_toggle_btn.setFixedSize(30,30)
        self.menu_toggle_btn.clicked.connect(self.toggle_sidebar)
        title_layout.addWidget(self.menu_toggle_btn)

        logo_pixmap = QPixmap(resource_path("alrajhi_logo.png")).scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.logo_label = QLabel()
        self.logo_label.setPixmap(logo_pixmap)
        title_layout.addWidget(self.logo_label)

        self.title_label = QLabel("الراجحي للمحاسبة")
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()

        self.minimize_btn = QPushButton()
        self.minimize_btn.setIcon(qta.icon('fa5s.window-minimize'))
        self.minimize_btn.setFixedSize(30,30)
        self.minimize_btn.clicked.connect(self.showMinimized)
        title_layout.addWidget(self.minimize_btn)

        self.maximize_btn = QPushButton()
        self.maximize_btn.setIcon(qta.icon('fa5s.window-maximize'))
        self.maximize_btn.setFixedSize(30,30)
        self.maximize_btn.clicked.connect(self.toggle_maximize)
        title_layout.addWidget(self.maximize_btn)

        self.close_btn = QPushButton()
        self.close_btn.setIcon(qta.icon('fa5s.times'))
        self.close_btn.setObjectName("close_btn")
        self.close_btn.setFixedSize(30,30)
        self.close_btn.clicked.connect(self.close)
        title_layout.addWidget(self.close_btn)

        main_vlayout.addWidget(self.title_bar)

        from views_pyqt5.modern_topbar import ModernTopBar
        self.top_bar = ModernTopBar(self)
        main_vlayout.addWidget(self.top_bar)

        self.stack = QStackedWidget()
        main_vlayout.addWidget(self.stack)

        self.pages = {}
        self.init_pages()
        self.setup_topbar_buttons()

        self.update_badges()

        menubar = self.menuBar()
        file_menu = menubar.addMenu("ملف")
        exit_action = QAction("خروج", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        theme_menu = menubar.addMenu("الثيم")
        for theme_name in ["dark_teal.xml", "light_blue.xml", "dark_green.xml", "dark_blue.xml"]:
            display_name = theme_name.replace('.xml', '').replace('_', ' ').title()
            action = QAction(display_name, self)
            action.triggered.connect(lambda checked, t=theme_name: self.change_theme(t))
            theme_menu.addAction(action)

        QShortcut(QKeySequence("Ctrl+K"), self, self.show_global_search)
        QShortcut(QKeySequence("Ctrl+1"), self, lambda: self.switch_page('dashboard'))
        QShortcut(QKeySequence("Ctrl+2"), self, lambda: self.switch_page('invoices'))
        QShortcut(QKeySequence("Ctrl+3"), self, lambda: self.switch_page('items'))
        QShortcut(QKeySequence("Ctrl+4"), self, lambda: self.switch_page('customers'))

        self.statusBar().showMessage("جاهز")
        self.switch_page('dashboard')
        self.apply_theme(self.current_theme)

        self.setup_reminder()
        self.backup_timer = QTimer()
        self.backup_timer.timeout.connect(self.perform_auto_backup)
        self.restart_backup_timer()

    def init_pages(self):
        from views_pyqt5.dashboard import DashboardWidget
        from views_pyqt5.items import ItemsWidget
        from views_pyqt5.invoices import InvoicesWidget
        from views_pyqt5.customers_suppliers import CustomersSuppliersWidget
        from views_pyqt5.categories_units import CategoriesUnitsWidget
        from views_pyqt5.vouchers import VouchersWidget
        from views_pyqt5.reports_widget import ReportsWidget
        from views_pyqt5.settings import SettingsWidget
        from views_pyqt5.users import UsersWidget
        self.pages['dashboard'] = DashboardWidget(self)
        self.pages['items'] = ItemsWidget()
        self.pages['invoices'] = InvoicesWidget()
        self.pages['customers'] = CustomersSuppliersWidget(None, 'customer')
        self.pages['suppliers'] = CustomersSuppliersWidget(None, 'supplier')
        self.pages['categories'] = CategoriesUnitsWidget(None, 'category')
        self.pages['vouchers'] = VouchersWidget()
        self.pages['reports'] = ReportsWidget()
        self.pages['settings'] = SettingsWidget(main_window=self)
        if is_admin():
            self.pages['users'] = UsersWidget()
        for name, widget in self.pages.items():
            self.stack.addWidget(widget)

    def setup_topbar_buttons(self):
        self.top_bar.add_button("الرئيسية", "tachometer-alt", lambda: self.switch_page('dashboard'))
        self.top_bar.add_button("المواد", "boxes", lambda: self.switch_page('items'))
        self.top_bar.add_button("الفواتير", "file-invoice", lambda: self.switch_page('invoices'))
        self.top_bar.add_button("العملاء", "user-friends", lambda: self.switch_page('customers'))
        self.top_bar.add_button("الموردين", "truck", lambda: self.switch_page('suppliers'))
        self.top_bar.add_button("التصنيفات", "folder", lambda: self.switch_page('categories'))
        self.top_bar.add_button("السندات", "scroll", lambda: self.switch_page('vouchers'))
        self.top_bar.add_button("التقارير", "chart-line", lambda: self.switch_page('reports'))
        self.top_bar.add_button("الإعدادات", "cog", lambda: self.switch_page('settings'))
        if is_admin():
            self.top_bar.add_button("المستخدمين", "user-cog", lambda: self.switch_page('users'))

    def toggle_sidebar(self):
        pass

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_pos is not None:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_pos = None

    def load_settings(self):
        settings = QSettings("Alrajhi", "Accounting")
        self.current_theme = settings.value("theme", "dark_teal.xml")

    def save_settings(self):
        settings = QSettings("Alrajhi", "Accounting")
        settings.setValue("theme", self.current_theme)

    def apply_theme(self, theme_name):
        try:
            qt_material.apply_stylesheet(QApplication.instance(), theme=theme_name)
        except Exception as e:
            print(f"خطأ في تطبيق الثيم: {e}")
            qt_material.apply_stylesheet(QApplication.instance(), theme="dark_teal.xml")

    def change_theme(self, theme_name):
        self.current_theme = theme_name
        self.apply_theme(theme_name)
        self.save_settings()
        from utils_pyqt5 import show_toast
        show_toast(f"تم تغيير الثيم إلى {theme_name}", "success", self)

    def switch_page(self, page_name):
        widget = self.pages.get(page_name)
        if widget:
            self.stack.setCurrentWidget(widget)
            if hasattr(widget, 'refresh'):
                widget.refresh()
            self.statusBar().showMessage(f"فتح {page_name}", 2000)

    def update_badges(self):
        invoices = invoice_dao.get_all()
        pending = sum(1 for inv in invoices if inv.total > inv.paid)
        self.top_bar.set_badge("الفواتير", pending)

    def show_global_search(self):
        from views_pyqt5.global_search import GlobalSearchDialog
        dialog = GlobalSearchDialog(self)
        dialog.exec()

    def setup_reminder(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.windowIcon())
        self.tray_icon.setVisible(True)
        tray_menu = QMenu()
        show_action = tray_menu.addAction("عرض التطبيق")
        show_action.triggered.connect(self.showNormal)
        quit_action = tray_menu.addAction("خروج")
        quit_action.triggered.connect(self.close)
        self.tray_icon.setContextMenu(tray_menu)

        self.reminder_timer = QTimer()
        self.reminder_timer.timeout.connect(self.check_overdue_invoices)
        self.reminder_timer.start(3600000)
        self.check_overdue_invoices()

    def check_overdue_invoices(self):
        invoices = invoice_dao.get_all()
        overdue = 0
        for inv in invoices:
            if inv.total - inv.paid > 0:
                overdue += 1
        if overdue > 0:
            self.tray_icon.showMessage("تذكير بالدفعات", f"لديك {overdue} فاتورة غير مسددة.", QSystemTrayIcon.Warning, 5000)
        self.top_bar.set_badge("الفواتير", overdue)

    def restart_backup_timer(self):
        settings = QSettings("Alrajhi", "Accounting")
        interval_days = settings.value("backup_interval", 1, type=int)
        interval_ms = interval_days * 24 * 3600 * 1000
        self.backup_timer.start(interval_ms)

    def perform_auto_backup(self):
        from utils_pyqt5 import create_auto_backup, show_toast
        backup_file = create_auto_backup()
        if backup_file:
            show_toast(f"تم إنشاء نسخة احتياطية تلقائية: {os.path.basename(backup_file)}", "success", self)

def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Tajawal", 10))
    app.setWindowIcon(QIcon(resource_path("alrajhi_icon.ico")))

    splash = ModernSplashScreen()
    splash.show()
    splash.set_progress(10, "جاري تهيئة النظام...")
    QApplication.processEvents()

    splash.set_progress(30, "التحقق من التفعيل...")
    activation_result = check_activation()
    QApplication.processEvents()

    splash.set_progress(50, "تجهيز البيانات...")
    QApplication.processEvents()

    if not activation_result or (isinstance(activation_result, dict) and not activation_result.get('valid')):
        splash.set_progress(70, "التفعيل مطلوب...")
        QApplication.processEvents()
        from activation_dialog_pyqt5 import ActivationDialog
        dialog = ActivationDialog()
        splash.hide()
        if dialog.exec() != QDialog.Accepted:
            sys.exit(0)
        splash.show()
        splash.set_progress(80, "تم التفعيل، جاري المتابعة...")
        QApplication.processEvents()

    # التحقق من كلمة مرور المسؤول الافتراضية (مع إخفاء splash)
    db_conn = DatabaseConnection()
    if db_conn.check_default_admin_password():
        splash.set_progress(85, "كلمة المرور الافتراضية للمسؤول تحتاج إلى تغيير...")
        QApplication.processEvents()
        # إخفاء splash قبل فتح الحوار
        splash.hide()
        from views_pyqt5.change_password_dialog import ChangeAdminPasswordDialog
        dlg = ChangeAdminPasswordDialog()
        # ضبط النافذة لتكون في المقدمة ووسط الشاشة
        dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowStaysOnTopHint)
        dlg.exec()
        # إعادة إظهار splash
        splash.show()

    splash.set_progress(90, "تسجيل الدخول...")
    QApplication.processEvents()
    from login_dialog_pyqt5 import LoginDialog
    login = LoginDialog()
    splash.hide()
    if login.exec() != QDialog.Accepted:
        sys.exit(0)

    # ========== التحقق من الحاجة لتغيير كلمة المرور (ترقية SHA256 إلى PBKDF2) ==========
    if Session.get_force_password_change():
        from views_pyqt5.change_password_dialog import ChangePasswordDialog
        dlg = ChangePasswordDialog(Session.get_current_user_id())
        dlg.exec()
        Session.set_force_password_change(False)

    user_data = get_current_user()
    if user_data:
        from PyQt5.QtCore import QSettings
        settings = QSettings("Alrajhi", "Accounting")
        skip_welcome = settings.value("welcome/skip", False, type=bool)
        if not skip_welcome:
            summary = reporting_dao.get_summary()
            welcome = WelcomeScreen(user_data, summary)
            welcome.exec()
        else:
            print("تم تخطي شاشة الترحيب حسب الإعدادات (لم يتم إنشاؤها)")

    window = MainWindow()
    window.show()
    splash.finish_splash(window)
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
