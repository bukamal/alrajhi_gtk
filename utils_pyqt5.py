# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QMessageBox
from datetime import datetime

def format_currency(amount, settings=None):
    from config import get_currency_settings
    s = settings or get_currency_settings()
    symbol = s.get('symbol', '$')
    try:
        formatted = f"{amount:,.{s.get('decimals',2)}f}"
    except:
        formatted = str(amount)
    return f"{formatted} {symbol}"

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
