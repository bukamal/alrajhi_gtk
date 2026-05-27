# -*- coding: utf-8 -*-
import os
import json
from datetime import datetime, timedelta
import uuid

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
        'expiration': (datetime.now() + timedelta(days=365)).isoformat()
    }
    os.makedirs(os.path.dirname(LICENSE_FILE), exist_ok=True)
    with open(LICENSE_FILE, 'w') as f:
        json.dump(data, f)
    return True

def get_currency_settings():
    settings_file = os.path.join(os.path.dirname(__file__), 'data', 'settings.json')
    if os.path.exists(settings_file):
        with open(settings_file, 'r') as f:
            return json.load(f)
    return {'symbol': '$', 'decimals': 2, 'number_format': 'western'}

def save_currency_settings(settings):
    settings_file = os.path.join(os.path.dirname(__file__), 'data', 'settings.json')
    os.makedirs(os.path.dirname(settings_file), exist_ok=True)
    with open(settings_file, 'w') as f:
        json.dump(settings, f)
