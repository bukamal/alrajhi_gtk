# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
                             QDoubleSpinBox, QDateEdit, QTextEdit, QGroupBox, QListWidget,
                             QPushButton, QFormLayout, QMessageBox, QShortcut)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QKeySequence
from database import db
from utils_pyqt5 import format_currency, show_toast

class InvoiceDialog(QDialog):
    def __init__(self, inv_type, parent=None):
        super().__init__(parent)
        self.inv_type = inv_type
        self.lines = []
        self.setWindowTitle(f"فاتورة {'بيع' if inv_type=='sale' else 'شراء'} جديدة")
        self.setModal(True)
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(800, 700)
        self.init_ui()
        self.setup_shortcuts()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # اختيار العميل/المورد
        if self.inv_type == 'sale':
            self.customers = db.get_customers()
            self.entity_combo = QComboBox()
            self.entity_combo.addItem("نقدي", None)
            for c in self.customers:
                self.entity_combo.addItem(f"{c['name']} (الرصيد: {format_currency(c['balance'])})", c['id'])
            entity_label = QLabel("العميل:")
        else:
            self.suppliers = db.get_suppliers()
            self.entity_combo = QComboBox()
            self.entity_combo.addItem("نقدي", None)
            for s in self.suppliers:
                self.entity_combo.addItem(f"{s['name']} (الرصيد: {format_currency(s['balance'])})", s['id'])
            entity_label = QLabel("المورد:")

        main_layout.addWidget(entity_label)
        main_layout.addWidget(self.entity_combo)

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

        # نموذج المعلومات الإضافية
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
        self.paid_spin.setPrefix("$ ")
        form.addRow("المدفوع:", self.paid_spin)
        main_layout.addLayout(form)

        self.total_label = QLabel()
        self.total_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        main_layout.addWidget(self.total_label)

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

    def setup_shortcuts(self):
        QShortcut(QKeySequence("F2"), self, self.on_save)
        QShortcut(QKeySequence("F3"), self, self.print_invoice)
        QShortcut(QKeySequence("F4"), self, self.add_customer_supplier)
        QShortcut(QKeySequence("F5"), self, self.refresh_items)

    def add_line(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("إضافة بند")
        dialog.setLayoutDirection(Qt.RightToLeft)
        dialog.resize(450, 350)
        layout = QFormLayout(dialog)

        items = db.get_items()
        item_combo = QComboBox()
        for it in items:
            price = it.get('selling_price',0) if self.inv_type=='sale' else it.get('purchase_price',0)
            item_combo.addItem(f"{it['name']} ({format_currency(price)})", it['id'])
        layout.addRow("المادة:", item_combo)

        qty_spin = QDoubleSpinBox()
        qty_spin.setRange(0.01, 999999)
        qty_spin.setValue(1)
        layout.addRow("الكمية:", qty_spin)

        # قائمة الوحدات (تتغير حسب المادة)
        unit_combo = QComboBox()
        unit_combo.addItem("الوحدة الأساسية", 1.0)
        layout.addRow("الوحدة:", unit_combo)

        price_spin = QDoubleSpinBox()
        price_spin.setRange(0.01, 999999)
        price_spin.setPrefix("$ ")
        layout.addRow("السعر:", price_spin)

        def update_units():
            item_id = item_combo.currentData()
            unit_combo.clear()
            unit_combo.addItem("الوحدة الأساسية", 1.0)
            if item_id:
                subunits = db.get_item_units(item_id)
                for su in subunits:
                    unit_combo.addItem(su['unit_name'], su['conversion_factor'])
            update_price()

        def update_price():
            item_id = item_combo.currentData()
            if item_id:
                item = next((i for i in items if i['id']==item_id), None)
                if item:
                    price = item.get('selling_price',0) if self.inv_type=='sale' else item.get('purchase_price',0)
                    price_spin.setValue(price)

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
            item = next((i for i in items if i['id']==item_id), None)
            if not item:
                return
            qty = qty_spin.value()
            factor = unit_combo.currentData()
            unit_name = unit_combo.currentText()
            base_qty = qty * factor
            price = price_spin.value()
            total = base_qty * price   # السعر دائماً للوحدة الأساسية
            line_data = {
                'item_id': item_id,
                'item_name': item['name'],
                'quantity': qty,
                'unit': unit_name if unit_name != "الوحدة الأساسية" else item.get('unit', ''),
                'conversion_factor': factor,
                'base_qty': base_qty,
                'unit_price': price,
                'total': total
            }
            self.lines.append(line_data)
            unit_display = f" ({line_data['unit']})" if line_data['unit'] else ""
            self.lines_list.addItem(f"{item['name']}{unit_display} - {qty} × {format_currency(price)} = {format_currency(total)}")
            self.update_total()
            dialog.accept()

        add_btn.clicked.connect(on_add)
        cancel_btn.clicked.connect(dialog.reject)
        dialog.exec()

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
            self.paid_spin.setValue(total)

    def on_save(self):
        if not self.lines:
            show_toast("أضف بنداً واحداً على الأقل", "error", self)
            return
        total = sum(line['total'] for line in self.lines)
        paid = self.paid_spin.value()
        if paid > total:
            paid = total
        entity_id = self.entity_combo.currentData()
        reference = self.ref_edit.toPlainText().strip()
        if not reference:
            reference = db.get_next_invoice_reference(self.inv_type)
        data = {
            'type': self.inv_type,
            'customer_id': entity_id if self.inv_type=='sale' else None,
            'supplier_id': entity_id if self.inv_type=='purchase' else None,
            'date': self.date_edit.date().toString("yyyy-MM-dd"),
            'reference': reference,
            'notes': self.notes_edit.toPlainText().strip(),
            'total': total,
            'paid_amount': paid,
            'lines': self.lines
        }
        try:
            db.create_invoice(data)
            show_toast("تم حفظ الفاتورة", "success", self)
            self.accept()
        except Exception as e:
            show_toast(str(e), "error", self)

    def print_invoice(self):
        from PyQt5.QtGui import QTextDocument
        from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog
        html = f"""
        <html dir="rtl">
        <head><meta charset="UTF-8"><title>فاتورة</title></head>
        <body style="font-family: 'Tajawal', sans-serif; padding:20px;">
        <h2>الراجحي للمحاسبة</h2>
        <p><strong>فاتورة {self.ref_edit.toPlainText() or 'جديدة'}</strong><br>
        التاريخ: {self.date_edit.date().toString("yyyy-MM-dd")}<br>
        {'العميل: ' + (self.entity_combo.currentText().split(' (')[0] if self.entity_combo.currentData() else 'نقدي') if self.inv_type=='sale' else 'المورد: ' + (self.entity_combo.currentText().split(' (')[0] if self.entity_combo.currentData() else 'نقدي')}</p>
        <table border="1" cellpadding="5" style="border-collapse:collapse; width:100%;">
        <thead><tr><th>المادة</th><th>الكمية</th><th>الوحدة</th><th>السعر</th><th>الإجمالي</th></tr></thead>
        <tbody>
        """
        for line in self.lines:
            html += f"<tr><td style='font-weight:bold'>{line['item_name']}</td><td>{line['quantity']}</td><td>{line.get('unit', '')}</td><td>{format_currency(line['unit_price'])}浏<td>{format_currency(line['total'])}浏</tr>"
        total = sum(line['total'] for line in self.lines)
        paid = self.paid_spin.value()
        html += f"""
        </tbody>
        </table>
        <p><strong>الإجمالي:</strong> {format_currency(total)}<br>
        <strong>المدفوع:</strong> {format_currency(paid)}<br>
        <strong>المتبقي:</strong> {format_currency(total-paid)}</p>
        <p>شكراً للتعامل معنا</p>
        </body></html>
        """
        doc = QTextDocument()
        doc.setHtml(html)
        printer = QPrinter(QPrinter.HighResolution)
        preview = QPrintPreviewDialog(printer, self)
        preview.paintRequested.connect(lambda p: doc.print(p))
        preview.exec()

    def add_customer_supplier(self):
        from views_pyqt5.customers_suppliers import CustomersSuppliersWidget
        dialog = QDialog(self)
        dialog.setWindowTitle(f"إضافة {'عميل' if self.inv_type=='sale' else 'مورد'} جديد")
        dialog.setModal(True)
        layout = QVBoxLayout(dialog)
        widget = CustomersSuppliersWidget(dialog, 'customer' if self.inv_type=='sale' else 'supplier')
        def on_close():
            if self.inv_type == 'sale':
                self.customers = db.get_customers()
                self.entity_combo.clear()
                self.entity_combo.addItem("نقدي", None)
                for c in self.customers:
                    self.entity_combo.addItem(f"{c['name']} (الرصيد: {format_currency(c['balance'])})", c['id'])
            else:
                self.suppliers = db.get_suppliers()
                self.entity_combo.clear()
                self.entity_combo.addItem("نقدي", None)
                for s in self.suppliers:
                    self.entity_combo.addItem(f"{s['name']} (الرصيد: {format_currency(s['balance'])})", s['id'])
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
