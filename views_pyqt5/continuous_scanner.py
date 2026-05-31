# -*- coding: utf-8 -*-
import sys
import time
import tempfile
import os
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QMessageBox, QFileDialog
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPixmap

try:
    import cv2
    from pyzbar.pyzbar import decode
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
    decode = None

try:
    from PyQt5.QtMultimedia import QSound
    SOUND_AVAILABLE = True
except ImportError:
    SOUND_AVAILABLE = False

from PIL import Image

class ContinuousScanner(QDialog):
    barcode_scanned = pyqtSignal(str)

    def __init__(self, parent=None, camera_id=0):
        super().__init__(parent)
        self.setWindowTitle("مسح باركود (كاميرا)")
        self.setModal(True)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)
        self.resize(500, 400)
        self.camera_id = camera_id
        self.cap = None

        layout = QVBoxLayout(self)

        self.status_label = QLabel("جاهز للمسح - اضغط على زر 'التقاط صورة'" if CV2_AVAILABLE else "مكتبات الكاميرا غير مثبتة")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(400, 300)
        self.preview_label.setStyleSheet("border: 1px solid #ccc; background-color: #f0f0f0;")
        self.preview_label.setText("معاينة الصورة ستظهر هنا")
        layout.addWidget(self.preview_label)

        btn_layout = QHBoxLayout()
        self.capture_btn = QPushButton("📸 التقاط صورة")
        self.capture_btn.clicked.connect(self.capture_photo)
        self.capture_btn.setObjectName("primary")
        self.capture_btn.setEnabled(CV2_AVAILABLE)
        btn_layout.addWidget(self.capture_btn)

        self.close_btn = QPushButton("❌ إغلاق")
        self.close_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

        if CV2_AVAILABLE:
            self.init_camera()
        else:
            self.status_label.setText("⚠️ OpenCV غير مثبت، لا يمكن استخدام الكاميرا")

    def init_camera(self):
        if not CV2_AVAILABLE:
            return
        self.cap = cv2.VideoCapture(self.camera_id)
        if not self.cap.isOpened():
            for i in range(5):
                self.cap = cv2.VideoCapture(i)
                if self.cap.isOpened():
                    self.camera_id = i
                    break
        if not self.cap.isOpened():
            self.status_label.setText("⚠️ لا يمكن فتح الكاميرا")
            QMessageBox.warning(self, "خطأ", "لا يمكن فتح الكاميرا. تأكد من توصيلها.")
            self.capture_btn.setEnabled(False)
        else:
            self.status_label.setText("✅ الكاميرا جاهزة. اضغط زر 'التقاط صورة'")
            self.show_preview()

    def show_preview(self):
        if CV2_AVAILABLE and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb.shape
                bytes_per_line = ch * w
                from PyQt5.QtGui import QImage
                q_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(q_img)
                self.preview_label.setPixmap(pixmap.scaled(self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def capture_photo(self):
        if not CV2_AVAILABLE or not self.cap or not self.cap.isOpened():
            QMessageBox.warning(self, "خطأ", "الكاميرا غير متاحة")
            return

        ret, frame = self.cap.read()
        if not ret:
            self.status_label.setText("فشل التقاط الصورة")
            return

        # حفظ الصورة مؤقتاً
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            temp_path = tmp.name
        cv2.imwrite(temp_path, frame)

        # عرض الصورة الملتقطة
        pixmap = QPixmap(temp_path)
        self.preview_label.setPixmap(pixmap.scaled(self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

        # تحليل الباركود - تجربة عدة تنسيقات
        img = cv2.imread(temp_path)
        decoded = None
        if decode is not None:
            # 1. BGR مباشرة
            decoded = decode(img)
            if not decoded:
                # 2. RGB
                rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                decoded = decode(rgb)
            if not decoded:
                # 3. Gray
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                decoded = decode(gray)
            if not decoded:
                # 4. عبر PIL
                pil_img = Image.open(temp_path)
                decoded = decode(pil_img)

        os.unlink(temp_path)

        if decoded:
            barcode_data = decoded[0].data.decode('utf-8')
            self.status_label.setText(f"✅ تم المسح: {barcode_data}")
            if SOUND_AVAILABLE:
                QSound.play("beep.wav")
            self.barcode_scanned.emit(barcode_data)
            self.accept()
        else:
            self.status_label.setText("❌ لم يتم العثور على باركود. حاول مرة أخرى")

    def closeEvent(self, event):
        if CV2_AVAILABLE and self.cap:
            self.cap.release()
        event.accept()
