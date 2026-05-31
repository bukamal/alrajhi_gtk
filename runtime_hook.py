import os
import sys
import ctypes

def load_zbar_libs():
    """تحميل مكتبات zbar يدوياً عند بدء التشغيل (خاصة لبيئة Windows المجمعة)"""
    if getattr(sys, 'frozen', False) and sys.platform == 'win32':
        base_path = sys._MEIPASS
        # محاولة تحميل libzbar-64.dll
        dll_path = os.path.join(base_path, 'libzbar-64.dll')
        if os.path.exists(dll_path):
            ctypes.CDLL(dll_path)
        # محاولة تحميل libiconv-2.dll
        iconv_path = os.path.join(base_path, 'libiconv-2.dll')
        if os.path.exists(iconv_path):
            ctypes.CDLL(iconv_path)

load_zbar_libs()
