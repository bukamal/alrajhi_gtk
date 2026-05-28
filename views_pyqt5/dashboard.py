# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QComboBox, QFrame, QMessageBox, QDialog, QApplication)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon
import qtawesome as qta
from database import db
from utils_pyqt5 import format_currency, show_toast
from config import get_currency_settings, refresh_currency_settings, currency_notifier
from views_pyqt5.kpi_cards import KPICardsWidget
from views_pyqt5.invoice_dialog import InvoiceDialog
from views_pyqt5.items import ItemsWidget
from views_pyqt5.centered_dialog import CenteredDialog

class DashboardWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(16)
        self.main_layout.setContentsMargins(16, 16, 16, 16)

        self.setup_currency_bar()
        self.kpi_cards = KPICardsWidget()
        self.main_layout.addWidget(self.kpi_cards)
        self.setup_quick_actions()
        self.setup_exchange_rates_card()
        currency_notifier.currency_changed.connect(self.on_currency_changed)
        self.refresh()

    def setup_currency_bar(self):
        currency_bar = QFrame()
        currency_bar.setStyleSheet("QFrame { background-color: #f8fafc; border-radius: 12px; padding: 8px; } QLabel { font-weight: bold; color: #1e293b; }")
        bar_layout = QHBoxLayout(currency_bar)
        bar_layout.setContentsMargins(12, 8, 12, 8)
        bar_layout.addWidget(QLabel("العملة المعروضة:"))
        self.currency_combo = QComboBox()
        self.currency_combo.setMinimumWidth(120)
        bar_layout.addWidget(self.currency_combo)
        bar_layout.addStretch()
        self.exchange_rate_label = QLabel()
        bar_layout.addWidget(self.exchange_rate_label)
        self.main_layout.addWidget(currency_bar)
        self.load_currencies()
        self.currency_combo.currentIndexChanged.connect(self.on_currency_selected)

    def load_currencies(self):
        rates = db.get_all_exchange_rates()
        self.currency_combo.clear()
        current_display = get_currency_settings().get('display_currency', 'USD')
        current_index = 0
        for i, r in enumerate(rates):
            code = r['currency_code']
            symbol = self.get_symbol(code)
            self.currency_combo.addItem(f"{code} ({symbol})", code)
            if code == current_display:
                current_index = i
        self.currency_combo.setCurrentIndex(current_index)
        self.update_exchange_rate_label(current_display)

    def get_symbol(self, code):
        from config import get_currency_symbol
        return get_currency_symbol(code)

    def update_exchange_rate_label(self, currency_code):
        rate = db.get_exchange_rate(currency_code)
        if rate:
            usd_rate = 1.0 / float(rate) if rate != 0 else 0
            self.exchange_rate_label.setText(f"1 {currency_code} = {usd_rate:.4f} USD")
        else:
            self.exchange_rate_label.setText("")

    def on_currency_selected(self, index):
        new_currency = self.currency_combo.currentData()
        if not new_currency:
            return
        settings = get_currency_settings()
        if settings['display_currency'] == new_currency:
            return
        settings['display_currency'] = new_currency
        from config import save_currency_settings
        save_currency_settings(settings)
        show_toast(f"تم تغيير العملة إلى {new_currency}", "success", self)

    def on_currency_changed(self, new_currency):
        for i in range(self.currency_combo.count()):
            if self.currency_combo.itemData(i) == new_currency:
                self.currency_combo.setCurrentIndex(i)
                break
        self.update_exchange_rate_label(new_currency)
        self.refresh_kpis()

    def setup_quick_actions(self):
        actions_frame = QFrame()
        actions_frame.setStyleSheet("QFrame { background-color: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; } QPushButton { background-color: #f1f5f9; border: none; border-radius: 12px; padding: 12px; font-weight: bold; font-size: 14px; } QPushButton:hover { background-color: #e2e8f0; }")
        actions_layout = QHBoxLayout(actions_frame)
        actions_layout.setSpacing(16)
        actions_layout.setContentsMargins(16, 16, 16, 16)

        self.add_item_btn = QPushButton(qta.icon('fa5s.boxes', color='#3b82f6'), " إضافة مادة")
        self.add_item_btn.setIconSize(QSize(28, 28))
        self.add_item_btn.clicked.connect(self.quick_add_item)

        self.sale_inv_btn = QPushButton(qta.icon('fa5s.file-invoice-dollar', color='#10b981'), " فاتورة بيع")
        self.sale_inv_btn.setIconSize(QSize(28, 28))
        self.sale_inv_btn.clicked.connect(lambda: self.quick_invoice('sale'))

        self.purchase_inv_btn = QPushButton(qta.icon('fa5s.shopping-cart', color='#f59e0b'), " فاتورة شراء")
        self.purchase_inv_btn.setIconSize(QSize(28, 28))
        self.purchase_inv_btn.clicked.connect(lambda: self.quick_invoice('purchase'))

        actions_layout.addWidget(self.add_item_btn)
        actions_layout.addWidget(self.sale_inv_btn)
        actions_layout.addWidget(self.purchase_inv_btn)
        actions_layout.addStretch()
        self.main_layout.addWidget(actions_frame)

    def setup_exchange_rates_card(self):
        rates_frame = QFrame()
        rates_frame.setStyleSheet("QFrame { background-color: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; } QLabel { padding: 4px; }")
        rates_layout = QVBoxLayout(rates_frame)
        rates_layout.setSpacing(8)
        rates_layout.setContentsMargins(16, 16, 16, 16)

        title = QLabel("📊 أسعار الصرف مقابل الدولار")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        rates_layout.addWidget(title)

        self.rates_grid = QHBoxLayout()
        self.rate_labels = {}
        display_codes = ['USD', 'EUR', 'GBP', 'SAR', 'AED', 'SYP']
        for code in display_codes:
            label = QLabel(f"{code}: --")
            label.setStyleSheet("font-size: 12px;")
            self.rate_labels[code] = label
            self.rates_grid.addWidget(label)
        rates_layout.addLayout(self.rates_grid)

        refresh_btn = QPushButton("تحديث الأسعار")
        refresh_btn.setObjectName("secondary")
        refresh_btn.clicked.connect(self.open_currency_settings)
        rates_layout.addWidget(refresh_btn, alignment=Qt.AlignLeft)

        self.main_layout.addWidget(rates_frame)
        self.update_rates_display()

    def update_rates_display(self):
        for code, label in self.rate_labels.items():
            rate_to_usd = db.get_exchange_rate(code)
            if rate_to_usd:
                usd_rate = 1.0 / float(rate_to_usd) if rate_to_usd != 0 else 0
                label.setText(f"{code}: {usd_rate:.4f}")
            else:
                label.setText(f"{code}: --")

    def quick_add_item(self):
        # إنشاء كائن ItemsWidget مؤقت ولكن نمرر له الداشبورد كـ parent
        # ثم نستدعي open_item_dialog مع تمرير الداشبورد كـ dialog_parent
        temp_widget = ItemsWidget(self)
        temp_widget.open_item_dialog(is_edit=False, dialog_parent=self)
        self.refresh()

    def quick_invoice(self, inv_type):
        dialog = InvoiceDialog(inv_type, self)
        dialog.exec()
        self.refresh()

    def open_currency_settings(self):
        from views_pyqt5.settings import SettingsWidget
        dialog = CenteredDialog(self)
        dialog.setWindowTitle("إعدادات العملات وأسعار الصرف")
        dialog.setLayoutDirection(Qt.RightToLeft)
        dialog.resize(700, 500)
        layout = QVBoxLayout(dialog)
        settings_widget = SettingsWidget(main_window=self.parent_window)
        layout.addWidget(settings_widget)
        def on_finished():
            self.load_currencies()
            self.update_rates_display()
            self.refresh()
        dialog.finished.connect(on_finished)
        dialog.exec()

    def refresh(self):
        self.refresh_kpis()
        self.update_rates_display()

    def refresh_kpis(self):
        summary = db.get_summary()
        settings = get_currency_settings()
        self.kpi_cards.clear()
        self.kpi_cards.add_card("إجمالي المبيعات", format_currency(summary['total_sales'], settings), "💰", "#10b981", "up", "+12%", callback=lambda: self._switch_page('invoices'))
        self.kpi_cards.add_card("صافي الربح", format_currency(summary['net_profit'], settings), "📈", "#3b82f6", "up" if summary['net_profit'] >= 0 else "down", "+5%" if summary['net_profit'] >= 0 else "-2%")
        self.kpi_cards.add_card("رصيد الصندوق", format_currency(summary['cash_balance'], settings), "🏦", "#f59e0b")
        self.kpi_cards.add_card("الذمم المدينة", format_currency(summary['receivables'], settings), "📌", "#ef4444")
        self.kpi_cards.add_card("الذمم الدائنة", format_currency(summary['payables'], settings), "⚠️", "#8b5cf6")
        self.kpi_cards.add_card("إجمالي المصاريف", format_currency(summary['total_expenses'], settings), "📊", "#64748b")

    def _switch_page(self, page_name):
        if self.parent_window and hasattr(self.parent_window, 'switch_page'):
            self.parent_window.switch_page(page_name)
