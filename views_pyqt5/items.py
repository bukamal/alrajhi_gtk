# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QTableView,
                             QHeaderView, QMessageBox, QDialog, QFormLayout, QComboBox, QDoubleSpinBox,
                             QLabel, QGroupBox, QListWidget, QApplication, QMenu, QAction, QFileDialog)
from PyQt5.QtCore import Qt, QPoint, QTimer
from PyQt5.QtGui import QColor, QClipboard, QPixmap
from database import db, Session
from utils_pyqt5 import format_currency, show_toast
from config import get_currency_settings, get_current_currency_symbol
from views_pyqt5.base_table_model import BaseTableModel
from views_pyqt5.centered_dialog import CenteredDialog
from views_pyqt5.modern_table import ModernTableView
import uuid
import barcode
from barcode.writer import ImageWriter
import tempfile
import os

try:
    from PyQt5.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog
    from PyQt5.QtGui import QImage, QPainter
    PRINT_AVAILABLE = True
except:
    PRINT_AVAILABLE = False

class ItemsTableModel(BaseTableModel):
    def custom_data(self, index, role):
        if role == Qt.ForegroundRole and index.column() == 2:
            try:
                qty = self._data[index.row()][2]
                if isinstance(qty, (int, float)):
                    if qty <= 0:
                        return QColor(239, 68, 68)
                    elif qty < 5:
                        return QColor(249, 115, 22)
            except:
                pass
        return None

class ItemsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_item_id = None
        self.current_item_name = None
        self.init_ui()
        self.refresh()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(6,6,6,6)

        top = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("بحث عن مادة...")
        self.search_edit.textChanged.connect(self.refresh)
        top.addWidget(self.search_edit)

        self.category_filter = QComboBox()
        self.category_filter.addItem("جميع التصنيفات", None)
        top.addWidget(QLabel("التصنيف:"))
        top.addWidget(self.category_filter)

        self.type_filter = QComboBox()
        self.type_filter.addItem("جميع الأنواع", None)
        self.type_filter.addItem("مخزون", "مخزون")
        self.type_filter.addItem("منتج نهائي", "منتج نهائي")
        self.type_filter.addItem("خدمة", "خدمة")
        self.type_filter.currentIndexChanged.connect(self.refresh)
        top.addWidget(QLabel("النوع:"))
        top.addWidget(self.type_filter)

        self.add_btn = QPushButton("➕ إضافة مادة")
        self.add_btn.setObjectName("primary")
        self.add_btn.clicked.connect(self.add_item)
        top.addWidget(self.add_btn)

        self.delete_btn = QPushButton("🗑 حذف المحدد")
        self.delete_btn.setObjectName("danger")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self.delete_selected)
        top.addWidget(self.delete_btn)

        self.movement_btn = QPushButton("📊 كشف حركة")
        self.movement_btn.setEnabled(False)
        self.movement_btn.clicked.connect(self.show_movement)
        top.addWidget(self.movement_btn)

        self.quick_edit_btn = QPushButton("⚡ تعديل سريع")
        self.quick_edit_btn.setEnabled(False)
        self.quick_edit_btn.clicked.connect(self.quick_edit)
        top.addWidget(self.quick_edit_btn)

        self.print_barcode_btn = QPushButton("🖨️ طباعة باركود")
        self.print_barcode_btn.setEnabled(False)
        self.print_barcode_btn.clicked.connect(self.print_barcode)
        top.addWidget(self.print_barcode_btn)

        self.refresh_btn = QPushButton("🔄 تحديث")
        self.refresh_btn.clicked.connect(self.refresh)
        top.addWidget(self.refresh_btn)

        self.export_excel_btn = QPushButton("📊 Excel")
        self.export_excel_btn.clicked.connect(self.export_to_excel)
        top.addWidget(self.export_excel_btn)

        self.print_btn = QPushButton("🖨️ طباعة القائمة")
        self.print_btn.clicked.connect(self.print_list)
        top.addWidget(self.print_btn)

        layout.addLayout(top)

        self.table = ModernTableView()
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.doubleClicked.connect(self.edit_item)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.table)

        self.status_label = QLabel()
        layout.addWidget(self.status_label)

        self.load_categories()
        self.category_filter.currentIndexChanged.connect(self.refresh)
        self.refresh()

    def load_categories(self):
        categories = db.get_categories()
        self.category_filter.clear()
        self.category_filter.addItem("جميع التصنيفات", None)
        for c in categories:
            self.category_filter.addItem(c['name'], c['id'])

    def refresh(self):
        search = self.search_edit.text().strip().lower() or None
        category_id = self.category_filter.currentData()
        item_type = self.type_filter.currentData()

        items = db.get_items(search=search)
        if items is None:
            items = []

        filtered = []
        for it in items:
            if category_id and it.get('category_id') != category_id:
                continue
            if item_type and it.get('item_type') != item_type:
                continue
            filtered.append(it)

        settings = get_currency_settings()
        data = []
        for it in filtered:
            data.append([
                it.get('id', ''),
                it.get('name', ''),
                it.get('available', 0),
                it.get('unit', ''),
                format_currency(it.get('selling_price', 0), settings),
                format_currency(it.get('total_value', 0), settings),
                it.get('barcode', '')
            ])
        headers = ["#", "الاسم", "الكمية", "الوحدة الأساسية", "سعر البيع", "قيمة المخزون", "الباركود"]
        self.model = ItemsTableModel(data, headers)
        self.table.setModel(self.model)
        self.table.setColumnHidden(0, True)
        self.table.setColumnHidden(6, True)
        self.table.resizeRowsToContents()

        for row, it in enumerate(filtered):
            if it.get('item_units'):
                subunits = ", ".join([f"{u['unit_name']} ({u['conversion_factor']})" for u in it['item_units']])
                self.table.model().setData(self.table.model().index(row, 3), subunits, Qt.ToolTipRole)

        if self.table.selectionModel():
            try:
                self.table.selectionModel().selectionChanged.disconnect()
            except:
                pass
            self.table.selectionModel().selectionChanged.connect(self.on_selection_changed)

        self.delete_btn.setEnabled(False)
        self.movement_btn.setEnabled(False)
        self.quick_edit_btn.setEnabled(False)
        self.print_barcode_btn.setEnabled(False)
        self.current_item_id = None
        self.current_item_name = None
        self.status_label.setText(f"إجمالي السجلات: {len(filtered)}")

    def on_selection_changed(self, selected, deselected):
        rows = self.table.selectionModel().selectedRows()
        if rows:
            row = rows[0].row()
            self.current_item_id = self.model._data[row][0]
            self.current_item_name = self.model._data[row][1]
            self.delete_btn.setEnabled(True)
            self.movement_btn.setEnabled(True)
            self.quick_edit_btn.setEnabled(True)
            # تمكين طباعة الباركود فقط إذا كان للمادة باركود
            barcode = self.model._data[row][6]
            self.print_barcode_btn.setEnabled(bool(barcode))
        else:
            self.current_item_id = None
            self.current_item_name = None
            self.delete_btn.setEnabled(False)
            self.movement_btn.setEnabled(False)
            self.quick_edit_btn.setEnabled(False)
            self.print_barcode_btn.setEnabled(False)

    def show_context_menu(self, pos: QPoint):
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        col = index.column()
        if col in (1, 4, 6):
            menu = QMenu()
            copy_action = QAction("نسخ", self)
            copy_action.triggered.connect(lambda: self.copy_to_clipboard(row, col))
            menu.addAction(copy_action)
            menu.exec(self.table.viewport().mapToGlobal(pos))

    def copy_to_clipboard(self, row, col):
        value = self.model._data[row][col]
        clipboard = QApplication.clipboard()
        clipboard.setText(str(value))
        show_toast("تم النسخ إلى الحافظة", "success", self)

    def add_item(self):
        self.current_item_id = None
        self.open_item_dialog()

    def edit_item(self, index):
        row = index.row()
        if row < 0 or not hasattr(self, 'model') or row >= len(self.model._data):
            return
        self.current_item_id = self.model._data[row][0]
        self.open_item_dialog(is_edit=True)

    def delete_selected(self):
        if not self.current_item_id:
            return
        reply = QMessageBox.question(self, "تأكيد الحذف", "هل تريد حذف هذه المادة؟", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                db.delete_item(self.current_item_id)
                show_toast("تم الحذف", "success", self)
                self.refresh()
            except Exception as e:
                show_toast(str(e), "error", self)

    def show_movement(self):
        if not self.current_item_id:
            return
        dialog = CenteredDialog(self)
        dialog.setWindowTitle(f"كشف حركة المادة - {self.current_item_name}")
        dialog.resize(700, 500)
        layout = QVBoxLayout(dialog)

        cur = db.connect().cursor()
        cur.execute("""
            SELECT movement_type, quantity, unit_cost, movement_date, reference_id
            FROM inventory_movements
            WHERE item_id = ? AND user_id = ?
            ORDER BY movement_date DESC
        """, (self.current_item_id, Session.get_current_user_id()))
        rows = cur.fetchall()
        if not rows:
            label = QLabel("لا توجد حركات لهذه المادة")
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)
        else:
            html = f"""
            <div style="text-align: center;">
                <h3>كشف حركة المادة: {self.current_item_name}</h3>
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
            for r in rows:
                movement_type = "شراء" if r['movement_type'] == 'purchase' else "بيع" if r['movement_type'] == 'sale' else "تعديل"
                qty = float(r['quantity'])
                unit_cost = float(r['unit_cost']) if r['unit_cost'] else 0
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
            html += "</tbody></table>"
            text_edit = QLabel(html)
            text_edit.setWordWrap(True)
            text_edit.setTextFormat(Qt.RichText)
            layout.addWidget(text_edit)

        close_btn = QPushButton("إغلاق")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        dialog.exec()

    def quick_edit(self):
        if not self.current_item_id:
            return
        items = db.get_items()
        item = next((i for i in items if i['id'] == self.current_item_id), None)
        if not item:
            show_toast("لم يتم العثور على المادة", "error", self)
            return

        dialog = CenteredDialog(self)
        dialog.setWindowTitle(f"تعديل سريع - {self.current_item_name}")
        dialog.resize(350, 200)
        layout = QFormLayout(dialog)

        selling_spin = QDoubleSpinBox()
        selling_spin.setRange(0, 999999)
        selling_spin.setDecimals(2)
        selling_spin.setValue(item.get('selling_price', 0))
        layout.addRow("سعر البيع الجديد:", selling_spin)

        qty_spin = QDoubleSpinBox()
        qty_spin.setRange(0, 999999)
        qty_spin.setDecimals(2)
        qty_spin.setValue(item.get('quantity', 0))
        layout.addRow("الكمية الجديدة:", qty_spin)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("حفظ")
        cancel_btn = QPushButton("إلغاء")
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

        def on_save():
            new_price = selling_spin.value()
            new_qty = qty_spin.value()
            try:
                update_data = {
                    'name': item['name'],
                    'category_id': item.get('category_id'),
                    'item_type': item.get('item_type', 'مخزون'),
                    'purchase_price': item.get('purchase_price', 0),
                    'selling_price': new_price,
                    'quantity': new_qty,
                    'unit': item.get('unit', ''),
                    'average_cost': item.get('average_cost', 0),
                    'barcode': item.get('barcode')
                }
                db.update_item(self.current_item_id, update_data)
                show_toast("تم التحديث بنجاح", "success", self)
                dialog.accept()
                self.refresh()
            except Exception as e:
                show_toast(str(e), "error", self)

        save_btn.clicked.connect(on_save)
        cancel_btn.clicked.connect(dialog.reject)
        dialog.exec()

    def print_barcode(self):
        """طباعة باركود المادة المحددة"""
        if not self.current_item_id:
            show_toast("لم يتم تحديد مادة", "error", self)
            return
        
        # جلب المادة للتأكد من وجود باركود
        items = db.get_items()
        item = next((i for i in items if i['id'] == self.current_item_id), None)
        if not item:
            show_toast("المادة غير موجودة", "error", self)
            return
        
        barcode_text = item.get('barcode')
        if not barcode_text:
            show_toast("هذه المادة ليس لها باركود", "error", self)
            return
        
        try:
            # توليد صورة الباركود باستخدام python-barcode
            # نستخدم EAN-13 أو Code128 (نختار Code128 لأنه يدعم أي أرقام/حروف)
            # ولكن EAN-13 يتطلب 12 أو 13 رقماً فقط. لضمان التوافق، نستخدم Code128
            code128 = barcode.get_barcode_class('code128')
            barcode_obj = code128(barcode_text, writer=ImageWriter())
            
            # حفظ مؤقت
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                filename = tmp.name
            barcode_obj.save(filename)
            
            # طباعة الصورة باستخدام QPrinter (معاينة قبل الطباعة)
            if PRINT_AVAILABLE:
                printer = QPrinter(QPrinter.HighResolution)
                preview = QPrintPreviewDialog(printer, self)
                preview.paintRequested.connect(lambda p: self._print_barcode_image(p, filename, item['name']))
                preview.exec()
            else:
                # بديل: حفظ الصورة وفتحها
                save_path, _ = QFileDialog.getSaveFileName(self, "حفظ الباركود", f"barcode_{item['name']}.png", "PNG (*.png)")
                if save_path:
                    import shutil
                    shutil.copy(filename, save_path)
                    show_toast(f"تم حفظ الباركود إلى {save_path}", "success", self)
            
            # حذف الملف المؤقت بعد فترة
            QTimer.singleShot(5000, lambda: os.unlink(filename) if os.path.exists(filename) else None)
            
        except Exception as e:
            show_toast(f"خطأ في إنشاء الباركود: {str(e)}", "error", self)

    def _print_barcode_image(self, printer, image_path, item_name):
        """طباعة الصورة على الطابعة"""
        try:
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                return
            # قياس الصفحة ومركزة الصورة
            page_rect = printer.pageRect()
            scaled_pixmap = pixmap.scaled(page_rect.width() * 0.6, page_rect.height() * 0.3, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            x = (page_rect.width() - scaled_pixmap.width()) / 2
            y = (page_rect.height() - scaled_pixmap.height()) / 2
            painter = QPainter(printer)
            painter.drawPixmap(int(x), int(y), scaled_pixmap)
            # إضافة اسم المادة تحت الباركود
            painter.setFont(QFont("Tajawal", 12))
            painter.drawText(page_rect, Qt.AlignCenter | Qt.AlignBottom, item_name)
            painter.end()
        except Exception as e:
            show_toast(f"خطأ في الطباعة: {str(e)}", "error", self)

    def open_item_dialog(self, is_edit=False, dialog_parent=None):
        if dialog_parent is None:
            dialog_parent = self
        dialog = CenteredDialog(dialog_parent)
        dialog.setWindowTitle("تعديل مادة" if is_edit else "إضافة مادة جديدة")
        dialog.setLayoutDirection(Qt.RightToLeft)
        dialog.resize(620, 600)
        main_layout = QVBoxLayout(dialog)

        currency_symbol = get_current_currency_symbol()

        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setSpacing(8)
        form_layout.setContentsMargins(12,12,12,12)

        name_edit = QLineEdit()
        form_layout.addRow("اسم المادة:", name_edit)

        barcode_layout = QHBoxLayout()
        self.barcode_edit = QLineEdit()
        self.barcode_edit.setPlaceholderText("رمز الباركود (اختياري)")
        generate_barcode_btn = QPushButton("إنشاء عشوائي")
        generate_barcode_btn.setFixedWidth(100)
        generate_barcode_btn.clicked.connect(self.generate_barcode)
        barcode_layout.addWidget(self.barcode_edit)
        barcode_layout.addWidget(generate_barcode_btn)
        form_layout.addRow("الباركود:", barcode_layout)

        cat_layout = QHBoxLayout()
        cat_combo = QComboBox()
        cat_combo.addItem("بدون تصنيف", None)
        categories = db.get_categories()
        for c in categories:
            cat_combo.addItem(c['name'], c['id'])
        cat_layout.addWidget(cat_combo)
        add_cat_btn = QPushButton("+")
        add_cat_btn.setFixedSize(30, 30)
        add_cat_btn.setToolTip("إضافة تصنيف جديد")
        cat_layout.addWidget(add_cat_btn)
        form_layout.addRow("التصنيف:", cat_layout)

        type_combo = QComboBox()
        type_combo.addItems(["مخزون", "منتج نهائي", "خدمة"])
        form_layout.addRow("نوع المادة:", type_combo)

        unit_edit = QLineEdit()
        unit_edit.setPlaceholderText("مثال: قطعة، كيلو، متر، علبة...")
        form_layout.addRow("الوحدة الأساسية:", unit_edit)

        purchase_spin = QDoubleSpinBox()
        purchase_spin.setRange(0, 999999)
        purchase_spin.setDecimals(2)
        purchase_spin.setPrefix(f"{currency_symbol} ")
        form_layout.addRow("سعر الشراء:", purchase_spin)

        selling_spin = QDoubleSpinBox()
        selling_spin.setRange(0, 999999)
        selling_spin.setDecimals(2)
        selling_spin.setPrefix(f"{currency_symbol} ")
        form_layout.addRow("سعر البيع:", selling_spin)

        qty_spin = QDoubleSpinBox()
        qty_spin.setRange(0, 999999)
        qty_spin.setDecimals(2)
        form_layout.addRow("الكمية الافتتاحية:", qty_spin)

        main_layout.addWidget(form_widget)

        units_group = QGroupBox("الوحدات الفرعية (للتحويل في الفواتير)")
        units_layout = QVBoxLayout(units_group)
        self.units_list = QListWidget()
        units_layout.addWidget(self.units_list)
        btn_add_unit = QPushButton("➕ إضافة وحدة فرعية")
        btn_add_unit.clicked.connect(lambda: self.add_subunit_dialog(self.units_list, unit_edit.text()))
        units_layout.addWidget(btn_add_unit)
        btn_remove_unit = QPushButton("🗑 حذف الوحدة المحددة")
        btn_remove_unit.clicked.connect(lambda: self.remove_subunit(self.units_list))
        units_layout.addWidget(btn_remove_unit)
        main_layout.addWidget(units_group)

        stats_label = QLabel()
        stats_label.setWordWrap(True)
        stats_label.setVisible(False)

        if is_edit:
            items = db.get_items()
            item_data = next((i for i in items if i.get('id') == self.current_item_id), None)
            if item_data:
                name_edit.setText(item_data.get('name', ''))
                self.barcode_edit.setText(item_data.get('barcode', ''))
                idx = cat_combo.findData(item_data.get('category_id'))
                if idx >= 0: cat_combo.setCurrentIndex(idx)
                type_combo.setCurrentText(item_data.get('item_type', 'مخزون'))
                unit_edit.setText(item_data.get('unit', ''))
                purchase_spin.setValue(item_data.get('purchase_price', 0))
                selling_spin.setValue(item_data.get('selling_price', 0))
                qty_spin.setValue(item_data.get('quantity', 0))
                subunits = db.get_item_units(self.current_item_id)
                for su in subunits:
                    self.units_list.addItem(f"{su['unit_name']} : {su['conversion_factor']}")
                stats_text = f"""
                <b>إجمالي الكمية المشتراة:</b> {item_data.get('purchase_qty', 0)}<br>
                <b>إجمالي الكمية المباعة:</b> {item_data.get('sale_qty', 0)}<br>
                <b>عدد مرات الشراء:</b> {item_data.get('purchase_count', 0)}<br>
                <b>عدد مرات البيع:</b> {item_data.get('sale_count', 0)}<br>
                <b>آخر شراء:</b> {item_data.get('last_purchase_date', '-')}<br>
                <b>آخر بيع:</b> {item_data.get('last_sale_date', '-')}<br>
                <b>متوسط سعر الشراء:</b> {format_currency(item_data.get('average_cost', 0))}
                """
                stats_label.setText(stats_text)
                stats_label.setVisible(True)
                main_layout.addWidget(stats_label)

        def add_new_category():
            cat_dialog = CenteredDialog(dialog)
            cat_dialog.setWindowTitle("إضافة تصنيف جديد")
            cat_dialog.setLayoutDirection(Qt.RightToLeft)
            cat_dialog.resize(300, 120)
            cat_layout_form = QFormLayout(cat_dialog)
            cat_name_edit = QLineEdit()
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
                    show_toast("اسم التصنيف مطلوب", "error", cat_dialog)
                    return
                try:
                    new_id = db.add_category(cat_name)
                    cat_combo.addItem(cat_name, new_id)
                    cat_combo.setCurrentIndex(cat_combo.count()-1)
                    cat_dialog.accept()
                    show_toast("تمت إضافة التصنيف", "success", dialog)
                except Exception as e:
                    show_toast(str(e), "error", cat_dialog)
            save_cat_btn.clicked.connect(save_category)
            cancel_cat_btn.clicked.connect(cat_dialog.reject)
            cat_dialog.exec()

        add_cat_btn.clicked.connect(add_new_category)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("حفظ")
        save_btn.setObjectName("primary")
        cancel_btn = QPushButton("إلغاء")
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        main_layout.addLayout(btn_layout)

        def on_save():
            name = name_edit.text().strip()
            if not name:
                show_toast("اسم المادة مطلوب", "error", dialog)
                return
            barcode = self.barcode_edit.text().strip() or None
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
                    db.update_item(self.current_item_id, data)
                    db.clear_item_units(self.current_item_id)
                    for i in range(self.units_list.count()):
                        item_text = self.units_list.item(i).text()
                        parts = item_text.split(' : ')
                        if len(parts) == 2:
                            unit_name = parts[0]
                            factor = float(parts[1])
                            db.add_item_unit(self.current_item_id, unit_name, factor)
                    show_toast("تم التعديل", "success", dialog)
                else:
                    new_id = db.add_item(data)
                    self.current_item_id = new_id
                    for i in range(self.units_list.count()):
                        item_text = self.units_list.item(i).text()
                        parts = item_text.split(' : ')
                        if len(parts) == 2:
                            unit_name = parts[0]
                            factor = float(parts[1])
                            db.add_item_unit(new_id, unit_name, factor)
                    show_toast("تمت الإضافة", "success", dialog)
                dialog.accept()
                self.refresh()
                self.load_categories()
            except Exception as e:
                show_toast(str(e), "error", dialog)

        save_btn.clicked.connect(on_save)
        cancel_btn.clicked.connect(dialog.reject)
        dialog.exec()

    def generate_barcode(self):
        import uuid
        new_barcode = str(uuid.uuid4().int)[:13]
        self.barcode_edit.setText(new_barcode)

    def add_subunit_dialog(self, units_list, base_unit):
        dialog = CenteredDialog(self)
        dialog.setWindowTitle("إضافة وحدة فرعية")
        dialog.setLayoutDirection(Qt.RightToLeft)
        dialog.resize(350, 180)
        layout = QFormLayout(dialog)
        unit_name_edit = QLineEdit()
        unit_name_edit.setPlaceholderText("مثال: كرتونة، طبق، دستة...")
        layout.addRow("اسم الوحدة الفرعية:", unit_name_edit)
        factor_spin = QDoubleSpinBox()
        factor_spin.setRange(0.001, 999999)
        factor_spin.setValue(1.0)
        factor_spin.setToolTip("1 وحدة فرعية = ? وحدة أساسية")
        layout.addRow("عامل التحويل (1 فرعية = ? أساسية):", factor_spin)
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("إضافة")
        cancel_btn = QPushButton("إلغاء")
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

        def on_add():
            unit_name = unit_name_edit.text().strip()
            if not unit_name:
                show_toast("اسم الوحدة مطلوب", "error", dialog)
                return
            factor = factor_spin.value()
            if factor <= 0:
                show_toast("عامل التحويل يجب أن يكون أكبر من صفر", "error", dialog)
                return
            units_list.addItem(f"{unit_name} : {factor}")
            dialog.accept()

        add_btn.clicked.connect(on_add)
        cancel_btn.clicked.connect(dialog.reject)
        dialog.exec()

    def remove_subunit(self, units_list):
        row = units_list.currentRow()
        if row >= 0:
            units_list.takeItem(row)

    def export_to_excel(self):
        if hasattr(self.table, 'export_to_excel'):
            self.table.export_to_excel()
        else:
            show_toast("هذه الميزة غير متوفرة حالياً", "error", self)

    def print_list(self):
        if hasattr(self.table, 'print_table'):
            self.table.print_table()
        else:
            show_toast("هذه الميزة غير متوفرة حالياً", "error", self)
