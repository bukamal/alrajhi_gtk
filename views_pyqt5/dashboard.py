# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from database import db
from utils_pyqt5 import format_currency
from config import get_currency_settings
from views_pyqt5.kpi_cards import KPICardsWidget
from views_pyqt5.charts import ModernChart

class DashboardWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(16)
        self.layout.setContentsMargins(16,16,16,16)

        self.kpi_cards = KPICardsWidget()
        self.layout.addWidget(self.kpi_cards)

        self.sales_chart = ModernChart("📈 المبيعات الشهرية")
        self.profit_chart = ModernChart("💰 صافي الربح الشهري")
        self.layout.addWidget(self.sales_chart)
        self.layout.addWidget(self.profit_chart)

        self.refresh()

    def refresh(self):
        summary = db.get_summary()
        settings = get_currency_settings()

        self.kpi_cards.clear()

        # إضافة البطاقات مع إمكانية النقر للانتقال
        self.kpi_cards.add_card(
            "إجمالي المبيعات",
            format_currency(summary['total_sales'], settings),
            "💰", "#10b981", "up", "+12%",
            callback=lambda: self._switch_page('invoices')
        )
        self.kpi_cards.add_card(
            "صافي الربح",
            format_currency(summary['net_profit'], settings),
            "📈", "#3b82f6",
            "up" if summary['net_profit'] >= 0 else "down",
            "+5%" if summary['net_profit'] >= 0 else "-2%"
        )
        self.kpi_cards.add_card(
            "رصيد الصندوق",
            format_currency(summary['cash_balance'], settings),
            "🏦", "#f59e0b"
        )
        self.kpi_cards.add_card(
            "الذمم المدينة",
            format_currency(summary['receivables'], settings),
            "📌", "#ef4444"
        )
        self.kpi_cards.add_card(
            "الذمم الدائنة",
            format_currency(summary['payables'], settings),
            "⚠️", "#8b5cf6"
        )
        self.kpi_cards.add_card(
            "إجمالي المصاريف",
            format_currency(summary['total_expenses'], settings),
            "📊", "#64748b"
        )

        # جلب بيانات حقيقية للرسوم البيانية
        sales_data = db.get_monthly_sales()
        profit_data = db.get_monthly_profit()

        if sales_data and len(sales_data) > 0:
            months = [d['month'] for d in sales_data]
            sales_values = [d['total'] for d in sales_data]
            self.sales_chart.plot_bar(months, sales_values, '#3b82f6')
        else:
            # بيانات تجريبية للاختبار
            months = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو']
            sales_values = [12000, 15000, 18000, 22000, 25000, 28000]
            self.sales_chart.plot_bar(months, sales_values, '#3b82f6')

        if profit_data and len(profit_data) > 0:
            months = [d['month'] for d in profit_data]
            profit_values = [d['profit'] for d in profit_data]
            self.profit_chart.plot_line(months, profit_values, 'صافي الربح', '#10b981')
        else:
            months = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو']
            profit_values = [2000, 2500, 3000, 3500, 4000, 4500]
            self.profit_chart.plot_line(months, profit_values, 'صافي الربح', '#10b981')

    def _switch_page(self, page_name):
        if self.parent_window and hasattr(self.parent_window, 'switch_page'):
            self.parent_window.switch_page(page_name)
