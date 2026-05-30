import os
import sys
import ctypes

def load_zbar_libs():
    """تحميل مكتبات zbar يدوياً عند بدء التشغيل"""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
        libiconv_path = os.path.join(base_path, 'libiconv.dll')
        libzbar_path = os.path.join(base_path, 'libzbar-64.dll')
        if os.path.exists(libiconv_path):
            ctypes.CDLL(libiconv_path)
        if os.path.exists(libzbar_path):
            ctypes.CDLL(libzbar_path)

load_zbar_libs()
