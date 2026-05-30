# -*- coding: utf-8 -*-
import sys
import time
import os
import subprocess
import tempfile
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QMessageBox
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage
from pyzbar.pyzbar import decode

try:
    from PyQt5.QtMultimedia import QSound
    SOUND_AVAILABLE = True
except ImportError:
    SOUND_AVAILABLE = False

# التحقق من وجود termux-camera-photo (في بيئة Termux)
TERMUX_CAMERA_AVAILABLE = False
try:
    subprocess.run(['termux-camera-photo', '-h'], capture_output=True, check=False)
    TERMUX_CAMERA_AVAILABLE = True
except FileNotFoundError:
    pass


class ContinuousScanner(QDialog):
    barcode_scanned = pyqtSignal(str)

    def __init__(self, parent=None, camera_id=0):
        super().__init__(parent)
        self.setWindowTitle("مسح باركود مستمر (كاميرا)")
        self.setModal(True)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)
        self.setMinimumSize(800, 600)
        self.camera_id = camera_id
        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.scanning = True
        self.last_barcode = None
        self.cooldown = 1000
        self.last_scan_time = 0
        self.flip_horizontal = False
        self.use_termux = TERMUX_CAMERA_AVAILABLE
        self.temp_image_path = None

        layout = QVBoxLayout(self)

        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setText("⚠️ جاري تهيئة الكاميرا...")
        layout.addWidget(self.video_label)

        self.status_label = QLabel("جاهز للمسح... (وجه الكاميرا نحو الباركود)")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        btn_layout = QHBoxLayout()
        self.pause_btn = QPushButton("⏸️ إيقاف مؤقت")
        self.pause_btn.setCheckable(True)
        self.pause_btn.toggled.connect(self.toggle_scanning)
        btn_layout.addWidget(self.pause_btn)

        self.flip_btn = QPushButton("🔄 عكس الكاميرا")
        self.flip_btn.clicked.connect(self.toggle_flip)
        btn_layout.addWidget(self.flip_btn)

        self.close_btn = QPushButton("❌ إغلاق")
        self.close_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)

        # زر لالتقاط صورة يدوياً (بديل للكاميرا الحية)
        self.snap_btn = QPushButton("📸 التقاط صورة")
        self.snap_btn.clicked.connect(self.capture_photo)
        layout.addWidget(self.snap_btn)

        self.init_camera()

    def init_camera(self):
        """تهيئة الكاميرا (محاولة OpenCV أولاً، ثم Termux camera)"""
        global cv2
        if not self.use_termux:
            try:
                import cv2
            except ImportError:
                self.status_label.setText("⚠️ مكتبة OpenCV غير مثبتة. سيتم استخدام وضع التقاط الصور بدلاً من البث المباشر.")
                self.use_termux = True
                self.snap_btn.setVisible(True)
                self.timer.stop()
                self.video_label.setText("وضع التقاط الصور (بدون بث مباشر)")
                return

            try:
                self.cap = cv2.VideoCapture(self.camera_id)
                if not self.cap.isOpened():
                    # تجربة indices مختلفة
                    for idx in range(5):
                        self.cap = cv2.VideoCapture(idx)
                        if self.cap.isOpened():
                            self.camera_id = idx
                            break
                if not self.cap.isOpened():
                    raise Exception("لا يمكن فتح الكاميرا بأي فهرس")
                self.timer.start(50)
                self.status_label.setText("✅ الكاميرا جاهزة، يرجى توجيهها نحو الباركود")
                self.snap_btn.setVisible(False)
                self.video_label.setText("")
                return
            except Exception as e:
                self.status_label.setText(f"⚠️ فشل فتح الكاميرا: {e}")
                self.use_termux = True
                self.snap_btn.setVisible(True)
                self.video_label.setText("وضع التقاط الصور (بدون بث مباشر)")
                self.timer.stop()
                self.cap = None
                return

        # وضع Termux: بدون بث مباشر، نعتمد على التقاط الصور يدوياً
        self.snap_btn.setVisible(True)
        self.video_label.setText("وضع Termux: اضغط على زر 'التقاط صورة' لمسح الباركود")
        self.status_label.setText("✅ جاهز للتصوير")

    def capture_photo(self):
        """التقاط صورة باستخدام termux-camera-photo ثم تحليلها"""
        if not TERMUX_CAMERA_AVAILABLE:
            QMessageBox.warning(self, "خطأ", "لا يوجد دعم للكاميرا في هذه البيئة")
            return
        try:
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                self.temp_image_path = tmp.name
            self.status_label.setText("جاري التقاط الصورة...")
            QApplication.processEvents()
            result = subprocess.run(['termux-camera-photo', '-c', '0', self.temp_image_path], capture_output=True, text=True, timeout=10)
            if result.returncode != 0 or not os.path.exists(self.temp_image_path):
                self.status_label.setText("فشل التقاط الصورة")
                return
            # تحليل الصورة
            from PIL import Image
            img = Image.open(self.temp_image_path)
            decoded = decode(img)
            if decoded:
                barcode = decoded[0].data.decode('utf-8')
                self.on_barcode_detected(barcode)
            else:
                self.status_label.setText("لم يتم العثور على باركود في الصورة")
            # حذف الملف المؤقت
            try:
                os.unlink(self.temp_image_path)
            except:
                pass
        except Exception as e:
            self.status_label.setText(f"خطأ: {str(e)[:50]}")

    def update_frame(self):
        if not self.cap or not self.cap.isOpened():
            return
        ret, frame = self.cap.read()
        if not ret:
            return
        if self.flip_horizontal:
            frame = cv2.flip(frame, 1)

        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        self.video_label.setPixmap(pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

        if self.scanning:
            decoded_objects = decode(frame)
            now_ms = int(time.time() * 1000)
            for obj in decoded_objects:
                if now_ms - self.last_scan_time > self.cooldown:
                    barcode_data = obj.data.decode('utf-8')
                    self.last_scan_time = now_ms
                    self.on_barcode_detected(barcode_data)

    def on_barcode_detected(self, barcode):
        self.last_barcode = barcode
        self.status_label.setText(f"✅ تم المسح: {barcode}")
        if SOUND_AVAILABLE:
            QSound.play("beep.wav")
        self.barcode_scanned.emit(barcode)

    def toggle_scanning(self, checked):
        self.scanning = not checked
        self.pause_btn.setText("▶️ استئناف" if checked else "⏸️ إيقاف مؤقت")
        self.status_label.setText("⏸️ مؤقت" if checked else "✅ جاهز للمسح")

    def toggle_flip(self):
        self.flip_horizontal = not self.flip_horizontal

    def closeEvent(self, event):
        if self.cap:
            self.cap.release()
        self.timer.stop()
        if self.temp_image_path and os.path.exists(self.temp_image_path):
            try:
                os.unlink(self.temp_image_path)
            except:
                pass
        event.accept()
