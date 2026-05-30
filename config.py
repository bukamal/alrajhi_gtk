# -*- coding: utf-8 -*-
import os
import json
from datetime import datetime, timedelta
import uuid
from PyQt5.QtCore import QObject, pyqtSignal

class CurrencyNotifier(QObject):
    currency_changed = pyqtSignal(str)

currency_notifier = CurrencyNotifier()

LICENSE_FILE = os.path.join(os.path.dirname(__file__), 'data', 'license.json')

def get_or_create_device_id():
    device_file = os.path.join(os.path.dirname(__file__), 'data', 'device_id.txt')
    os.makedirs(os.path.dirname(device_file), exist_ok=True)
    if os.path.exists(device_file):
        with open(device_file, 'r') as f:
            return f.read().strip()
    device_id = str(uuid.uuid4())
    with open(device_file, 'w') as f:
        f.write(device_id)
    return device_id

def check_activation():
    if not os.path.exists(LICENSE_FILE):
        return False
    try:
        with open(LICENSE_FILE, 'r') as f:
            data = json.load(f)
        if data.get('device') != get_or_create_device_id():
            return False
        expiry = datetime.fromisoformat(data['expiration'])
        if datetime.now() > expiry:
            return False
        return True
    except:
        return False

def save_activation(license_key):
    if not license_key:
        raise ValueError("مفتاح التفعيل مطلوب")
    import hashlib
    data = {
        'key': hashlib.sha256(license_key.encode()).hexdigest(),
        'device': get_or_create_device_id(),
        'expiration': (datetime.now() + timedelta(days=60)).isoformat()  # 60 يوماً
    }
    os.makedirs(os.path.dirname(LICENSE_FILE), exist_ok=True)
    with open(LICENSE_FILE, 'w') as f:
        json.dump(data, f)
    return True

def get_currency_symbol(code):
    symbols = {
        'USD': '$', 'EUR': '€', 'GBP': '£', 'SAR': '﷼', 'AED': 'د.إ', 'SYP': 'ل.س'
    }
    return symbols.get(code, code)

_current_currency_settings = None

def get_currency_settings():
    global _current_currency_settings
    if _current_currency_settings is not None:
        return _current_currency_settings
    settings_file = os.path.join(os.path.dirname(__file__), 'data', 'currency_settings.json')
    if os.path.exists(settings_file):
        with open(settings_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = {}
    data['decimals'] = 2
    _current_currency_settings = {
        'base_currency': data.get('base_currency', 'USD'),
        'display_currency': data.get('display_currency', 'USD'),
        'decimals': 2,
        'symbol_position': data.get('symbol_position', 'after'),
        'use_conversion': data.get('use_conversion', False)
    }
    return _current_currency_settings

def save_currency_settings(settings):
    global _current_currency_settings
    settings['decimals'] = 2
    settings_file = os.path.join(os.path.dirname(__file__), 'data', 'currency_settings.json')
    os.makedirs(os.path.dirname(settings_file), exist_ok=True)
    with open(settings_file, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
    _current_currency_settings = None
    get_currency_settings()
    currency_notifier.currency_changed.emit(_current_currency_settings['display_currency'])

def refresh_currency_settings():
    global _current_currency_settings
    _current_currency_settings = None
    get_currency_settings()
    currency_notifier.currency_changed.emit(_current_currency_settings['display_currency'])

def convert_currency(amount, from_curr, to_curr):
    if from_curr == to_curr:
        return amount
    from database import exchange_rate_dao
    from_rate = exchange_rate_dao.get_rate(from_curr)
    to_rate = exchange_rate_dao.get_rate(to_curr)
    return amount * (from_rate / to_rate)

def format_currency_with_settings(amount, settings=None):
    if settings is None:
        settings = get_currency_settings()
    base_curr = settings.get('base_currency', 'USD')
    display_curr = settings.get('display_currency', 'USD')
    decimals = 2
    symbol_pos = settings.get('symbol_position', 'after')
    use_conversion = settings.get('use_conversion', False)

    if use_conversion:
        amount = convert_currency(amount, base_curr, display_curr)

    try:
        formatted = f"{amount:,.{decimals}f}"
    except:
        formatted = str(amount)
    symbol = get_currency_symbol(display_curr)
    if symbol_pos == 'before':
        return f"{symbol} {formatted}"
    else:
        return f"{formatted} {symbol}"

def get_current_currency_symbol():
    settings = get_currency_settings()
    display_curr = settings.get('display_currency', 'USD')
    return get_currency_symbol(display_curr)
