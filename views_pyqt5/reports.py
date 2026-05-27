# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, 
                             QComboBox, QLabel, QDialog, QFormLayout, QTabWidget, QFrame)
from PyQt5.QtCore import Qt
from database import db
from utils_pyqt5 import format_currency, show_toast

class ReportsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8,8,8,8)

        # علامات تبويب للتقارير
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        self.tabs.setDocumentMode(True)
        self.tabs.setStyleSheet("""
            QTabBar::tab { 
                padding: 8px 16px; 
                font-weight: bold;
            }
        """)

        # تبويب ميزان المراجعة
        self.trial_tab = QWidget()
        self.trial_layout = QVBoxLayout(self.trial_tab)
        self.trial_text = QTextEdit()
        self.trial_text.setReadOnly(True)
        self.trial_text.setStyleSheet("font-family: 'Tajawal'; font-size: 12px;")
        self.trial_layout.addWidget(self.trial_text)
        self.tabs.addTab(self.trial_tab, "📊 ميزان المراجعة")

        # تبويب قائمة الدخل
        self.income_tab = QWidget()
        self.income_layout = QVBoxLayout(self.income_tab)
        self.income_text = QTextEdit()
        self.income_text.setReadOnly(True)
        self.income_layout.addWidget(self.income_text)
        self.tabs.addTab(self.income_tab, "💰 قائمة الدخل")

        # تبويب الميزانية العمومية
        self.balance_tab = QWidget()
        self.balance_layout = QVBoxLayout(self.balance_tab)
        self.balance_text = QTextEdit()
        self.balance_text.setReadOnly(True)
        self.balance_layout.addWidget(self.balance_text)
        self.tabs.addTab(self.balance_tab, "🏦 الميزانية العمومية")

        # تبويب كشف حساب عميل
        self.customer_tab = QWidget()
        self.customer_layout = QVBoxLayout(self.customer_tab)
        customer_top = QHBoxLayout()
        self.customer_combo = QComboBox()
        self.customer_combo.setMinimumWidth(250)
        customer_top.addWidget(QLabel("اختر العميل:"))
        customer_top.addWidget(self.customer_combo)
        customer_top.addStretch()
        self.customer_layout.addLayout(customer_top)
        self.customer_text = QTextEdit()
        self.customer_text.setReadOnly(True)
        self.customer_layout.addWidget(self.customer_text)
        self.tabs.addTab(self.customer_tab, "👤 كشف حساب عميل")

        # تبويب كشف حساب مورد
        self.supplier_tab = QWidget()
        self.supplier_layout = QVBoxLayout(self.supplier_tab)
        supplier_top = QHBoxLayout()
        self.supplier_combo = QComboBox()
        self.supplier_combo.setMinimumWidth(250)
        supplier_top.addWidget(QLabel("اختر المورد:"))
        supplier_top.addWidget(self.supplier_combo)
        supplier_top.addStretch()
        self.supplier_layout.addLayout(supplier_top)
        self.supplier_text = QTextEdit()
        self.supplier_text.setReadOnly(True)
        self.supplier_layout.addWidget(self.supplier_text)
        self.tabs.addTab(self.supplier_tab, "🏭 كشف حساب مورد")

        layout.addWidget(self.tabs)

        # الآن نقوم بتحميل البيانات
        self.refresh_customers()
        self.refresh_suppliers()
        self.show_trial_balance()
        self.show_income_statement()
        self.show_balance_sheet()

    def refresh_customers(self):
        customers = db.get_customers()
        self.customer_combo.clear()
        for c in customers:
            self.customer_combo.addItem(f"{c['name']} (الرصيد: {format_currency(c['balance'])})", c['id'])
        if customers:
            self.show_customer_statement()
        else:
            self.customer_text.setHtml("<div style='text-align: center;'><h3>لا يوجد عملاء مسجلون</h3></div>")

    def refresh_suppliers(self):
        suppliers = db.get_suppliers()
        self.supplier_combo.clear()
        for s in suppliers:
            self.supplier_combo.addItem(f"{s['name']} (الرصيد: {format_currency(s['balance'])})", s['id'])
        if suppliers:
            self.show_supplier_statement()
        else:
            self.supplier_text.setHtml("<div style='text-align: center;'><h3>لا يوجد موردون مسجلون</h3></div>")

    def show_trial_balance(self):
        trial = db.get_trial_balance()
        html = """
        <div style="text-align: center;">
            <h2 style="color: #2c3e50;">ميزان المراجعة</h2>
            <hr>
        </div>
        <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
            <thead>
                <tr style="background-color: #34495e; color: white;">
                    <th style="padding: 8px; text-align: center;">الحساب</th>
                    <th style="padding: 8px; text-align: center;">مدين</th>
                    <th style="padding: 8px; text-align: center;">دائن</th>
                </td>
            </thead>
            <tbody>
        """
        for row in trial:
            html += f"""
                <tr style="border-bottom: 1px solid #ddd;">
                    <td style="padding: 8px; text-align: center;">{row['name']}</td>
                    <td style="padding: 8px; text-align: center;">{format_currency(row['debit'])}</td>
                    <td style="padding: 8px; text-align: center;">{format_currency(row['credit'])}</td>
                </tr>
            """
        total_debit = sum(r['debit'] for r in trial)
        total_credit = sum(r['credit'] for r in trial)
        html += f"""
                <tr style="background-color: #ecf0f1; font-weight: bold;">
                    <td style="padding: 8px; text-align: center;">الإجمالي</td>
                    <td style="padding: 8px; text-align: center;">{format_currency(total_debit)}</td>
                    <td style="padding: 8px; text-align: center;">{format_currency(total_credit)}</td>
                </tr>
            </tbody>
        </table>
        """
        self.trial_text.setHtml(html)

    def show_income_statement(self):
        stmt = db.get_income_statement()
        html = """
        <div style="text-align: center;">
            <h2 style="color: #2c3e50;">قائمة الدخل</h2>
            <hr>
        </div>
        <h3 style="color: #27ae60;">الإيرادات</h3>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
            <thead>
                <tr style="background-color: #2ecc71; color: white;">
                    <th style="padding: 8px; text-align: center;">الحساب</th>
                    <th style="padding: 8px; text-align: center;">الرصيد</th>
                </tr>
            </thead>
            <tbody>
        """
        for inc in stmt['income']:
            html += f"""
                <tr style="border-bottom: 1px solid #ddd;">
                    <td style="padding: 8px;">{inc['name']}</td>
                    <td style="padding: 8px; text-align: center;">{format_currency(inc['balance'])}</td>
                </tr>
            """
        html += f"""
                <tr style="background-color: #ecf0f1; font-weight: bold;">
                    <td style="padding: 8px;">إجمالي الإيرادات</td>
                    <td style="padding: 8px; text-align: center;">{format_currency(stmt['total_income'])}</td>
                </tr>
            </tbody>
        </table>
        <h3 style="color: #e67e22;">المصروفات</h3>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
            <thead>
                <tr style="background-color: #f39c12; color: white;">
                    <th style="padding: 8px; text-align: center;">الحساب</th>
                    <th style="padding: 8px; text-align: center;">الرصيد</th>
                </tr>
            </thead>
            <tbody>
        """
        for exp in stmt['expenses']:
            html += f"""
                <tr style="border-bottom: 1px solid #ddd;">
                    <td style="padding: 8px;">{exp['name']}</td>
                    <td style="padding: 8px; text-align: center;">{format_currency(exp['balance'])}</td>
                </tr>
            """
        html += f"""
                <tr style="background-color: #ecf0f1; font-weight: bold;">
                    <td style="padding: 8px;">إجمالي المصروفات</td>
                    <td style="padding: 8px; text-align: center;">{format_currency(stmt['total_expenses'])}</td>
                </tr>
                <tr style="background-color: #3498db; color: white; font-weight: bold;">
                    <td style="padding: 8px;">صافي الربح</td>
                    <td style="padding: 8px; text-align: center;">{format_currency(stmt['net_profit'])}</td>
                </tr>
            </tbody>
        </table>
        """
        self.income_text.setHtml(html)

    def show_balance_sheet(self):
        bs = db.get_balance_sheet()
        html = """
        <div style="text-align: center;">
            <h2 style="color: #2c3e50;">الميزانية العمومية</h2>
            <hr>
        </div>
        <h3 style="color: #2980b9;">الأصول</h3>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
            <thead>
                <tr style="background-color: #3498db; color: white;">
                    <th style="padding: 8px; text-align: center;">الحساب</th>
                    <th style="padding: 8px; text-align: center;">الرصيد</th>
                </tr>
            </thead>
            <tbody>
        """
        for a in bs['assets']:
            html += f"""
                <tr style="border-bottom: 1px solid #ddd;">
                    <td style="padding: 8px;">{a['name']}</td>
                    <td style="padding: 8px; text-align: center;">{format_currency(a['debit'])}</td>
                </tr>
            """
        html += f"""
                <tr style="background-color: #ecf0f1; font-weight: bold;">
                    <td style="padding: 8px;">إجمالي الأصول</td>
                    <td style="padding: 8px; text-align: center;">{format_currency(bs['total_assets'])}</td>
                </tr>
            </tbody>
        </table>
        <h3 style="color: #e67e22;">الخصوم</h3>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
            <thead>
                <tr style="background-color: #f39c12; color: white;">
                    <th style="padding: 8px; text-align: center;">الحساب</th>
                    <th style="padding: 8px; text-align: center;">الرصيد</th>
                </tr>
            </thead>
            <tbody>
        """
        for l in bs['liabilities']:
            html += f"""
                <tr style="border-bottom: 1px solid #ddd;">
                    <td style="padding: 8px;">{l['name']}</td>
                    <td style="padding: 8px; text-align: center;">{format_currency(l['credit'])}</td>
                </tr>
            """
        html += f"""
                <tr style="background-color: #ecf0f1; font-weight: bold;">
                    <td style="padding: 8px;">إجمالي الخصوم</td>
                    <td style="padding: 8px; text-align: center;">{format_currency(bs['total_liabilities'])}</td>
                </tr>
            </tbody>
        </table>
        <h3 style="color: #27ae60;">حقوق الملكية</h3>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
            <thead>
                <tr style="background-color: #2ecc71; color: white;">
                    <th style="padding: 8px; text-align: center;">الحساب</th>
                    <th style="padding: 8px; text-align: center;">الرصيد</th>
                </tr>
            </thead>
            <tbody>
        """
        for e in bs['equity']:
            html += f"""
                <tr style="border-bottom: 1px solid #ddd;">
                    <td style="padding: 8px;">{e['name']}</td>
                    <td style="padding: 8px; text-align: center;">{format_currency(e['credit'])}</td>
                </tr>
            """
        html += f"""
                <tr style="background-color: #ecf0f1; font-weight: bold;">
                    <td style="padding: 8px;">إجمالي حقوق الملكية</td>
                    <td style="padding: 8px; text-align: center;">{format_currency(bs['total_equity'])}</td>
                </tr>
            </tbody>
        </table>
        """
        self.balance_text.setHtml(html)

    def show_customer_statement(self):
        cust_id = self.customer_combo.currentData()
        if not cust_id:
            self.customer_text.setHtml("<div style='text-align: center;'><h3>اختر عميلاً أولاً</h3></div>")
            return
        lines = db.get_customer_statement(cust_id)
        if not lines:
            self.customer_text.setHtml("<div style='text-align: center;'><h3>لا توجد حركات لهذا العميل</h3></div>")
            return
        html = f"""
        <div style="text-align: center;">
            <h2 style="color: #2c3e50;">كشف حساب العميل</h2>
            <h3>{self.customer_combo.currentText().split(' (')[0]}</h3>
            <hr>
        </div>
        <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
            <thead>
                <tr style="background-color: #34495e; color: white;">
                    <th style="padding: 8px;">التاريخ</th>
                    <th style="padding: 8px;">الوصف</th>
                    <th style="padding: 8px;">مدين</th>
                    <th style="padding: 8px;">دائن</th>
                    <th style="padding: 8px;">الرصيد</th>
                </tr>
            </thead>
            <tbody>
        """
        balance = 0
        for l in lines:
            balance += l['debit'] - l['credit']
            html += f"""
                <tr style="border-bottom: 1px solid #ddd;">
                    <td style="padding: 8px; text-align: center;">{l['date']}</td>
                    <td style="padding: 8px;">{l['description']}浏
                    <td style="padding: 8px; text-align: center;">{format_currency(l['debit'])}浏
                    <td style="padding: 8px; text-align: center;">{format_currency(l['credit'])}浏
                    <td style="padding: 8px; text-align: center;">{format_currency(balance)}浏
                </tr>
            """
        html += """
            </tbody>
        </table>
        """
        self.customer_text.setHtml(html)

    def show_supplier_statement(self):
        supp_id = self.supplier_combo.currentData()
        if not supp_id:
            self.supplier_text.setHtml("<div style='text-align: center;'><h3>اختر مورداً أولاً</h3></div>")
            return
        lines = db.get_supplier_statement(supp_id)
        if not lines:
            self.supplier_text.setHtml("<div style='text-align: center;'><h3>لا توجد حركات لهذا المورد</h3></div>")
            return
        html = f"""
        <div style="text-align: center;">
            <h2 style="color: #2c3e50;">كشف حساب المورد</h2>
            <h3>{self.supplier_combo.currentText().split(' (')[0]}</h3>
            <hr>
        </div>
        <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
            <thead>
                <tr style="background-color: #34495e; color: white;">
                    <th style="padding: 8px;">التاريخ</th>
                    <th style="padding: 8px;">الوصف</th>
                    <th style="padding: 8px;">مدين</th>
                    <th style="padding: 8px;">دائن</th>
                    <th style="padding: 8px;">الرصيد</th>
                </tr>
            </thead>
            <tbody>
        """
        balance = 0
        for l in lines:
            balance += l['credit'] - l['debit']
            html += f"""
                <tr style="border-bottom: 1px solid #ddd;">
                    <td style="padding: 8px; text-align: center;">{l['date']}浏
                    <td style="padding: 8px;">{l['description']}浏
                    <td style="padding: 8px; text-align: center;">{format_currency(l['debit'])}浏
                    <td style="padding: 8px; text-align: center;">{format_currency(l['credit'])}浏
                    <td style="padding: 8px; text-align: center;">{format_currency(balance)}浏
                </tr>
            """
        html += """
            </tbody>
        </table>
        """
        self.supplier_text.setHtml(html)

    def refresh(self):
        self.show_trial_balance()
        self.show_income_statement()
        self.show_balance_sheet()
        self.refresh_customers()
        self.refresh_suppliers()
