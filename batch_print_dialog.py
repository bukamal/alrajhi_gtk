# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QPushButton, QSpinBox, QHeaderView, QMessageBox, QComboBox, QLabel,
                             QListWidget, QListWidgetItem, QDialogButtonBox)
from PyQt5.QtCore import Qt
from views_pyqt5.centered_dialog import CenteredDialog
from database import item_dao
from utils_pyqt5 import format_currency, show_toast
from thermal_printer import ThermalPrinter, PDFPrinter, ImagePrinter
from printer_manager import PrinterManager
from label_designer import get_current_template
import base64
import io
from barcode import Code128
from barcode.writer import ImageWriter

class BatchPrintDialog(CenteredDialog):
    def __init__(self, parent=None, selected_items=None):
        super().__init__(parent)
        self.setWindowTitle("طباعة باركودات متعددة")
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(700, 500)
        self.selected_items = selected_items or []
        self.printer_manager = PrinterManager()
        self.printer_manager.load_default_printer()
        
        layout = QVBoxLayout(self)
        
        # شريط الأدوات العلوي
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("الطابعة:"))
        self.printer_combo = QComboBox()
        for p in self.printer_manager.printers:
            self.printer_combo.addItem(p.name, p.id)
        toolbar.addWidget(self.printer_combo)
        
        self.copies_spin = QSpinBox()
        self.copies_spin.setRange(1, 10)
        self.copies_spin.setValue(1)
        toolbar.addWidget(QLabel("عدد النسخ:"))
        toolbar.addWidget(self.copies_spin)
        layout.addLayout(toolbar)
        
        # جدول المواد
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["المادة", "الباركود", "السعر", "عدد النسخ"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        
        # أزرار التحكم
        btn_layout = QHBoxLayout()
        select_btn = QPushButton("➕ إضافة مواد")
        select_btn.clicked.connect(self.select_items)
        btn_layout.addWidget(select_btn)
        remove_btn = QPushButton("🗑 حذف المحدد")
        remove_btn.clicked.connect(self.remove_selected)
        btn_layout.addWidget(remove_btn)
        print_btn = QPushButton("🖨️ طباعة")
        print_btn.setObjectName("primary")
        print_btn.clicked.connect(self.do_print)
        btn_layout.addWidget(print_btn)
        cancel_btn = QPushButton("إلغاء")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        self.load_items()
    
    def load_items(self):
        if self.selected_items:
            for item in self.selected_items:
                self.add_item_to_table(item)
        else:
            self.select_items()
    
    def select_items(self):
        dialog = CenteredDialog(self)
        dialog.setWindowTitle("اختر المواد")
        dialog.resize(500, 400)
        layout = QVBoxLayout(dialog)
        
        items = item_dao.get_items()
        list_widget = QListWidget()
        list_widget.setSelectionMode(QListWidget.MultiSelection)
        for it in items:
            if it.barcode:
                item_text = f"{it.name} - {it.barcode} - {format_currency(it.selling_price)}"
                list_item = QListWidgetItem(item_text)
                list_item.setData(Qt.UserRole, it.id)
                list_widget.addItem(list_item)
        layout.addWidget(list_widget)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec():
            for list_item in list_widget.selectedItems():
                item_id = list_item.data(Qt.UserRole)
                it = next((x for x in items if x.id == item_id), None)
                if it:
                    self.add_item_to_table(it)
    
    def add_item_to_table(self, item):
        # التحقق من عدم التكرار
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).data(Qt.UserRole) == item.id:
                return
        row = self.table.rowCount()
        self.table.insertRow(row)
        name_item = QTableWidgetItem(item.name)
        name_item.setData(Qt.UserRole, item.id)
        self.table.setItem(row, 0, name_item)
        self.table.setItem(row, 1, QTableWidgetItem(item.barcode or ""))
        self.table.setItem(row, 2, QTableWidgetItem(format_currency(item.selling_price)))
        copies_spin = QSpinBox()
        copies_spin.setRange(1, 99)
        copies_spin.setValue(1)
        self.table.setCellWidget(row, 3, copies_spin)
    
    def remove_selected(self):
        rows = set()
        for item in self.table.selectedItems():
            rows.add(item.row())
        for row in sorted(rows, reverse=True):
            self.table.removeRow(row)
    
    def do_print(self):
        if self.table.rowCount() == 0:
            show_toast("لا توجد مواد للطباعة", "error", self)
            return
        
        printer_id = self.printer_combo.currentData()
        printer_info = self.printer_manager.get_printer(printer_id)
        if not printer_info:
            show_toast("لم يتم اختيار طابعة", "error", self)
            return
        
        # تجميع البيانات
        items_data = []
        for row in range(self.table.rowCount()):
            item_id = self.table.item(row, 0).data(Qt.UserRole)
            barcode = self.table.item(row, 1).text()
            price = self.table.item(row, 2).text()
            copies = self.table.cellWidget(row, 3).value()
            items_data.append({
                'id': item_id,
                'barcode': barcode,
                'name': self.table.item(row, 0).text(),
                'price': price,
                'copies': copies
            })
        
        success = True
        
        if printer_info.type.value == 'serial':
            tp = ThermalPrinter(printer_info.connection_string, baudrate=9600)
            if not tp.connect():
                show_toast("فشل الاتصال بالطابعة", "error", self)
                return
            for item in items_data:
                for _ in range(item['copies']):
                    if not tp.print_label(item['barcode'], item['name'], item['price'], 1):
                        success = False
            tp.disconnect()
        elif printer_info.type.value == 'pdf':
            pdf_printer = PDFPrinter(self)
            for item in items_data:
                for _ in range(item['copies']):
                    pdf_printer.print_label(item['barcode'], item['name'], item['price'], 1)
        elif printer_info.type.value == 'image':
            img_printer = ImagePrinter(self)
            for item in items_data:
                for _ in range(item['copies']):
                    img_printer.print_label(item['barcode'], item['name'], item['price'], 1)
        else:
            # طباعة عادية عبر QPrinter (PDF) - استخدم PDFPrinter
            pdf_printer = PDFPrinter(self)
            for item in items_data:
                for _ in range(item['copies']):
                    pdf_printer.print_label(item['barcode'], item['name'], item['price'], 1)
        
        if success:
            show_toast("تمت الطباعة بنجاح", "success", self)
            self.accept()
        else:
            show_toast("حدثت بعض الأخطاء أثناء الطباعة", "error", self)
