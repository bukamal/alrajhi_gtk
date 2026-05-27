# -*- coding: utf-8 -*-
import os
import json
import base64
import hashlib
import uuid
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

LICENSE_STORAGE_KEY = 'alrajhi_license_v10'
SERVER_URL = 'https://license.manhal-almasriiii199119.workers.dev/activate'

PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAqFo0vsRBik7fUVfVY3neK7YNfatWQKfq6IacPAOwfxM4C43+sOjxZyTB15eF8zU+KsBMj1bPhqtbKOrfhVrEYAGTaUc8+SK16+vJCeDWP2vzVhHKZPNdg1gFPjgChAJr1lp72XASiA1NKgRZrp6S/9OWnMzjKA3Is6jAIJKThZqTjb01k7jJRTO2XlX6PpIPLYd4sZlkYsIXVntU6LpZ0FCHPMKvtC/1IlwTZylUcrpPqKeToRdtYKNSqxiXQmqUedWe6PxPDS5SYmTdn00q/8Divm3tZRTLYgj/tvDjD27MWtvFDFa34tzRwo4xHBlAEwW8NPbg/+CR+rlkwneeYQIDAQAB
-----END PUBLIC KEY-----"""

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

def xor_encrypt(data, key):
    result = []
    for i, ch in enumerate(data):
        result.append(chr(ord(ch) ^ ord(key[i % len(key)])))
    return base64.b64encode(''.join(result).encode()).decode()

def xor_decrypt(encrypted, key):
    try:
        decoded = base64.b64decode(encrypted).decode()
        result = []
        for i, ch in enumerate(decoded):
            result.append(chr(ord(ch) ^ ord(key[i % len(key)])))
        return ''.join(result)
    except:
        return ''

def verify_rsa_signature(data, signature_base64):
    try:
        public_key = serialization.load_pem_public_key(PUBLIC_KEY_PEM.encode(), backend=default_backend())
        signature = base64.b64decode(signature_base64)
        public_key.verify(signature, data.encode(), padding.PKCS1v15(), hashes.SHA256())
        return True
    except:
        return False

def online_activate(license_code):
    if not REQUESTS_AVAILABLE:
        raise Exception("مكتبة requests غير مثبتة. تأكد من تثبيتها أولاً.")
    fingerprint = get_or_create_device_id()
    try:
        response = requests.post(SERVER_URL, json={'licenseCode': license_code, 'fingerprint': fingerprint}, timeout=30)
        if response.status_code != 200:
            raise Exception(response.text or "فشل التفعيل")
        result = response.json()
        data_to_verify = f"{fingerprint}|{result['expirationDate']}"
        if not verify_rsa_signature(data_to_verify, result['signature']):
            raise Exception("توقيع غير صالح")
        now = int(datetime.now().timestamp() * 1000)
        license_data = {
            'key': license_code,
            'device': fingerprint,
            'activationDate': now,
            'expirationDate': result['expirationDate'],
            'lastOpened': now,
            'remainingSeconds': result.get('durationHours', 365*24) * 3600,
            'onlineActivated': True
        }
        encrypted = xor_encrypt(json.dumps(license_data), 'Alrajhi-License-2024-S3cr3t!K3y#')
        license_file = os.path.join(os.path.dirname(__file__), 'data', LICENSE_STORAGE_KEY)
        with open(license_file, 'w') as f:
            f.write(encrypted)
        return True
    except requests.exceptions.ConnectionError:
        raise Exception("لا يوجد اتصال بالإنترنت. يرجى التحقق من الاتصال.")
    except requests.exceptions.Timeout:
        raise Exception("انتهت مهلة الاتصال. حاول مرة أخرى.")

def check_activation():
    license_file = os.path.join(os.path.dirname(__file__), 'data', LICENSE_STORAGE_KEY)
    if not os.path.exists(license_file):
        return {'valid': False, 'reason': 'no_license'}
    try:
        with open(license_file, 'r') as f:
            encrypted = f.read().strip()
        decrypted = xor_decrypt(encrypted, 'Alrajhi-License-2024-S3cr3t!K3y#')
        data = json.loads(decrypted)
    except:
        os.remove(license_file)
        return {'valid': False, 'reason': 'corrupted'}
    now = int(datetime.now().timestamp() * 1000)
    current_fingerprint = get_or_create_device_id()
    if data.get('device') != current_fingerprint:
        os.remove(license_file)
        return {'valid': False, 'reason': 'device_mismatch'}
    if now > data['expirationDate'] + 60000:
        os.remove(license_file)
        return {'valid': False, 'reason': 'expired'}
    if data.get('lastOpened') and now < data.get('lastOpened', 0) - 60000:
        os.remove(license_file)
        return {'valid': False, 'reason': 'clock_tampered'}
    data['lastOpened'] = now
    data['remainingSeconds'] = max(0, (data['expirationDate'] - now) // 1000)
    encrypted = xor_encrypt(json.dumps(data), 'Alrajhi-License-2024-S3cr3t!K3y#')
    with open(license_file, 'w') as f:
        f.write(encrypted)
    return {'valid': True, 'remainingSeconds': data['remainingSeconds']}
