# -*- coding: utf-8 -*-
import os
import time
import io
import base64
from typing import Optional
from PIL import Image
from barcode import Code128
from barcode.writer import ImageWriter
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QApplication
from PyQt5.QtGui import QTextDocument
from PyQt5.QtPrintSupport import QPrinter
from label_designer import get_current_template
from config import get_currency_symbol
from utils_pyqt5 import show_toast

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

# ========== ThermalPrinter (ESC/POS) ==========
class ThermalPrinter:
    CMD_INIT = b'\x1b\x40'
    CMD_BOLD_ON = b'\x1b\x45\x01'
    CMD_BOLD_OFF = b'\x1b\x45\x00'
    CMD_ALIGN_LEFT = b'\x1b\x61\x00'
    CMD_ALIGN_CENTER = b'\x1b\x61\x01'
    CMD_ALIGN_RIGHT = b'\x1b\x61\x02'
    CMD_FONT_SIZE_NORMAL = b'\x1d\x21\x00'
    CMD_FONT_SIZE_DOUBLE = b'\x1d\x21\x11'
    CMD_LINE_FEED = b'\x0a'
    CMD_CUT = b'\x1d\x56\x42\x00'
    CMD_BARCODE_CODE128 = b'\x1d\x6b\x73'
    
    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 2.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._serial = None
    
    def connect(self) -> bool:
        if not SERIAL_AVAILABLE:
            return False
        try:
            self._serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            self._serial.write(self.CMD_INIT)
            time.sleep(0.1)
            return True
        except Exception as e:
            print(f"خطأ في فتح المنفذ {self.port}: {e}")
            return False
    
    def disconnect(self):
        if self._serial and self._serial.is_open:
            self._serial.close()
            self._serial = None
    
    def is_connected(self) -> bool:
        return self._serial is not None and self._serial.is_open
    
    def _write(self, data: bytes):
        if self._serial:
            self._serial.write(data)
    
    def set_alignment(self, align: str):
        if align == 'center':
            self._write(self.CMD_ALIGN_CENTER)
        elif align == 'right':
            self._write(self.CMD_ALIGN_RIGHT)
        else:
            self._write(self.CMD_ALIGN_LEFT)
    
    def set_bold(self, bold: bool = True):
        self._write(self.CMD_BOLD_ON if bold else self.CMD_BOLD_OFF)
    
    def set_double_size(self, double: bool = True):
        self._write(self.CMD_FONT_SIZE_DOUBLE if double else self.CMD_FONT_SIZE_NORMAL)
    
    def text(self, text: str, encoding: str = 'cp1256'):
        try:
            encoded = text.encode(encoding)
        except:
            encoded = text.encode('utf-8')
        self._write(encoded)
    
    def line_feed(self, lines: int = 1):
        for _ in range(lines):
            self._write(self.CMD_LINE_FEED)
    
    def feed_and_cut(self):
        self.line_feed(3)
        self._write(self.CMD_CUT)
    
    def print_barcode(self, barcode: str, height: int = 80, hri: str = 'B'):
        if not barcode:
            return
        self._write(b'\x1d\x68' + bytes([height]))
        hri_map = {'N': 0, 'A': 1, 'B': 2, 'C': 3}
        hri_code = hri_map.get(hri, 2)
        self._write(b'\x1d\x48' + bytes([hri_code]))
        n = len(barcode)
        self._write(self.CMD_BARCODE_CODE128 + bytes([n]) + barcode.encode() + b'\x00')
    
    def print_label(self, barcode: str, item_name: str, price: str = "", copies: int = 1) -> bool:
        self.connect()
        if not self.is_connected():
            return False
        try:
            for _ in range(copies):
                self.set_alignment('center')
                self.set_bold(True)
                self.set_double_size(True)
                self.text(item_name)
                self.line_feed(1)
                self.set_double_size(False)
                self.set_bold(False)
                self.print_barcode(barcode, height=80, hri='B')
                self.line_feed(1)
                if price:
                    self.text(f"السعر: {price}")
                self.line_feed(2)
            self.feed_and_cut()
            return True
        except Exception as e:
            print(f"خطأ في الطباعة: {e}")
            return False
        finally:
            self.disconnect()

