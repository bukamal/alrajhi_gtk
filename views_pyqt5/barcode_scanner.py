# views_pyqt5/barcode_scanner.py
# -*- coding: utf-8 -*-
import sys
import os
import subprocess
import tempfile
import time
from PyQt5.QtWidgets import QApplication, QLabel, QPushButton, QMessageBox, QVBoxLayout, QProgressBar
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QPixmap
from views_pyqt5.centered_dialog import CenteredDialog

# التحقق من وجود termux-camera-photo (في بيئة Termux)
TERMUX_CAMERA_AVAILABLE = False
try:
    subprocess.run(['termux-camera-photo', '-h'], capture_output=True, check=False)
    TERMUX_CAMERA_AVAILABLE = True
except FileNotFoundError:
    pass

if TERMUX_CAMERA_AVAILABLE:
    # وضع Termux: استخدام termux-camera-photo
    class CameraThread(QThread):
        image_captured = pyqtSignal(str)  # مسار الصورة الملتقطة
        error = pyqtSignal(str)

        def run(self):
            try:
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                    tmp_path = tmp.name
                # التقاط صورة باستخدام الكاميرا الخلفية (id 0)
                result = subprocess.run(['termux-camera-photo', '-c', '0', tmp_path], capture_output=True, text=True, timeout=10)
                if result.returncode != 0:
                    self.error.emit(result.stderr or "فشل التقاط الصورة")
                else:
                    # انتظار للتأكد من اكتمال الحفظ
                    time.sleep(0.5)
                    if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
                        self.error.emit("ملف الصورة فارغ أو غير موجود")
                    else:
                        self.image_captured.emit(tmp_path)
            except Exception as e:
                self.error.emit(str(e))

    class BarcodeScanner(CenteredDialog):
        barcode_scanned = pyqtSignal(str)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("مسح الباركود (كاميرا Termux)")
            self.setModal(True)
            self.resize(400, 300)
            layout = QVBoxLayout(self)

            self.status_label = QLabel("جاري التقاط صورة...")
            self.status_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(self.status_label)

            self.progress = QProgressBar()
            self.progress.setRange(0, 0)  # غير محدد
            self.progress.setVisible(True)
            layout.addWidget(self.progress)

            self.close_btn = QPushButton("إلغاء")
            self.close_btn.clicked.connect(self.reject)
            layout.addWidget(self.close_btn)

            self.thread = CameraThread()
            self.thread.image_captured.connect(self.on_image_captured)
            self.thread.error.connect(self.on_error)
            self.thread.start()

        def on_image_captured(self, image_path):
            self.progress.setVisible(False)
            self.status_label.setText("جاري تحليل الباركود...")
            QApplication.processEvents()
            try:
                from pyzbar.pyzbar import decode
                from PIL import Image
                # محاولة فتح الصورة عدة مرات في حالة عدم جاهزيتها
                for _ in range(5):
                    try:
                        img = Image.open(image_path)
                        break
                    except Exception:
                        time.sleep(0.2)
                else:
                    self.status_label.setText("فشل فتح الصورة")
                    QTimer.singleShot(1500, self.reject)
                    return

                decoded = decode(img)
                if decoded:
                    barcode_data = decoded[0].data.decode('utf-8')
                    self.barcode_data = barcode_data
                    self.status_label.setText(f"تم المسح: {barcode_data}")
                    QTimer.singleShot(500, self.accept)
                else:
                    self.status_label.setText("لم يتم العثور على باركود في الصورة")
                    QTimer.singleShot(1500, self.reject)
            except Exception as e:
                self.status_label.setText(f"خطأ: {str(e)[:50]}")
                QTimer.singleShot(1500, self.reject)
            finally:
                try:
                    os.unlink(image_path)
                except:
                    pass

        def on_error(self, error_msg):
            self.status_label.setText(f"فشل التقاط الصورة: {error_msg}")
            QTimer.singleShot(1500, self.reject)

        def get_barcode(self):
            return getattr(self, 'barcode_data', None)

else:
    # وضع Linux العادي: استخدام OpenCV
    import cv2
    from pyzbar.pyzbar import decode
    from PyQt5.QtGui import QImage, QPainter, QPen, QColor

    class BarcodeScanner(CenteredDialog):
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
            if not self.cap or not self.cap.isOpened():
                return
            ret, frame = self.cap.read()
            if not ret:
                return
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            q_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(q_img)

            if self.scanning:
                decoded_objects = decode(frame)
                for obj in decoded_objects:
                    points = obj.polygon
                    if len(points) == 4:
                        pts = [(p.x, p.y) for p in points]
                        painter = QPainter(pixmap)
                        painter.setPen(QPen(QColor(0, 255, 0), 3))
                        painter.drawPolygon([QPoint(p[0], p[1]) for p in pts])
                        painter.end()
                    self.barcode_data = obj.data.decode('utf-8')
                    self.scanning = False
                    self.status_label.setText(f"تم المسح: {self.barcode_data}")
                    QTimer.singleShot(500, self.accept)
                    break
            self.video_label.setPixmap(pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

        def get_barcode(self):
            return self.barcode_data

        def closeEvent(self, event):
            if hasattr(self, 'cap') and self.cap:
                self.cap.release()
            if hasattr(self, 'timer') and self.timer:
                self.timer.stop()
            event.accept()
