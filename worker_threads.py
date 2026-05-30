# -*- coding: utf-8 -*-
from PyQt5.QtCore import QThread, pyqtSignal
from database import reporting_dao

class ExportWorker(QThread):
    finished = pyqtSignal(bytes)
    error = pyqtSignal(str)

    def run(self):
        try:
            # لا توجد أي عمليات واجهة مستخدم هنا، فقط معالجة بيانات
            data = reporting_dao.export_full_database()
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))

class ImportWorker(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, data):
        super().__init__()
        self.data = data

    def run(self):
        try:
            reporting_dao.import_full_database(self.data)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))