# ========== PDFPrinter (يستخدم القالب) ==========
class PDFPrinter:
    def __init__(self, parent_widget=None):
        self.parent = parent_widget
    
    def _barcode_to_base64(self, barcode: str) -> str:
        code128 = Code128(barcode, writer=ImageWriter())
        buffer = io.BytesIO()
        code128.write(buffer)
        return base64.b64encode(buffer.getvalue()).decode()
    
    def print_label(self, barcode: str, item_name: str, price: str = "", copies: int = 1) -> bool:
        # التأكد من أن parent widget موجود وقابل للاستخدام
        if self.parent is None:
            print("خطأ: لا يوجد نافذة أبوية لفتح حوار الحفظ")
            return False
        
        # فتح حوار حفظ الملف
        filename, selected_filter = QFileDialog.getSaveFileName(
            self.parent,
            "حفظ الباركود كـ PDF",
            f"barcode_{item_name}.pdf",
            "PDF Files (*.pdf)"
        )
        
        if not filename:
            print("تم إلغاء الحفظ من قبل المستخدم")
            return False
        
        try:
            # تحديث واجهة المستخدم لإظهار أن العمل جارٍ
            QApplication.processEvents()
            
            img_base64 = self._barcode_to_base64(barcode)
            template = get_current_template()
            currency = get_currency_symbol('USD')
            price_label = "السعر:" if price else ""
            
            html = template.replace("{{company_name}}", "الراجحي للمحاسبة")
            html = html.replace("{{item_name}}", item_name)
            html = html.replace("{{barcode_image}}", img_base64)
            html = html.replace("{{barcode}}", barcode)
            html = html.replace("{{price_label}}", price_label)
            html = html.replace("{{price}}", price)
            
            doc = QTextDocument()
            doc.setHtml(html)
            printer = QPrinter()
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(filename)
            doc.print(printer)
            
            # عرض رسالة نجاح
            if self.parent:
                show_toast(f"تم حفظ PDF بنجاح: {os.path.basename(filename)}", "success", self.parent)
            return True
        except Exception as e:
            error_msg = f"فشل حفظ PDF: {str(e)}"
            print(error_msg)
            if self.parent:
                show_toast(error_msg, "error", self.parent)
            return False

# ========== ImagePrinter ==========
class ImagePrinter:
    def __init__(self, parent_widget=None):
        self.parent = parent_widget
    
    def print_label(self, barcode: str, item_name: str, price: str = "", copies: int = 1) -> bool:
        # التأكد من أن parent widget موجود وقابل للاستخدام
        if self.parent is None:
            print("خطأ: لا يوجد نافذة أبوية لفتح حوار الحفظ")
            return False
        
        # فتح حوار حفظ الملف
        filename, selected_filter = QFileDialog.getSaveFileName(
            self.parent,
            "حفظ الباركود كـ PNG",
            f"barcode_{item_name}.png",
            "PNG Files (*.png)"
        )
        
        if not filename:
            print("تم إلغاء الحفظ من قبل المستخدم")
            return False
        
        try:
            # تحديث واجهة المستخدم لإظهار أن العمل جارٍ
            QApplication.processEvents()
            
            code128 = Code128(barcode, writer=ImageWriter())
            code128.save(filename)
            
            # عرض رسالة نجاح
            if self.parent:
                show_toast(f"تم حفظ الصورة بنجاح: {os.path.basename(filename)}", "success", self.parent)
            return True
        except Exception as e:
            error_msg = f"فشل حفظ الصورة: {str(e)}"
            print(error_msg)
            if self.parent:
                show_toast(error_msg, "error", self.parent)
            return False
