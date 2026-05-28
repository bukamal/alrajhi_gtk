# -*- coding: utf-8 -*-
import sys
import os
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QMessageBox, QApplication
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QRect
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QColor

# إضافة مسار المكتبات الإضافية في حالة التجميع
if getattr(sys, 'frozen', False):
    # عند تشغيل exe، أضف المسار الحالي إلى متغير بيئة PATH
    os.environ['PATH'] = os.path.dirname(sys.executable) + os.pathsep + os.environ['PATH']

# محاولة استيراد مكتبات الكاميرا
CV2_AVAILABLE = False
try:
    import cv2
    from pyzbar.pyzbar import decode
    CV2_AVAILABLE = True
except ImportError as e:
    print(f"فشل استيراد مكتبات المسح: {e}")

class BarcodeScanner(QDialog):
    barcode_scanned = pyqtSignal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("مسح الباركود بالكاميرا")
        self.setModal(True)
        self.resize(680, 520)
        layout = QVBoxLayout(self)
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        layout.addWidget(self.video_label)
        self.status_label = QLabel("جاهز للمسح...")
        layout.addWidget(self.status_label)
        
        self.close_btn = QPushButton("إلغاء")
        self.close_btn.clicked.connect(self.reject)
        layout.addWidget(self.close_btn)
        
        if not CV2_AVAILABLE:
            self.status_label.setText("⚠️ مكتبات OpenCV أو pyzbar غير مثبتة. لا يمكن استخدام الكاميرا.")
            self.video_label.setText("يرجى تثبيت المكتبات:\npip install opencv-python pyzbar")
            self.timer = None
            self.cap = None
            return
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.cap = None
        self.barcode_data = None
        self.scanning = True
        self.init_camera()

    def init_camera(self):
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                raise Exception("لا يمكن فتح الكاميرا")
            self.timer.start(50)
            self.status_label.setText("جارٍ المسح... (وجه الكاميرا نحو الباركود)")
        except Exception as e:
            QMessageBox.warning(self, "خطأ", f"فشل في تشغيل الكاميرا: {str(e)}")
            self.reject()

    def update_frame(self):
        if self.cap is None or not self.scanning:
            return
        ret, frame = self.cap.read()
        if ret:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            qt_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            decoded_objects = decode(rgb)
            for obj in decoded_objects:
                barcode = obj.data.decode('utf-8')
                if barcode:
                    self.barcode_data = barcode
                    self.status_label.setText(f"✅ تم المسح: {barcode}")
                    QApplication.beep()
                    self.scanning = False
                    self.timer.stop()
                    self.cap.release()
                    self.accept()
                    return
            
            painter = QPainter(qt_img)
            pen = QPen(QColor(0, 255, 0), 3, Qt.DashLine)
            painter.setPen(pen)
            center_rect = QRect(w//4, h//3, w//2, h//3)
            painter.drawRect(center_rect)
            painter.end()
            
            self.video_label.setPixmap(QPixmap.fromImage(qt_img).scaled(640, 480, Qt.KeepAspectRatio))
            self.status_label.setText("جارٍ المسح... (ضع الباركود داخل المستطيل الأخضر)")
        else:
            self.status_label.setText("فشل في قراءة الكاميرا")

    def get_barcode(self):
        return self.barcode_data

    def closeEvent(self, event):
        if hasattr(self, 'cap') and self.cap:
            self.cap.release()
        if hasattr(self, 'timer') and self.timer:
            self.timer.stop()
        event.accept()
