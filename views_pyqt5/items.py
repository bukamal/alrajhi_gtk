# views_pyqt5/items.py
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QPoint, QTimer
from PyQt5.QtGui import QColor, QPixmap, QFont
from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog
from database import item_dao, category_dao, inventory_dao, exchange_rate_dao
from database.utils import storage_to_decimal
from utils_pyqt5 import format_currency, show_toast
from config import get_currency_settings, get_current_currency_symbol
from views_pyqt5.base_table_model import BaseTableModel
from views_pyqt5.centered_dialog import CenteredDialog, show_centered_messagebox
from views_pyqt5.modern_table import ModernTableView
from views_pyqt5.base_widget import BaseWidget
import uuid
import barcode
from barcode.writer import ImageWriter
import tempfile
import os
import shutil

PRINT_AVAILABLE = True

class ItemsWidget(BaseWidget):
    entity_name = "المادة"
    search_placeholder = "بحث عن مادة..."
    headers = ["#", "الاسم", "الكمية", "الوحدة الأساسية", "سعر البيع", "قيمة المخزون", "الباركود"]
    has_export = True
    has_print = True
    has_pagination = True
    page_size = 50
    extra_buttons = [
        ("📊 كشف حركة", "show_movement", "btn_movement"),
        ("⚡ تعديل سريع", "quick_edit", "btn_quick_edit"),
        ("🖨️ طباعة باركود", "print_barcode", "btn_print_barcode"),
    ]

    def __init__(self, parent=None):
        self.category_filter = QComboBox()
        self.type_filter = QComboBox()
        self.current_item_obj = None
        super().__init__(parent)
        self.init_extra_filters()
        self.load_categories()

    def init_extra_filters(self):
        filter_layout = QHBoxLayout()
        self.category_filter.addItem("جميع التصنيفات", None)
        filter_layout.addWidget(QLabel("التصنيف:"))
        filter_layout.addWidget(self.category_filter)

        self.type_filter.addItem("جميع الأنواع", None)
        self.type_filter.addItem("مخزون", "مخزون")
        self.type_filter.addItem("منتج نهائي", "منتج نهائي")
        self.type_filter.addItem("خدمة", "خدمة")
        filter_layout.addWidget(QLabel("النوع:"))
        filter_layout.addWidget(self.type_filter)
        filter_layout.addStretch()
        self.layout.insertLayout(2, filter_layout)

        self.category_filter.currentIndexChanged.connect(self.refresh)
        self.type_filter.currentIndexChanged.connect(self.refresh)

    def load_categories(self):
        categories = category_dao.get_all()
        self.category_filter.clear()
        self.category_filter.addItem("جميع التصنيفات", None)
        for c in categories:
            self.category_filter.addItem(c['name'], c['id'])

    def get_total_count(self, search=None):
        return item_dao.get_count(search)

    def fetch_data(self, search=None, limit=None, offset=None):
        category_id = self.category_filter.currentData() if self.category_filter else None
        item_type = self.type_filter.currentData() if self.type_filter else None
        items = item_dao.get_items(search=search, limit=limit, offset=offset)
        if items is None:
            return []
        filtered = []
        for it in items:
            if category_id and it.category_id != category_id:
                continue
            if item_type and it.item_type != item_type:
                continue
            filtered.append(it)
        return filtered

    def prepare_table_data(self, items):
        settings = get_currency_settings()
        data = []
        for it in items:
            data.append([
                it.id,
                it.name,
                it.available,
                it.unit,
                format_currency(it.selling_price, settings),
                format_currency(it.total_value, settings),
                it.barcode or ''
            ])
        return data

    def set_action_buttons_enabled(self, enabled):
        super().set_action_buttons_enabled(enabled)
        if enabled and self.current_id:
            item = self.get_current_item_object()
            self.btn_print_barcode.setEnabled(bool(item and item.barcode))
        else:
            self.btn_print_barcode.setEnabled(False)

    def get_current_item_object(self):
        if not self.current_id:
            return None
        if self.current_item_obj and self.current_item_obj.id == self.current_id:
            return self.current_item_obj
        items = item_dao.get_items()
        for it in items:
            if it.id == self.current_id:
                self.current_item_obj = it
                return it
        return None

    def show_movement(self):
        if not self.current_id:
            show_toast("لم يتم تحديد مادة", "error", self)
            return
        item = self.get_current_item_object()
        if not item:
            show_toast("المادة غير موجودة", "error", self)
            return
        dialog = CenteredDialog(self)
        dialog.setWindowTitle(f"كشف حركة المادة - {item.name}")
        dialog.resize(700, 500)
        layout = QVBoxLayout(dialog)

        movements = inventory_dao.get_movements(self.current_id)
        if not movements:
            label = QLabel("لا توجد حركات لهذه المادة")
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)
        else:
            html = f"""
            <div style="text-align: center;">
                <h3>كشف حركة المادة: {item.name}</h3>
                <hr>
            </div>
            <table style="width:100%; border-collapse:collapse;">
                <thead>
                    <tr style="background-color:#34495e; color:white;">
                        <th>التاريخ</th><th>نوع الحركة</th><th>الكمية</th><th>سعر الوحدة</th><th>المرجع</th>
                    </tr>
                </thead>
                <tbody>
            """
            for r in movements:
                movement_type = "شراء" if r['movement_type'] == 'purchase' else "بيع" if r['movement_type'] == 'sale' else "تعديل"
                qty = r['quantity']
                unit_cost = r['unit_cost']
                ref = r['reference_id'] or '-'
                html += f"""
                    <tr style="border-bottom:1px solid #ddd;">
                        <td style="padding:8px;">{r['movement_date']}浏
                        <td style="padding:8px;">{movement_type}浏
                        <td style="padding:8px;">{qty}浏
                        <td style="padding:8px;">{format_currency(unit_cost)}浏
                        <td style="padding:8px;">{ref}浏
                    </tr>
                """
            html += "</tbody></tr>"
            text_edit = QLabel(html)
            text_edit.setWordWrap(True)
            text_edit.setTextFormat(Qt.RichText)
            layout.addWidget(text_edit)

        close_btn = QPushButton("إغلاق")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        dialog.exec()

    def quick_edit(self):
        if not self.current_id:
            show_toast("لم يتم تحديد مادة", "error", self)
            return
        item = self.get_current_item_object()
        if not item:
            show_toast("لم يتم العثور على المادة", "error", self)
            return

        dialog = CenteredDialog(self)
        dialog.setWindowTitle(f"تعديل سريع - {item.name}")
        dialog.resize(350, 200)
        layout = QFormLayout(dialog)
        selling_spin = QDoubleSpinBox()
        selling_spin.setRange(0, 999999)
        selling_spin.setDecimals(2)
        selling_spin.setValue(float(item.selling_price))
        layout.addRow("سعر البيع الجديد:", selling_spin)
        qty_spin = QDoubleSpinBox()
        qty_spin.setRange(0, 999999)
        qty_spin.setDecimals(2)
        qty_spin.setValue(float(item.quantity))
        layout.addRow("الكمية الجديدة:", qty_spin)
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("حفظ")
        cancel_btn = QPushButton("إلغاء")
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

        def on_save():
            update_data = {
                'name': item.name,
                'category_id': item.category_id,
                'item_type': item.item_type,
                'purchase_price': item.purchase_price,
                'selling_price': selling_spin.value(),
                'quantity': qty_spin.value(),
                'unit': item.unit,
                'average_cost': item.average_cost,
                'barcode': item.barcode
            }
            try:
                item_dao.update(self.current_id, update_data)
                show_toast("تم التحديث بنجاح", "success", self)
                dialog.accept()
                self.refresh()
            except Exception as e:
                show_toast(str(e), "error", self)

        save_btn.clicked.connect(on_save)
        cancel_btn.clicked.connect(dialog.reject)
        dialog.exec()

    def print_barcode(self):
        if not self.current_id:
            show_toast("لم يتم تحديد مادة", "error", self)
            return
        item = self.get_current_item_object()
        if not item:
            show_toast("المادة غير موجودة", "error", self)
            return
        barcode_text = item.barcode
        if not barcode_text:
            show_toast("هذه المادة ليس لها باركود", "error", self)
            return
        try:
            code128 = barcode.get_barcode_class('code128')
            barcode_obj = code128(barcode_text, writer=ImageWriter())
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                filename = tmp.name
            barcode_obj.save(filename)
            if PRINT_AVAILABLE:
                printer = QPrinter(QPrinter.HighResolution)
                preview = QPrintPreviewDialog(printer, self)
                preview.paintRequested.connect(lambda p: self._print_barcode_image(p, filename, item.name))
                preview.exec()
            else:
                save_path, _ = QFileDialog.getSaveFileName(self, "حفظ الباركود", f"barcode_{item.name}.png", "PNG (*.png)")
                if save_path:
                    shutil.copy(filename, save_path)
                    show_toast(f"تم حفظ الباركود إلى {save_path}", "success", self)
            QTimer.singleShot(5000, lambda: os.unlink(filename) if os.path.exists(filename) else None)
        except Exception as e:
            show_toast(f"خطأ في إنشاء الباركود: {str(e)}", "error", self)

    def _print_barcode_image(self, printer, image_path, item_name):
        try:
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                return
            page_rect = printer.pageRect()
            scaled_pixmap = pixmap.scaled(page_rect.width() * 0.6, page_rect.height() * 0.3, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            x = (page_rect.width() - scaled_pixmap.width()) / 2
            y = (page_rect.height() - scaled_pixmap.height()) / 2
            painter = QPainter(printer)
            painter.drawPixmap(int(x), int(y), scaled_pixmap)
            painter.setFont(QFont("Tajawal", 12))
            painter.drawText(page_rect, Qt.AlignCenter | Qt.AlignBottom, item_name)
            painter.end()
        except Exception as e:
            show_toast(f"خطأ في الطباعة: {str(e)}", "error", self)

    def delete_item(self, item_id):
        item_dao.delete(item_id)

    def open_dialog(self, is_edit=False, item_id=None, dialog_parent=None):
        parent_for_dialog = dialog_parent if dialog_parent else self
        dialog = CenteredDialog(parent_for_dialog)
        dialog.setWindowTitle("تعديل مادة" if is_edit else "إضافة مادة جديدة")
        dialog.setLayoutDirection(Qt.RightToLeft)
        dialog.resize(700, 600)
        main_layout = QVBoxLayout(dialog)

        # إنشاء تبويبات (Tabs) لتقسيم المحتوى
        tabs = QTabWidget()
        main_layout.addWidget(tabs)

        # ========== التبويب الأول: المعلومات الأساسية ==========
        basic_tab = QWidget()
        basic_layout = QFormLayout(basic_tab)
        basic_layout.setSpacing(8)
        basic_layout.setContentsMargins(12, 12, 12, 12)

        currency_symbol = get_current_currency_symbol()

        name_edit = QLineEdit()
        name_edit.setToolTip("اسم المادة كما سيظهر في الفواتير والتقارير")
        basic_layout.addRow("اسم المادة:", name_edit)

        barcode_layout = QHBoxLayout()
        barcode_edit = QLineEdit()
        barcode_edit.setPlaceholderText("رمز الباركود (اختياري)")
        barcode_edit.setToolTip("يمكنك إدخال باركود يدوياً أو الضغط على زر 'إنشاء عشوائي' لتوليد رقم عشوائي")
        generate_barcode_btn = QPushButton("إنشاء عشوائي")
        generate_barcode_btn.setFixedWidth(100)
        generate_barcode_btn.setToolTip("توليد رقم باركود عشوائي (13 رقم)")
        generate_barcode_btn.clicked.connect(lambda: barcode_edit.setText(str(uuid.uuid4().int)[:13]))
        barcode_layout.addWidget(barcode_edit)
        barcode_layout.addWidget(generate_barcode_btn)
        basic_layout.addRow("الباركود:", barcode_layout)

        cat_layout = QHBoxLayout()
        cat_combo = QComboBox()
        cat_combo.addItem("بدون تصنيف", None)
        cat_combo.setToolTip("اختر التصنيف المناسب للمادة (مثل: إلكترونيات، أدوات مكتبية...)")
        categories = category_dao.get_all()
        for c in categories:
            cat_combo.addItem(c['name'], c['id'])
        cat_layout.addWidget(cat_combo)
        add_cat_btn = QPushButton("+")
        add_cat_btn.setFixedSize(30, 30)
        add_cat_btn.setToolTip("إضافة تصنيف جديد")
        cat_layout.addWidget(add_cat_btn)
        basic_layout.addRow("التصنيف:", cat_layout)

        type_combo = QComboBox()
        type_combo.addItems(["مخزون", "منتج نهائي", "خدمة"])
        type_combo.setToolTip("تحديد نوع المادة:\n- مخزون: مواد يتم تتبع كميتها\n- منتج نهائي: مواد جاهزة للبيع\n- خدمة: خدمات غير ملموسة (بدون مخزون)")
        basic_layout.addRow("نوع المادة:", type_combo)

        unit_edit = QLineEdit()
        unit_edit.setPlaceholderText("مثال: قطعة، كيلو، متر، علبة...")
        unit_edit.setToolTip("الوحدة الأساسية للمادة (تستخدم في المخزون والفواتير)")
        basic_layout.addRow("الوحدة الأساسية:", unit_edit)

        purchase_spin = QDoubleSpinBox()
        purchase_spin.setRange(0, 999999)
        purchase_spin.setDecimals(2)
        purchase_spin.setPrefix(f"{currency_symbol} ")
        purchase_spin.setToolTip("سعر شراء المادة (يستخدم لحساب تكلفة المخزون)")
        basic_layout.addRow("سعر الشراء:", purchase_spin)

        selling_spin = QDoubleSpinBox()
        selling_spin.setRange(0, 999999)
        selling_spin.setDecimals(2)
        selling_spin.setPrefix(f"{currency_symbol} ")
        selling_spin.setToolTip("سعر بيع المادة للعملاء")
        basic_layout.addRow("سعر البيع:", selling_spin)

        qty_spin = QDoubleSpinBox()
        qty_spin.setRange(0, 999999)
        qty_spin.setDecimals(2)
        qty_spin.setToolTip("الكمية الافتتاحية للمادة في المخزون (للمواد المخزنية فقط)")
        basic_layout.addRow("الكمية الافتتاحية:", qty_spin)

        tabs.addTab(basic_tab, "📋 معلومات أساسية")

        # ========== التبويب الثاني: الوحدات الفرعية ==========
        units_tab = QWidget()
        units_layout = QVBoxLayout(units_tab)
        units_layout.setSpacing(8)
        units_layout.setContentsMargins(12, 12, 12, 12)

        units_group = QGroupBox("الوحدات الفرعية (للتحويل في الفواتير)")
        units_group.setToolTip("إضافة وحدات بديلة للمادة (مثل: كرتونة = 12 قطعة) لتسهيل إدخال الفواتير بوحدات مختلفة")
        group_layout = QVBoxLayout(units_group)
        units_list = QListWidget()
        units_list.setToolTip("الوحدات الفرعية المضافة مع معامل التحويل إلى الوحدة الأساسية")
        group_layout.addWidget(units_list)

        btn_units_layout = QHBoxLayout()
        btn_add_unit = QPushButton("➕ إضافة وحدة فرعية")
        btn_add_unit.setToolTip("إضافة وحدة قياس بديلة (مثال: كرتونة، طبق، دستة)")
        btn_remove_unit = QPushButton("🗑 حذف الوحدة المحددة")
        btn_remove_unit.setToolTip("حذف الوحدة الفرعية المحددة")
        btn_units_layout.addWidget(btn_add_unit)
        btn_units_layout.addWidget(btn_remove_unit)
        group_layout.addLayout(btn_units_layout)
        units_layout.addWidget(units_group)

        stats_label = QLabel()
        stats_label.setWordWrap(True)
        stats_label.setVisible(False)
        stats_label.setToolTip("إحصائيات حول حركات المادة (تظهر فقط عند التعديل)")
        units_layout.addWidget(stats_label)

        tabs.addTab(units_tab, "🔄 الوحدات الفرعية")

        # ========== التبويب الثالث: إحصائيات (يظهر فقط عند التعديل) ==========
        stats_tab = QWidget()
        stats_tab_layout = QVBoxLayout(stats_tab)
        stats_details_label = QLabel()
        stats_details_label.setWordWrap(True)
        stats_details_label.setAlignment(Qt.AlignCenter)
        stats_tab_layout.addWidget(stats_details_label)
        # سيتم إضافة هذا التبويب فقط إذا كان في وضع التعديل ولدينا بيانات

        # تحميل البيانات إذا كان وضع تعديل
        if is_edit and item_id:
            item = item_dao.get_by_id(item_id)
            if item:
                name_edit.setText(item.name)
                barcode_edit.setText(item.barcode or '')
                idx = cat_combo.findData(item.category_id)
                if idx >= 0:
                    cat_combo.setCurrentIndex(idx)
                type_combo.setCurrentText(item.item_type)
                unit_edit.setText(item.unit)
                purchase_spin.setValue(float(item.purchase_price))
                selling_spin.setValue(float(item.selling_price))
                qty_spin.setValue(float(item.quantity))
                subunits = item_dao.get_units(item_id)
                for su in subunits:
                    units_list.addItem(f"{su.unit_name} : {su.conversion_factor}")
                stats_text = f"""
                <b>إجمالي الكمية المشتراة:</b> {item.purchase_qty}<br>
                <b>إجمالي الكمية المباعة:</b> {item.sale_qty}<br>
                <b>عدد مرات الشراء:</b> {item.purchase_count}<br>
                <b>عدد مرات البيع:</b> {item.sale_count}<br>
                <b>آخر شراء:</b> {item.last_purchase_date or '-'}<br>
                <b>آخر بيع:</b> {item.last_sale_date or '-'}<br>
                <b>متوسط سعر الشراء:</b> {format_currency(item.average_cost)}
                """
                stats_label.setText(stats_text)
                stats_label.setVisible(True)
                stats_details_label.setText(stats_text)
                tabs.addTab(stats_tab, "📊 إحصائيات")

        # دوال إضافة/حذف الوحدات الفرعية
        def add_subunit_dialog():
            sub_dialog = CenteredDialog(dialog)
            sub_dialog.setWindowTitle("إضافة وحدة فرعية")
            sub_dialog.setLayoutDirection(Qt.RightToLeft)
            sub_dialog.resize(350, 180)
            sub_layout = QFormLayout(sub_dialog)
            unit_name_edit = QLineEdit()
            unit_name_edit.setPlaceholderText("مثال: كرتونة، طبق، دستة...")
            unit_name_edit.setToolTip("اسم الوحدة الفرعية (مثل: كرتونة، علبة، طبق)")
            sub_layout.addRow("اسم الوحدة الفرعية:", unit_name_edit)
            factor_spin = QDoubleSpinBox()
            factor_spin.setRange(0.001, 999999)
            factor_spin.setValue(1.0)
            factor_spin.setToolTip("كم وحدة أساسية تعادل هذه الوحدة الفرعية؟\nمثال: 1 كرتونة = 12 قطعة ← العامل = 12")
            sub_layout.addRow("عامل التحويل (1 فرعية = ? أساسية):", factor_spin)
            btn_sublayout = QHBoxLayout()
            add_btn = QPushButton("إضافة")
            cancel_btn = QPushButton("إلغاء")
            btn_sublayout.addWidget(add_btn)
            btn_sublayout.addWidget(cancel_btn)
            sub_layout.addRow(btn_sublayout)

            def on_add():
                unit_name = unit_name_edit.text().strip()
                if not unit_name:
                    show_toast("اسم الوحدة مطلوب", "error", sub_dialog)
                    return
                factor = factor_spin.value()
                if factor <= 0:
                    show_toast("عامل التحويل يجب أن يكون أكبر من صفر", "error", sub_dialog)
                    return
                units_list.addItem(f"{unit_name} : {factor}")
                sub_dialog.accept()
            add_btn.clicked.connect(on_add)
            cancel_btn.clicked.connect(sub_dialog.reject)
            sub_dialog.exec()

        def remove_subunit():
            row = units_list.currentRow()
            if row >= 0:
                units_list.takeItem(row)

        btn_add_unit.clicked.connect(add_subunit_dialog)
        btn_remove_unit.clicked.connect(remove_subunit)

        # إضافة تصنيف جديد
        def add_new_category():
            cat_dialog = CenteredDialog(dialog)
            cat_dialog.setWindowTitle("إضافة تصنيف جديد")
            cat_dialog.setLayoutDirection(Qt.RightToLeft)
            cat_dialog.resize(300, 120)
            cat_layout_form = QFormLayout(cat_dialog)
            cat_name_edit = QLineEdit()
            cat_name_edit.setToolTip("اسم التصنيف الجديد (مثل: إلكترونيات، أدوات مكتبية)")
            cat_layout_form.addRow("اسم التصنيف:", cat_name_edit)
            btn_cat_layout = QHBoxLayout()
            save_cat_btn = QPushButton("حفظ")
            cancel_cat_btn = QPushButton("إلغاء")
            btn_cat_layout.addWidget(save_cat_btn)
            btn_cat_layout.addWidget(cancel_cat_btn)
            cat_layout_form.addRow(btn_cat_layout)

            def save_category():
                cat_name = cat_name_edit.text().strip()
                if not cat_name:
                    show_centered_messagebox(cat_dialog, "خطأ", "اسم التصنيف مطلوب", QMessageBox.Warning)
                    return
                try:
                    new_id = category_dao.add(cat_name)
                    cat_combo.addItem(cat_name, new_id)
                    cat_combo.setCurrentIndex(cat_combo.count()-1)
                    cat_dialog.accept()
                    show_toast("تمت إضافة التصنيف", "success", dialog)
                except Exception as e:
                    show_centered_messagebox(cat_dialog, "خطأ", str(e), QMessageBox.Critical)
            save_cat_btn.clicked.connect(save_category)
            cancel_cat_btn.clicked.connect(cat_dialog.reject)
            cat_dialog.exec()

        add_cat_btn.clicked.connect(add_new_category)

        # أزرار الحفظ والإلغاء
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("حفظ")
        save_btn.setObjectName("primary")
        save_btn.setToolTip("حفظ المادة وإغلاق النافذة")
        cancel_btn = QPushButton("إلغاء")
        cancel_btn.setToolTip("إلغاء التغييرات وإغلاق النافذة")
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        main_layout.addLayout(btn_layout)

        def on_save():
            name = name_edit.text().strip()
            if not name:
                show_centered_messagebox(dialog, "خطأ", "اسم المادة مطلوب", QMessageBox.Warning)
                return
            barcode = barcode_edit.text().strip() or None
            cat_id = cat_combo.currentData()
            item_type = type_combo.currentText()
            unit = unit_edit.text().strip()
            purchase_price = purchase_spin.value()
            selling_price = selling_spin.value()
            qty = qty_spin.value()

            data = {
                'name': name,
                'barcode': barcode,
                'category_id': cat_id,
                'item_type': item_type,
                'purchase_price': purchase_price,
                'selling_price': selling_price,
                'quantity': qty,
                'unit': unit,
                'average_cost': purchase_price
            }
            try:
                if is_edit:
                    item_dao.update(item_id, data)
                    item_dao.clear_units(item_id)
                    for i in range(units_list.count()):
                        item_text = units_list.item(i).text()
                        parts = item_text.split(' : ')
                        if len(parts) == 2:
                            unit_name = parts[0]
                            factor = float(parts[1])
                            item_dao.add_unit(item_id, unit_name, factor)
                    show_toast("تم التعديل", "success", dialog)
                else:
                    new_id = item_dao.add(data)
                    for i in range(units_list.count()):
                        item_text = units_list.item(i).text()
                        parts = item_text.split(' : ')
                        if len(parts) == 2:
                            unit_name = parts[0]
                            factor = float(parts[1])
                            item_dao.add_unit(new_id, unit_name, factor)
                    show_toast("تمت الإضافة", "success", dialog)
                dialog.accept()
                self.refresh()
                self.load_categories()
            except Exception as e:
                show_centered_messagebox(dialog, "خطأ", str(e), QMessageBox.Critical)

        save_btn.clicked.connect(on_save)
        cancel_btn.clicked.connect(dialog.reject)
        dialog.exec()
