# -*- coding: utf-8 -*-
import serial
import serial.tools.list_ports
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QMessageBox, QSpinBox
from PyQt5.QtCore import Qt
import sys

class SerialPrinterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("طباعة عبر المنفذ التسلسلي")
        self.setModal(True)
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(400, 200)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("اختر المنفذ:"))
        self.port_combo = QComboBox()
        self.refresh_ports()
        layout.addWidget(self.port_combo)

        refresh_btn = QPushButton("تحديث المنافذ")
        refresh_btn.clicked.connect(self.refresh_ports)
        layout.addWidget(refresh_btn)

        layout.addWidget(QLabel("عدد النسخ:"))
        self.copies_spin = QSpinBox()
        self.copies_spin.setRange(1, 5)
        self.copies_spin.setValue(1)
        layout.addWidget(self.copies_spin)

        self.print_btn = QPushButton("طباعة")
        self.print_btn.clicked.connect(self.print)
        self.cancel_btn = QPushButton("إلغاء")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.print_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.printer_data = None  # سيتم تعيينه من الخارج (نص الطباعة)

    def refresh_ports(self):
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(f"{port.device} - {port.description}", port.device)
        if not ports:
            self.port_combo.addItem("لا توجد منافذ متاحة", None)

    def set_print_data(self, text):
        self.printer_data = text

    def print(self):
        port_name = self.port_combo.currentData()
        if not port_name:
            QMessageBox.warning(self, "خطأ", "الرجاء اختيار منفذ صحيح")
            return
        if not self.printer_data:
            QMessageBox.warning(self, "خطأ", "لا توجد بيانات للطباعة")
            return
        try:
            ser = serial.Serial(port_name, 9600, timeout=2)
            for _ in range(self.copies_spin.value()):
                ser.write(self.printer_data.encode('utf-8'))
                ser.write(b'\n\n\n')
            ser.close()
            QMessageBox.information(self, "نجاح", "تمت الطباعة بنجاح")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشلت الطباعة: {str(e)}")

def print_receipt_via_serial(text, parent=None):
    dialog = SerialPrinterDialog(parent)
    dialog.set_print_data(text)
    dialog.exec()
