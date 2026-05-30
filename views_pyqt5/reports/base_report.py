from PyQt5.QtGui import QTextDocument
from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog
import re

def clean_text(text):
    """إزالة أي أحرف غير مرغوب فيها مثل الحرف '浏'"""
    if not text:
        return ''
    # تحويل إلى نص عادي
    text = str(text)
    # إزالة الحرف المحدد بشكل خاص
    text = text.replace('浏', '').replace('�', '').replace('\x00', '')
    # الاحتفاظ فقط بالأحرف العربية والإنجليزية والأرقام والمسافات وعلامات الترقيم الأساسية
    text = re.sub(r'[^\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFFa-zA-Z0-9\s\-\.\,\:\;\(\)\/\+]', '', text)
    return text.strip()

class BaseReport:
    def __init__(self):
        self.html = ""
    def generate(self, start_date=None, end_date=None):
        raise NotImplementedError
    def to_html(self):
        return self.html
    def to_pdf(self, filename):
        doc = QTextDocument()
        doc.setHtml(self.html)
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(filename)
        doc.print(printer)
    def print_preview(self, parent=None):
        doc = QTextDocument()
        doc.setHtml(self.html)
        printer = QPrinter(QPrinter.HighResolution)
        preview = QPrintPreviewDialog(printer, parent)
        preview.paintRequested.connect(lambda p: doc.print(p))
        preview.exec()
