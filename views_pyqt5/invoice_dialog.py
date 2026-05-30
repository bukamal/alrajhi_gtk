# views_pyqt5/invoice_dialog.py
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
                             QDoubleSpinBox, QDateEdit, QTextEdit, QGroupBox, QListWidget,
                             QPushButton, QFormLayout, QMessageBox, QShortcut, QLineEdit, QApplication)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QKeySequence
from decimal import Decimal
from database import item_dao, customer_dao, supplier_dao, invoice_dao, exchange_rate_dao, reporting_dao
from database.utils import storage_to_decimal, decimal_to_storage
from utils_pyqt5 import format_currency, show_toast
from config import get_currency_settings, get_current_currency_symbol
from views_pyqt5.centered_dialog import CenteredDialog

BARCODE_SCANNER_AVAILABLE = None

def _get_barcode_scanner():
    global BARCODE_SCANNER_AVAILABLE
    try:
        from views_pyqt5.barcode_scanner import BarcodeScanner
        BARCODE_SCANNER_AVAILABLE = True
        return BarcodeScanner
    except ImportError:
        BARCODE_SCANNER_AVAILABLE = False
        return None

class InvoiceDialog(CenteredDialog):
    def __init__(self, inv_type, parent=None):
        super().__init__(parent)
        self.inv_type = inv_type
        self.lines = []
        self.setWindowTitle(f"فاتورة {'بيع' if inv_type=='sale' else 'شراء'} جديدة")
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(800, 750)
        self.init_ui()
        self.setup_shortcuts()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        currency_symbol = get_current_currency_symbol()

        # شريط الباركود
        barcode_layout = QHBoxLayout()
        barcode_label = QLabel("باركود:")
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("امسح الباركود أو اكتبه ثم اضغط Enter")
        self.barcode_input.returnPressed.connect(self.add_item_by_barcode)
        self.scan_btn = QPushButton("📷 مسح بالكاميرا")
        if _get_barcode_scanner() is None:
            self.scan_btn.setEnabled(False)
            self.scan_btn.setToolTip("مكتبات الكاميرا غير مثبتة")
        else:
            self.scan_btn.clicked.connect(self.scan_barcode)
        barcode_layout.addWidget(barcode_label)
        barcode_layout.addWidget(self.barcode_input)
        barcode_layout.addWidget(self.scan_btn)
        main_layout.addLayout(barcode_layout)

        # قائمة العملاء أو الموردين
        if self.inv_type == 'sale':
            self.customers = customer_dao.get_all()
            self.entity_combo = QComboBox()
            self.entity_combo.addItem("نقدي", None)
            for c in self.customers:
                self.entity_combo.addItem(f"{c.name} (الرصيد: {format_currency(c.balance)})", c.id)
            entity_label = QLabel("العميل:")
        else:
            self.suppliers = supplier_dao.get_all()
            self.entity_combo = QComboBox()
            self.entity_combo.addItem("نقدي", None)
            for s in self.suppliers:
                self.entity_combo.addItem(f"{s.name} (الرصيد: {format_currency(s.balance)})", s.id)
            entity_label = QLabel("المورد:")

        self.balance_label = QLabel()
        self.balance_label.setStyleSheet("color: #3b82f6; font-weight: bold; margin-top: 5px;")
        self.balance_label.setVisible(False)

        main_layout.addWidget(entity_label)
        main_layout.addWidget(self.entity_combo)
        main_layout.addWidget(self.balance_label)

        # مجموعة بنود الفاتورة
        self.group = QGroupBox("بنود الفاتورة")
        group_layout = QVBoxLayout(self.group)
        self.lines_list = QListWidget()
        group_layout.addWidget(self.lines_list)
        btn_add_line = QPushButton("➕ إضافة بند")
        btn_add_line.clicked.connect(self.add_line)
        btn_remove_line = QPushButton("🗑 حذف البند المحدد")
        btn_remove_line.clicked.connect(self.remove_selected_line)
        group_layout.addWidget(btn_add_line)
        group_layout.addWidget(btn_remove_line)
        main_layout.addWidget(self.group)

        # نموذج المعلومات
        form = QFormLayout()
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        form.addRow("التاريخ:", self.date_edit)
        self.ref_edit = QTextEdit()
        self.ref_edit.setMaximumHeight(60)
        form.addRow("المرجع (سيُولد تلقائياً):", self.ref_edit)
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(80)
        form.addRow("ملاحظات:", self.notes_edit)
        self.paid_spin = QDoubleSpinBox()
        self.paid_spin.setRange(0, 999999)
        self.paid_spin.setDecimals(2)
        self.paid_spin.setPrefix(f"{currency_symbol} ")
        form.addRow("المدفوع:", self.paid_spin)
        main_layout.addLayout(form)

        self.total_label = QLabel()
        self.total_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        main_layout.addWidget(self.total_label)

        # أزرار الحفظ والإلغاء
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("حفظ (F2)")
        self.save_btn.setObjectName("primary")
        self.cancel_btn = QPushButton("إلغاء")
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        main_layout.addLayout(btn_layout)

        self.save_btn.clicked.connect(self.on_save)
        self.cancel_btn.clicked.connect(self.reject)
        self.update_total()

        self.entity_combo.currentIndexChanged.connect(self.update_balance_display)
        self.update_balance_display()

    def update_balance_display(self):
        entity_id = self.entity_combo.currentData()
        if not entity_id:
            self.balance_label.setVisible(False)
            return
        if self.inv_type == 'sale':
            customer = next((c for c in self.customers if c.id == entity_id), None)
            if customer:
                self.balance_label.setText(f"رصيد العميل الحالي: {format_currency(customer.balance)}")
                self.balance_label.setVisible(True)
        else:
            supplier = next((s for s in self.suppliers if s.id == entity_id), None)
            if supplier:
                self.balance_label.setText(f"رصيد المورد الحالي: {format_currency(supplier.balance)}")
                self.balance_label.setVisible(True)

    def scan_barcode(self):
        BarcodeScanner = _get_barcode_scanner()
        if BarcodeScanner is None:
            show_toast("مكتبات الكاميرا غير مثبتة. لا يمكن المسح.", "error", self)
            return
        scanner = BarcodeScanner(self)
        if scanner.exec():
            barcode = scanner.get_barcode()
            if barcode:
                self.barcode_input.setText(barcode)
                self.add_item_by_barcode()

    def add_item_by_barcode(self):
        barcode = self.barcode_input.text().strip()
        if not barcode:
            return
        item = item_dao.get_by_barcode(barcode)
        if not item:
            show_toast(f"لم يتم العثور على مادة بهذا الباركود: {barcode}", "error", self)
            self.barcode_input.clear()
            return
        price = item.selling_price if self.inv_type == 'sale' else item.purchase_price
        line_data = {
            'item_id': item.id,
            'item_name': item.name,
            'quantity': Decimal('1'),
            'unit': item.unit,
            'conversion_factor': Decimal('1'),
            'base_qty': Decimal('1'),
            'unit_price': price,
            'total': price
        }
        self.lines.append(line_data)
        unit_display = f" ({line_data['unit']})" if line_data['unit'] else ""
        currency_settings = get_currency_settings()
        self.lines_list.addItem(f"{item.name}{unit_display} - 1 × {format_currency(price, currency_settings)} = {format_currency(price, currency_settings)}")
        self.update_total()
        self.barcode_input.clear()
        show_toast(f"تمت إضافة {item.name}", "success", self)

    def setup_shortcuts(self):
        QShortcut(QKeySequence("F2"), self, self.on_save)
        QShortcut(QKeySequence("F3"), self, self.print_invoice)
        QShortcut(QKeySequence("F4"), self, self.add_customer_supplier)
        QShortcut(QKeySequence("F5"), self, self.refresh_items)

    def add_line(self):
        dialog = CenteredDialog(self)
        dialog.setWindowTitle("إضافة بند")
        dialog.setLayoutDirection(Qt.RightToLeft)
        dialog.resize(500, 420)
        layout = QFormLayout(dialog)
        currency_symbol = get_current_currency_symbol()
        currency_settings = get_currency_settings()

        barcode_line = QHBoxLayout()
        barcode_edit = QLineEdit()
        barcode_edit.setPlaceholderText("امسح الباركود")
        barcode_edit.returnPressed.connect(lambda: self.load_item_by_barcode(barcode_edit, item_combo, unit_combo, price_spin))
        barcode_search_btn = QPushButton("🔍")
        barcode_search_btn.clicked.connect(lambda: self.search_barcode_and_select(barcode_edit, item_combo, unit_combo, price_spin))
        barcode_line.addWidget(barcode_edit)
        barcode_line.addWidget(barcode_search_btn)
        layout.addRow("الباركود:", barcode_line)

        items = item_dao.get_items()
        item_combo = QComboBox()
        for it in items:
            price = it.selling_price if self.inv_type == 'sale' else it.purchase_price
            barcode_info = f" [باركود: {it.barcode}]" if it.barcode else ""
            item_combo.addItem(f"{it.name} ({format_currency(price, currency_settings)}){barcode_info}", it.id)
        layout.addRow("المادة:", item_combo)

        qty_spin = QDoubleSpinBox()
        qty_spin.setRange(0.01, 999999)
        qty_spin.setDecimals(2)
        qty_spin.setValue(1)
        layout.addRow("الكمية:", qty_spin)

        unit_combo = QComboBox()
        unit_combo.addItem("الوحدة الأساسية", Decimal('1'))
        layout.addRow("الوحدة:", unit_combo)

        price_spin = QDoubleSpinBox()
        price_spin.setRange(0.01, 999999)
        price_spin.setDecimals(2)
        price_spin.setPrefix(f"{currency_symbol} ")
        layout.addRow("السعر:", price_spin)

        def update_units():
            item_id = item_combo.currentData()
            unit_combo.clear()
            unit_combo.addItem("الوحدة الأساسية", Decimal('1'))
            if item_id:
                subunits = item_dao.get_units(item_id)
                for su in subunits:
                    unit_combo.addItem(su.unit_name, su.conversion_factor)
            update_price()

        def update_price():
            item_id = item_combo.currentData()
            if item_id:
                item = next((i for i in items if i.id == item_id), None)
                if item:
                    price = item.selling_price if self.inv_type == 'sale' else item.purchase_price
                    price_spin.setValue(float(price))

        item_combo.currentIndexChanged.connect(update_units)
        update_units()

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("إضافة")
        cancel_btn = QPushButton("إلغاء")
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

        def on_add():
            item_id = item_combo.currentData()
            if not item_id:
                show_toast("اختر مادة", "error", dialog)
                return
            item = next((i for i in items if i.id == item_id), None)
            if not item:
                return
            qty = Decimal(str(qty_spin.value()))
            factor = unit_combo.currentData()
            if not isinstance(factor, Decimal):
                factor = Decimal(str(factor))
            unit_name = unit_combo.currentText()
            base_qty = qty * factor
            price = Decimal(str(price_spin.value()))
            total = base_qty * price
            line_data = {
                'item_id': item_id,
                'item_name': item.name,
                'quantity': qty,
                'unit': unit_name if unit_name != "الوحدة الأساسية" else item.unit,
                'conversion_factor': factor,
                'base_qty': base_qty,
                'unit_price': price,
                'total': total
            }
            self.lines.append(line_data)
            unit_display = f" ({line_data['unit']})" if line_data['unit'] else ""
            self.lines_list.addItem(f"{item.name}{unit_display} - {qty} × {format_currency(price, currency_settings)} = {format_currency(total, currency_settings)}")
            self.update_total()
            dialog.accept()

        add_btn.clicked.connect(on_add)
        cancel_btn.clicked.connect(dialog.reject)
        dialog.exec()

    def load_item_by_barcode(self, barcode_edit, item_combo, unit_combo, price_spin):
        barcode = barcode_edit.text().strip()
        if not barcode:
            return
        item = item_dao.get_by_barcode(barcode)
        if item:
            idx = item_combo.findData(item.id)
            if idx >= 0:
                item_combo.setCurrentIndex(idx)
                self.update_units_for_combo(item_combo, unit_combo, price_spin)
                show_toast("تم العثور على المادة", "success", self)
            else:
                show_toast("المادة غير موجودة في القائمة", "error", self)
        else:
            show_toast("لم يتم العثور على مادة بهذا الباركود", "error", self)

    def search_barcode_and_select(self, barcode_edit, item_combo, unit_combo, price_spin):
        self.load_item_by_barcode(barcode_edit, item_combo, unit_combo, price_spin)

    def update_units_for_combo(self, item_combo, unit_combo, price_spin):
        item_id = item_combo.currentData()
        unit_combo.clear()
        unit_combo.addItem("الوحدة الأساسية", Decimal('1'))
        if item_id:
            subunits = item_dao.get_units(item_id)
            for su in subunits:
                unit_combo.addItem(su.unit_name, su.conversion_factor)
        items = item_dao.get_items()
        item = next((i for i in items if i.id == item_id), None)
        if item:
            price = item.selling_price if self.inv_type == 'sale' else item.purchase_price
            price_spin.setValue(float(price))

    def remove_selected_line(self):
        row = self.lines_list.currentRow()
        if row >= 0:
            self.lines.pop(row)
            self.lines_list.takeItem(row)
            self.update_total()

    def update_total(self):
        total = sum(line['total'] for line in self.lines)
        self.total_label.setText(f"الإجمالي: {format_currency(total)}")
        if self.paid_spin.value() == 0:
            self.paid_spin.setValue(float(total))

    def on_save(self):
        if not self.lines:
            show_toast("أضف بنداً واحداً على الأقل", "error", self)
            return
        total = sum(line['total'] for line in self.lines)
        paid = Decimal(str(self.paid_spin.value()))
        if paid > total:
            paid = total
        entity_id = self.entity_combo.currentData()
        reference = self.ref_edit.toPlainText().strip()
        if not reference:
            reference = invoice_dao.get_next_reference(self.inv_type)
        else:
            invoices = invoice_dao.get_all()
            if any(inv.reference == reference for inv in invoices):
                show_toast("المرجع موجود مسبقاً، يرجى استخدام مرجع آخر", "error", self)
                return
        data = {
            'type': self.inv_type,
            'customer_id': entity_id if self.inv_type == 'sale' else None,
            'supplier_id': entity_id if self.inv_type == 'purchase' else None,
            'date': self.date_edit.date().toString("yyyy-MM-dd"),
            'reference': reference,
            'notes': self.notes_edit.toPlainText().strip(),
            'total': total,
            'paid_amount': paid,
            'lines': self.lines
        }
        try:
            invoice_dao.create_invoice(data)
            show_toast("تم حفظ الفاتورة", "success", self)
            self.accept()
        except Exception as e:
            show_toast(str(e), "error", self)

    def print_invoice(self):
        from PyQt5.QtGui import QTextDocument
        from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog
        inv_ref = self.ref_edit.toPlainText() or "جديدة"
        inv_date = self.date_edit.date().toString("yyyy-MM-dd")
        entity_name = self.entity_combo.currentText().split(' (')[0] if self.entity_combo.currentData() else 'نقدي'
        entity_label = 'العميل' if self.inv_type == 'sale' else 'المورد'
        lines = self.lines
        total = sum(line['total'] for line in lines)
        paid = Decimal(str(self.paid_spin.value()))
        remaining = total - paid
        notes = self.notes_edit.toPlainText().strip()

        html = f"""
        <!DOCTYPE html>
        <html dir="rtl">
        <head>
            <meta charset="UTF-8">
            <title>فاتورة {inv_ref}</title>
            <style>
                body {{ font-family: 'Tajawal', 'Arial', sans-serif; padding: 20px; margin: 0; }}
                .invoice-container {{ max-width: 800px; margin: auto; border: 1px solid #ddd; border-radius: 8px; padding: 20px; }}
                .header {{ text-align: center; margin-bottom: 20px; border-bottom: 2px solid #3b82f6; padding-bottom: 10px; }}
                .logo {{ font-size: 24px; font-weight: bold; color: #1e293b; }}
                .title {{ font-size: 20px; font-weight: bold; margin: 10px 0; }}
                .info {{ margin-bottom: 20px; }}
                .info table {{ width: 100%; }}
                .info td {{ padding: 5px; }}
                table.items {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
                th {{ background-color: #3b82f6; color: white; }}
                .totals {{ margin-top: 20px; text-align: left; }}
                .totals table {{ width: 300px; margin-left: auto; }}
                .footer {{ margin-top: 30px; text-align: center; font-size: 12px; color: #64748b; border-top: 1px solid #ddd; padding-top: 10px; }}
                .notes {{ margin-top: 20px; padding: 10px; background-color: #f8fafc; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="invoice-container">
                <div class="header">
                    <div class="logo">نظام الراجحي للمحاسبة</div>
                    <div class="title">فاتورة {inv_ref}</div>
                </div>
                <div class="info">
                    <table>
                        <tr>
                            <td style="font-weight:bold;">التاريخ:浏
                            <td>{inv_date}浏
                            <td style="font-weight:bold;">{entity_label}:浏
                            <td>{entity_name}浏
                        </tr>
                    </table>
                </div>
                <table class="items">
                    <thead>
                        <tr><th>المادة</th><th>الكمية</th><th>الوحدة</th><th>السعر</th><th>الإجمالي</th></tr>
                    </thead>
                    <tbody>
        """
        for line in lines:
            html += f"""
                        <tr>
                            <td style='padding:8px;'>{line['item_name']}浏
                            <td style='padding:8px;'>{line['quantity']}浏
                            <td style='padding:8px;'>{line.get('unit', '')}浏
                            <td style='padding:8px;'>{format_currency(line['unit_price'])}浏
                            <td style='padding:8px;'>{format_currency(line['total'])}浏
                        </tr>
            """
        html += f"""
                    </tbody>
                </table>
                <div class="totals">
                    <tr>
                        <tr>
                            <td style="font-weight:bold;">الإجمالي:浏
                            <td>{format_currency(total)}浏
                            <td style="font-weight:bold;">المدفوع:浏
                            <td>{format_currency(paid)}浏
                            <td style="font-weight:bold;">المتبقي:浏
                            <td>{format_currency(remaining)}浏
                        </tr>
                    </table>
                </div>
        """
        if notes:
            html += f'<div class="notes"><strong>ملاحظات:</strong> {notes}</div>'
        html += """
                <div class="footer">
                    شكراً للتعامل معنا<br>
                    هذا المستند إلكتروني ولا يحتاج إلى توقيع
                </div>
            </div>
        </body>
        </html>
        """
        doc = QTextDocument()
        doc.setHtml(html)
        printer = QPrinter(QPrinter.HighResolution)
        preview = QPrintPreviewDialog(printer, self)
        preview.paintRequested.connect(lambda p: doc.print(p))
        preview.exec()

    def add_customer_supplier(self):
        from views_pyqt5.customers_suppliers import CustomersSuppliersWidget
        dialog = CenteredDialog(self)
        dialog.setWindowTitle(f"إضافة {'عميل' if self.inv_type=='sale' else 'مورد'} جديد")
        layout = QVBoxLayout(dialog)
        widget = CustomersSuppliersWidget(dialog, 'customer' if self.inv_type=='sale' else 'supplier')
        def on_close():
            if self.inv_type == 'sale':
                self.customers = customer_dao.get_all()
                self.entity_combo.clear()
                self.entity_combo.addItem("نقدي", None)
                for c in self.customers:
                    self.entity_combo.addItem(f"{c.name} (الرصيد: {format_currency(c.balance)})", c.id)
                self.update_balance_display()
            else:
                self.suppliers = supplier_dao.get_all()
                self.entity_combo.clear()
                self.entity_combo.addItem("نقدي", None)
                for s in self.suppliers:
                    self.entity_combo.addItem(f"{s.name} (الرصيد: {format_currency(s.balance)})", s.id)
                self.update_balance_display()
            dialog.accept()
        widget.add_btn.clicked.disconnect()
        original_add = widget.add_entity
        def new_add():
            original_add()
            on_close()
        widget.add_btn.clicked.connect(new_add)
        layout.addWidget(widget)
        dialog.exec()

    def refresh_items(self):
        pass
