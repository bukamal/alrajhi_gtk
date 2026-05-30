# fetch_exchange_rates.py
# -*- coding: utf-8 -*-

import requests
from decimal import Decimal
from database import exchange_rate_dao
from utils_pyqt5 import show_toast

def fetch_and_update_rates(parent=None):
    """جلب أسعار الصرف من API وتحديث قاعدة البيانات"""
    try:
        response = requests.get("https://api.exchangerate.host/latest?base=USD", timeout=10)
        if response.status_code != 200:
            raise Exception("فشل الاتصال بالخادم")
        data = response.json()
        rates = data.get('rates', {})
        updated = 0
        for code, rate in rates.items():
            if code in ['EUR', 'GBP', 'SAR', 'AED', 'SYP']:
                exchange_rate_dao.update(code, Decimal(str(1.0 / rate)))  # تخزين rate_to_usd
                updated += 1
        if updated > 0:
            show_toast(f"تم تحديث {updated} سعر صرف", "success", parent)
        else:
            show_toast("لم يتم العثور على عملات محدثة", "warning", parent)
    except requests.exceptions.ConnectionError:
        show_toast("لا يوجد اتصال بالإنترنت", "error", parent)
    except Exception as e:
        show_toast(f"خطأ: {str(e)}", "error", parent)
