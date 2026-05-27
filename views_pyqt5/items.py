# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QTableView,
                             QHeaderView, QMessageBox, QDialog, QFormLayout, QComboBox, QDoubleSpinBox,
                             QLabel, QGroupBox, QListWidget)
from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex
from PyQt5.QtGui import QColor
from database import db
from utils_pyqt5 import format_currency, show_toast
from config import get_currency_settings

class ItemsTableModel(QAbstractTableModel):
    def __init__(self, data, headers):
        super().__init__()
        self._data = data
        self._headers = headers

    def rowCount(self, parent=QModelIndex()): return len(self._data)
    def columnCount(self, parent=QModelIndex()): return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid(): return None
        if role == Qt.DisplayRole:
            try:
                row = index.row()
                col = index.column()
                if 0 <= row < len(self._data) and 0 <= col < len(self._data[row]):
                    value = self._data[row][col]
                    return str(value) if value is not None else ""
            except Exception:
                return ""
        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter
        if role == Qt.ForegroundRole and index.column() == 2:
            try:
                qty = self._data[index.row()][2]
                if isinstance(qty, (int, float)) and qty <= 0:
                    return QColor(239, 68, 68)
                elif isinstance(qty, (int, float)) and qty < 5:
                    return QColor(249, 115, 22)
            except:
                pass
        return None

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if 0 <= section < len(self._headers):
                return self._headers[section]
        return None

    def update_data(self, new_data):
        self.beginResetModel()
        self._data = new_data if new_data is not None else []
        self.endResetModel()

class ItemsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_item_id = None
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

        self.add_btn = QPushButton("➕ إضافة مادة")
        self.add_btn.setObjectName("primary")
        self.add_btn.clicked.connect(self.add_item)
        top.addWidget(self.add_btn)

        self.delete_btn = QPushButton("🗑 حذف المحدد")
        self.delete_btn.setObjectName("danger")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self.delete_selected)
        top.addWidget(self.delete_btn)

        layout.addLayout(top)

        self.table = QTableView()
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.doubleClicked.connect(self.edit_item)
        layout.addWidget(self.table)

    def refresh(self):
        try:
            search = self.search_edit.text().strip().lower()
            items = db.get_items()
            if not items:
                items = []
            if search:
                items = [it for it in items if search in it.get('name', '').lower()]
            settings = get_currency_settings()
            data = []
            for it in items:
                data.append([
                    it.get('id', ''),
                    it.get('name', ''),
                    it.get('available', 0),
                    it.get('unit', ''),
                    format_currency(it.get('selling_price', 0), settings),
                    format_currency(it.get('total_value', 0), settings)
                ])
            headers = ["#", "الاسم", "الكمية", "الوحدة الأساسية", "سعر البيع", "قيمة المخزون"]
            self.model = ItemsTableModel(data, headers)
            self.table.setModel(self.model)
            self.table.setColumnHidden(0, True)
            self.table.resizeRowsToContents()
            self.delete_btn.setEnabled(False)
            self.table.selectionModel().selectionChanged.connect(self.on_selection_changed)
        except Exception as e:
            show_toast(f"خطأ في تحديث المواد: {str(e)}", "error", self)

    def on_selection_changed(self, selected, deselected):
        self.delete_btn.setEnabled(len(self.table.selectionModel().selectedRows()) > 0)

    def add_item(self):
        self.current_item_id = None
        self.open_item_dialog()

    def edit_item(self, index):
        try:
            row = index.row()
            if row < 0 or not hasattr(self, 'model') or row >= len(self.model._data):
                return
            self.current_item_id = self.model._data[row][0]
            self.open_item_dialog(is_edit=True)
        except Exception as e:
            show_toast(f"خطأ: {str(e)}", "error", self)

    def delete_selected(self):
        selection = self.table.selectionModel().selectedRows()
        if not selection:
            return
        row = selection[0].row()
        item_id = self.model._data[row][0]
        reply = QMessageBox.question(self, "تأكيد الحذف", "هل تريد حذف هذه المادة؟", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                db.delete_item(item_id)
                show_toast("تم الحذف", "success", self)
                self.refresh()
            except Exception as e:
                show_toast(str(e), "error", self)

    def edit_item_by_id(self, item_id):
        self.current_item_id = item_id
        self.open_item_dialog(is_edit=True)

    def open_item_dialog(self, is_edit=False):
        dialog = QDialog(self)
        dialog.setWindowTitle("تعديل مادة" if is_edit else "إضافة مادة جديدة")
        dialog.setModal(True)
        dialog.setLayoutDirection(Qt.RightToLeft)
        dialog.resize(600, 550)
        main_layout = QVBoxLayout(dialog)

        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setSpacing(8)
        form_layout.setContentsMargins(12,12,12,12)

        name_edit = QLineEdit()
        form_layout.addRow("اسم المادة:", name_edit)

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
        purchase_spin.setPrefix("$ ")
        form_layout.addRow("سعر الشراء:", purchase_spin)

        selling_spin = QDoubleSpinBox()
        selling_spin.setRange(0, 999999)
        selling_spin.setPrefix("$ ")
        form_layout.addRow("سعر البيع:", selling_spin)

        qty_spin = QDoubleSpinBox()
        qty_spin.setRange(0, 999999)
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
            cat_dialog = QDialog(dialog)
            cat_dialog.setWindowTitle("إضافة تصنيف جديد")
            cat_dialog.setModal(True)
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
            cat_id = cat_combo.currentData()
            item_type = type_combo.currentText()
            unit = unit_edit.text().strip()
            purchase_price = purchase_spin.value()
            selling_price = selling_spin.value()
            qty = qty_spin.value()

            data = {
                'name': name,
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
            except Exception as e:
                show_toast(str(e), "error", dialog)

        save_btn.clicked.connect(on_save)
        cancel_btn.clicked.connect(dialog.reject)
        dialog.exec()

    def add_subunit_dialog(self, units_list, base_unit):
        dialog = QDialog(self)
        dialog.setWindowTitle("إضافة وحدة فرعية")
        dialog.setModal(True)
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
