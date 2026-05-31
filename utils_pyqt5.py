# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QMessageBox
from datetime import datetime
import traceback
import os
import shutil

def format_currency(amount, settings=None):
    from config import format_currency_with_settings
    return format_currency_with_settings(amount, settings)

def format_number(amount, decimals=2):
    try:
        return f"{amount:,.{decimals}f}"
    except:
        return str(amount)

def format_date(date_str):
    if not date_str:
        return ''
    try:
        return datetime.fromisoformat(date_str).strftime("%Y-%m-%d")
    except:
        return date_str

def show_toast(message, msg_type='info', parent=None):
    try:
        from views_pyqt5.toast_notification import ToastNotification
        if parent:
            toast = ToastNotification(message, msg_type, parent)
            toast.show_toast()
        else:
            QMessageBox.information(parent, "معلومة", message)
    except ImportError:
        QMessageBox.information(parent, "معلومة", message)

def safe_execute(func, error_msg="حدث خطأ", parent=None):
    """تنفيذ دالة مع التقاط الأخطاء وعرضها بشكل موحد"""
    try:
        return func()
    except Exception as e:
        tb = traceback.format_exc()
        show_toast(f"{error_msg}: {str(e)}", "error", parent)
        print(tb)
        return None

def create_auto_backup():
    """إنشاء نسخة احتياطية تلقائية من قاعدة البيانات (تدعم التشفير والعادي)"""
    from database.connection import DB_PATH
    if not os.path.exists(DB_PATH):
        return None
    backup_dir = os.path.join(os.path.dirname(DB_PATH), 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(backup_dir, f'alrajhi_backup_{timestamp}.db')
    try:
        shutil.copy2(DB_PATH, backup_file)
        # حذف النسخ القديمة (احتفظ بآخر 30 نسخة فقط)
        backups = sorted([f for f in os.listdir(backup_dir) if f.startswith('alrajhi_backup_')])
        while len(backups) > 30:
            os.remove(os.path.join(backup_dir, backups.pop(0)))
        return backup_file
    except Exception as e:
        print(f"فشل النسخ الاحتياطي التلقائي: {e}")
        return None
