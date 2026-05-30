# views_pyqt5/vouchers.py
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QTableView,
                             QHeaderView, QMessageBox, QDialog, QFormLayout, QLabel, QComboBox, QDateEdit, QDoubleSpinBox)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor
from database import voucher_dao, customer_dao, supplier_dao, invoice_dao, reporting_dao
from utils_pyqt5 import format_currency, show_toast
from views_pyqt5.base_table_model import BaseTableModel
from views_pyqt5.centered_dialog import CenteredDialog
from views_pyqt5.modern_table import ModernTableView
from views_pyqt5.base_widget import BaseWidget


class VouchersWidget(BaseWidget):
    entity_name = "سند"
    search_placeholder = "بحث عن سند..."
    headers = ["#", "النوع", "التاريخ", "المرجع", "الجهة", "المبلغ"]
    has_delete = True
    has_add = True
    has_export = True
    has_print = True
    has_pagination = True
    page_size = 50
    extra_buttons = [
        ("🖨️ طباعة إيصال", "print_receipt", "btn_print"),
        ("📄 كشف حساب الجهة", "show_entity_statement", "btn_statement"),
        ("🧾 فتح الفاتورة المرتبطة", "open_related_invoice", "btn_invoice"),
    ]

    def __init__(self, parent=None):
        self.type_filter = QComboBox()
        self.start_date = QDateEdit()
        self.end_date = QDateEdit()
        self.entity_filter = QComboBox()
        self.current_voucher_type = None
        self.current_entity_id = None
        self.current_invoice_id = None
        super().__init__(parent)
        self.init_filters()
        self.load_entities()

    def init_filters(self):
        filter_layout = QHBoxLayout()
        self.type_filter.addItem("جميع الأنواع", None)
        self.type_filter.addItem("قبض", "receipt")
        self.type_filter.addItem("دفع", "payment")
        self.type_filter.addItem("مصروف", "expense")
        self.type_filter.currentIndexChanged.connect(self.refresh)
        filter_layout.addWidget(QLabel("النوع:"))
        filter_layout.addWidget(self.type_filter)

        filter_layout.addWidget(QLabel("من تاريخ:"))
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.start_date.setCalendarPopup(True)
        self.start_date.dateChanged.connect(self.refresh)
        filter_layout.addWidget(self.start_date)

        filter_layout.addWidget(QLabel("إلى تاريخ:"))
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        self.end_date.dateChanged.connect(self.refresh)
        filter_layout.addWidget(self.end_date)

        filter_layout.addWidget(QLabel("الجهة:"))
        self.entity_filter.addItem("الكل", None)
        self.entity_filter.currentIndexChanged.connect(self.refresh)
        filter_layout.addWidget(self.entity_filter)

        filter_layout.addStretch()
        self.layout.insertLayout(2, filter_layout)

    def load_entities(self):
        customers = customer_dao.get_all()
        suppliers = supplier_dao.get_all()
        self.entity_filter.clear()
        self.entity_filter.addItem("الكل", None)
        for c in customers:
            self.entity_filter.addItem(f"عميل: {c.name}", ('customer', c.id))
        for s in suppliers:
            self.entity_filter.addItem(f"مورد: {s.name}", ('supplier', s.id))

    def get_total_count(self, search=None):
        vouchers = voucher_dao.get_all(search=search)
        if not vouchers:
            return 0
        vtype = self.type_filter.currentData()
        start_date = self.start_date.date().toString("yyyy-MM-dd")
        end_date = self.end_date.date().toString("yyyy-MM-dd")
        entity = self.entity_filter.currentData()
        entity_id = entity[1] if entity else None
        entity_type = entity[0] if entity else None
        filtered = 0
        for v in vouchers:
            if vtype and v['type'] != vtype:
                continue
            if v['date'] < start_date or v['date'] > end_date:
                continue
            if entity_id:
                if entity_type == 'customer' and v.get('customer_id') != entity_id:
                    continue
                if entity_type == 'supplier' and v.get('supplier_id') != entity_id:
                    continue
            filtered += 1
        return filtered

    def fetch_data(self, search=None, limit=None, offset=None):
        vouchers = voucher_dao.get_all(search=search)
        if not vouchers:
            return []
        vtype = self.type_filter.currentData()
        start_date = self.start_date.date().toString("yyyy-MM-dd")
        end_date = self.end_date.date().toString("yyyy-MM-dd")
        entity = self.entity_filter.currentData()
        entity_id = entity[1] if entity else None
        entity_type = entity[0] if entity else None

        filtered = []
        for v in vouchers:
            if vtype and v['type'] != vtype:
                continue
            if v['date'] < start_date or v['date'] > end_date:
                continue
            if entity_id:
                if entity_type == 'customer' and v.get('customer_id') != entity_id:
                    continue
                if entity_type == 'supplier' and v.get('supplier_id') != entity_id:
                    continue
            filtered.append(v)
        if limit is not None and offset is not None:
            return filtered[offset:offset+limit]
        return filtered

    def prepare_table_data(self, items):
        customers = {c.id: c.name for c in customer_dao.get_all()}
        suppliers = {s.id: s.name for s in supplier_dao.get_all()}
        data = []
        self.row_colors = []
        for v in items:
            typ = "قبض" if v['type'] == 'receipt' else "دفع" if v['type'] == 'payment' else "مصروف"
            entity_name = ""
            if v.get('customer_id'):
                entity_name = customers.get(v['customer_id'], '')
            elif v.get('supplier_id'):
                entity_name = suppliers.get(v['supplier_id'], '')
            data.append([
                v['id'],
                typ,
                v['date'],
                v.get('reference', ''),
                entity_name,
                v['amount']
            ])
            if v['type'] == 'receipt':
                self.row_colors.append(QColor(220, 252, 231))
            elif v['type'] == 'payment':
                self.row_colors.append(QColor(254, 226, 226))
            else:
                self.row_colors.append(QColor(255, 237, 213))
        return data

    def after_refresh(self):
        for row, color in enumerate(self.row_colors):
            self.model.set_row_background(row, color)

    def on_selection_changed(self, selected, deselected):
        super().on_selection_changed(selected, deselected)
        if self.current_id:
            vouchers = voucher_dao.get_all()
            v = next((v for v in vouchers if v['id'] == self.current_id), None)
            if v:
                self.current_voucher_type = v['type']
                self.current_entity_id = v.get('customer_id') or v.get('supplier_id')
                self.current_invoice_id = v.get('invoice_id')
                self.btn_invoice.setEnabled(self.current_invoice_id is not None)
            else:
                self.current_voucher_type = None
                self.current_entity_id = None
                self.current_invoice_id = None
                self.btn_invoice.setEnabled(False)
        else:
            self.current_voucher_type = None
            self.current_entity_id = None
            self.current_invoice_id = None
            self.btn_invoice.setEnabled(False)

    def delete_item(self, item_id):
        voucher_dao.delete(item_id)

    def print_receipt(self):
        if not self.current_id:
            show_toast("لم يتم تحديد سند", "error", self)
            return
        vouchers = voucher_dao.get_all()
        v = next((v for v in vouchers if v['id'] == self.current_id), None)
        if not v:
            show_toast("لم يتم العثور على السند", "error", self)
            return
        from PyQt5.QtGui import QTextDocument
        from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog
        amount = format_currency(v['amount'])
        typ = "قبض" if v['type'] == 'receipt' else "دفع" if v['type'] == 'payment' else "مصروف"
        entity_name = ""
        if v.get('customer_id'):
            customers = customer_dao.get_all()
            c = next((c for c in customers if c.id == v['customer_id']), None)
            entity_name = c.name if c else ''
        elif v.get('supplier_id'):
            suppliers = supplier_dao.get_all()
            s = next((s for s in suppliers if s.id == v['supplier_id']), None)
            entity_name = s.name if s else ''
        html = f"""
        <!DOCTYPE html>
        <html dir="rtl">
        <head><meta charset="UTF-8"><title>إيصال سند</title>
        <style>
            body {{ font-family: 'Tajawal', sans-serif; padding: 20px; }}
            .header {{ text-align: center; margin-bottom: 20px; }}
            .content {{ border: 1px solid #ddd; padding: 15px; border-radius: 8px; }}
            .row {{ margin: 10px 0; }}
            .label {{ font-weight: bold; }}
        </style>
        </head>
        <body>
            <div class="header">
                <h2>نظام الراجحي للمحاسبة</h2>
                <h3>إيصال {typ}</h3>
            </div>
            <div class="content">
                <div class="row"><span class="label">التاريخ:</span> {v['date']}</div>
                <div class="row"><span class="label">المرجع:</span> {v.get('reference', '-')}</div>
                <div class="row"><span class="label">الجهة:</span> {entity_name}</div>
                <div class="row"><span class="label">المبلغ:</span> {amount}</div>
                <div class="row"><span class="label">الوصف:</span> {v.get('description', '-')}</div>
            </div>
            <div style="margin-top: 30px; text-align: center;">شكراً للتعامل معنا</div>
        </body>
        </html>
        """
        doc = QTextDocument()
        doc.setHtml(html)
        printer = QPrinter(QPrinter.HighResolution)
        preview = QPrintPreviewDialog(printer, self)
        preview.paintRequested.connect(lambda p: doc.print(p))
        preview.exec()

    def show_entity_statement(self):
        if not self.current_entity_id:
            show_toast("لا توجد جهة مرتبطة بهذا السند", "error", self)
            return
        if self.current_voucher_type in ('receipt', 'payment'):
            entity_type = 'customer' if self.current_voucher_type == 'receipt' else 'supplier'
        else:
            show_toast("هذا السند ليس مرتبطاً بعميل أو مورد", "error", self)
            return
        dialog = CenteredDialog(self)
        dialog.setWindowTitle(f"كشف حساب {'العميل' if entity_type=='customer' else 'المورد'}")
        dialog.resize(700, 500)
        layout = QVBoxLayout(dialog)
        if entity_type == 'customer':
            lines = reporting_dao.get_customer_statement(self.current_entity_id)
            title = "كشف حساب عميل"
        else:
            lines = reporting_dao.get_supplier_statement(self.current_entity_id)
            title = "كشف حساب مورد"
        if not lines:
            label = QLabel("لا توجد حركات لهذه الجهة")
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)
        else:
            html = f"""
            <div style="text-align: center;">
                <h3>{title}</h3>
                <hr>
            </div>
            <table style="width:100%; border-collapse:collapse;">
                <thead>
                    <tr style="background-color:#34495e; color:white;">
                        <th>التاريخ</th><th>الوصف</th><th>مدين</th><th>دائن</th><th>الرصيد</th>
                    </td>
                </thead>
                <tbody>
            """
            for l in lines:
                html += f"""
                    <tr style="border-bottom:1px solid #ddd;">
                        <td>{l['date']}浏
                        <td>{l['description']}浏
                        <td>{format_currency(l['debit'])}浏
                        <td>{format_currency(l['credit'])}浏
                        <td>{format_currency(l['balance'])}浏
                    </tr>
                """
            html += "</tbody></table>"
            text_edit = QLabel(html)
            text_edit.setWordWrap(True)
            text_edit.setTextFormat(Qt.RichText)
            layout.addWidget(text_edit)
        close_btn = QPushButton("إغلاق")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        dialog.exec()

    def open_related_invoice(self):
        if not self.current_invoice_id:
            show_toast("هذا السند غير مرتبط بفاتورة", "error", self)
            return
        inv = invoice_dao.get_by_id(self.current_invoice_id)
        if not inv:
            show_toast("الفاتورة غير موجودة", "error", self)
            return
        dialog = CenteredDialog(self)
        dialog.setWindowTitle(f"فاتورة {inv.reference}")
        dialog.resize(600, 500)
        layout = QVBoxLayout(dialog)
        inv_type = "بيع" if inv.type == 'sale' else "شراء"
        total = inv.total
        paid = inv.paid
        remaining = total - paid
        info_text = f"""
        <b>النوع:</b> {inv_type}<br>
        <b>التاريخ:</b> {inv.date}<br>
        <b>المرجع:</b> {inv.reference}<br>
        <b>الإجمالي:</b> {format_currency(total)}<br>
        <b>المدفوع:</b> {format_currency(paid)}<br>
        <b>المتبقي:</b> {format_currency(remaining)}<br>
        """
        label = QLabel(info_text)
        label.setWordWrap(True)
        layout.addWidget(label)
        close_btn = QPushButton("إغلاق")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        dialog.exec()

    def open_dialog(self, is_edit=False, item_id=None, dialog_parent=None):
        parent_for_dialog = dialog_parent if dialog_parent else self
        dialog = CenteredDialog(parent_for_dialog)
        dialog.setWindowTitle("تعديل سند" if is_edit else "إضافة سند جديد")
        dialog.setLayoutDirection(Qt.RightToLeft)
        dialog.resize(450, 420)
        layout = QFormLayout(dialog)
        layout.setSpacing(8)
        layout.setContentsMargins(12,12,12,12)

        type_combo = QComboBox()
        type_combo.addItems(["قبض", "دفع", "مصروف"])
        layout.addRow("النوع:", type_combo)

        cust_combo = QComboBox()
        cust_combo.addItem("اختر عميل", None)
        customers = customer_dao.get_all()
        for c in customers:
            cust_combo.addItem(f"{c.name} (الرصيد: {format_currency(c.balance)})", c.id)
        supp_combo = QComboBox()
        supp_combo.addItem("اختر مورد", None)
        suppliers = supplier_dao.get_all()
        for s in suppliers:
            supp_combo.addItem(f"{s.name} (الرصيد: {format_currency(s.balance)})", s.id)

        layout.addRow("العميل:", cust_combo)
        layout.addRow("المورد:", supp_combo)

        invoice_combo = QComboBox()
        invoice_combo.addItem("بدون فاتورة", None)
        layout.addRow("الفاتورة:", invoice_combo)

        amount_edit = QDoubleSpinBox()
        amount_edit.setRange(0, 99999999)
        amount_edit.setDecimals(2)
        layout.addRow("المبلغ:", amount_edit)

        date_edit = QDateEdit()
        date_edit.setDate(QDate.currentDate())
        layout.addRow("التاريخ:", date_edit)

        desc_edit = QLineEdit()
        desc_edit.setPlaceholderText("الوصف")
        layout.addRow("الوصف:", desc_edit)

        ref_edit = QLineEdit()
        ref_edit.setPlaceholderText("المرجع (يُترك فارغاً للتوليد التلقائي)")
        layout.addRow("المرجع:", ref_edit)

        warning_label = QLabel()
        warning_label.setStyleSheet("color: #f97316; font-weight: bold;")
        warning_label.setVisible(False)
        layout.addRow(warning_label)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("حفظ")
        save_btn.setObjectName("primary")
        cancel_btn = QPushButton("إلغاء")
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

        def update_entity_visibility():
            typ = type_combo.currentText()
            if typ == "قبض":
                cust_combo.setVisible(True)
                supp_combo.setVisible(False)
                layout.labelForField(cust_combo).setVisible(True)
                layout.labelForField(supp_combo).setVisible(False)
            elif typ == "دفع":
                cust_combo.setVisible(False)
                supp_combo.setVisible(True)
                layout.labelForField(cust_combo).setVisible(False)
                layout.labelForField(supp_combo).setVisible(True)
            else:
                cust_combo.setVisible(False)
                supp_combo.setVisible(False)
                layout.labelForField(cust_combo).setVisible(False)
                layout.labelForField(supp_combo).setVisible(False)

        def update_invoice_list():
            typ = type_combo.currentText()
            entity_id = None
            if typ == "قبض":
                entity_id = cust_combo.currentData()
            elif typ == "دفع":
                entity_id = supp_combo.currentData()
            if not entity_id:
                invoice_combo.clear()
                invoice_combo.addItem("بدون فاتورة", None)
                return
            invoices = invoice_dao.get_all()
            filtered = []
            for inv in invoices:
                if typ == "قبض" and inv.customer_id == entity_id and inv.type == 'sale' and inv.deleted_at is None:
                    filtered.append(inv)
                elif typ == "دفع" and inv.supplier_id == entity_id and inv.type == 'purchase' and inv.deleted_at is None:
                    filtered.append(inv)
            invoice_combo.clear()
            invoice_combo.addItem("بدون فاتورة", None)
            for inv in filtered:
                remaining = inv.total - inv.paid
                invoice_combo.addItem(f"{'بيع' if inv.type=='sale' else 'شراء'} {inv.reference} - {format_currency(inv.total)} (متبقي: {format_currency(remaining)})", inv.id)

        def update_amount_from_invoice():
            inv_id = invoice_combo.currentData()
            if not inv_id:
                return
            inv = invoice_dao.get_by_id(inv_id)
            if inv:
                remaining = inv.total - inv.paid
                amount_edit.setValue(remaining)
                check_balance()

        def check_balance():
            typ = type_combo.currentText()
            amount = amount_edit.value()
            if amount <= 0:
                warning_label.setVisible(False)
                return
            balance = 0
            entity_name = ""
            if typ == "قبض":
                cust_id = cust_combo.currentData()
                if cust_id:
                    cust = next((c for c in customers if c.id == cust_id), None)
                    if cust:
                        balance = cust.balance
                        entity_name = cust.name
            elif typ == "دفع":
                supp_id = supp_combo.currentData()
                if supp_id:
                    supp = next((s for s in suppliers if s.id == supp_id), None)
                    if supp:
                        balance = supp.balance
                        entity_name = supp.name
            if amount > balance:
                warning_label.setText(f"⚠️ المبلغ يتجاوز رصيد {entity_name} الحالي ({format_currency(balance)}). سيتم تسجيل دفعة مقدمة.")
                warning_label.setVisible(True)
            else:
                warning_label.setVisible(False)

        type_combo.currentTextChanged.connect(update_entity_visibility)
        type_combo.currentTextChanged.connect(update_invoice_list)
        type_combo.currentTextChanged.connect(check_balance)
        cust_combo.currentIndexChanged.connect(update_invoice_list)
        cust_combo.currentIndexChanged.connect(check_balance)
        supp_combo.currentIndexChanged.connect(update_invoice_list)
        supp_combo.currentIndexChanged.connect(check_balance)
        invoice_combo.currentIndexChanged.connect(update_amount_from_invoice)
        amount_edit.valueChanged.connect(check_balance)
        update_entity_visibility()

        if is_edit and item_id:
            vouchers = voucher_dao.get_all()
            v = next((v for v in vouchers if v['id'] == item_id), None)
            if v:
                type_combo.setCurrentText("قبض" if v['type'] == 'receipt' else "دفع" if v['type'] == 'payment' else "مصروف")
                if v.get('customer_id'):
                    idx = cust_combo.findData(v['customer_id'])
                    if idx >= 0:
                        cust_combo.setCurrentIndex(idx)
                if v.get('supplier_id'):
                    idx = supp_combo.findData(v['supplier_id'])
                    if idx >= 0:
                        supp_combo.setCurrentIndex(idx)
                amount_edit.setValue(v['amount'])
                date_edit.setDate(QDate.fromString(v['date'], "yyyy-MM-dd"))
                desc_edit.setText(v.get('description', ''))
                ref_edit.setText(v.get('reference', ''))
                if v.get('invoice_id'):
                    update_invoice_list()
                    inv_idx = invoice_combo.findData(v['invoice_id'])
                    if inv_idx >= 0:
                        invoice_combo.setCurrentIndex(inv_idx)

        def on_save():
            typ = type_combo.currentText()
            if typ == "قبض":
                cust_id = cust_combo.currentData()
                if not cust_id:
                    show_toast("يرجى اختيار عميل", "error", dialog)
                    return
                supp_id = None
            elif typ == "دفع":
                supp_id = supp_combo.currentData()
                if not supp_id:
                    show_toast("يرجى اختيار مورد", "error", dialog)
                    return
                cust_id = None
            else:
                cust_id = supp_id = None
            amount = amount_edit.value()
            if amount <= 0:
                show_toast("المبلغ يجب أن يكون أكبر من صفر", "error", dialog)
                return
            date_str = date_edit.date().toString("yyyy-MM-dd")
            description = desc_edit.text().strip()
            reference = ref_edit.text().strip()
            invoice_id = invoice_combo.currentData() or None
            voucher_type = 'receipt' if typ == "قبض" else 'payment' if typ == "دفع" else 'expense'
            data = {
                'type': voucher_type,
                'amount': amount,
                'date': date_str,
                'description': description,
                'reference': reference if reference else None,
                'customer_id': cust_id,
                'supplier_id': supp_id,
                'invoice_id': invoice_id
            }
            try:
                if is_edit and item_id:
                    voucher_dao.delete(item_id)
                    voucher_dao.add(data)
                    show_toast("تم التعديل بنجاح", "success", dialog)
                else:
                    voucher_dao.add(data)
                    show_toast("تمت الإضافة بنجاح", "success", dialog)
                dialog.accept()
                self.refresh()
            except Exception as e:
                show_toast(str(e), "error", dialog)

        save_btn.clicked.connect(on_save)
        cancel_btn.clicked.connect(dialog.reject)
        dialog.exec()
