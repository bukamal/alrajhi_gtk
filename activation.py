# -*- coding: utf-8 -*-
"""
- تخزين معرف الجهاز مشفراً
- تخزين بيانات الترخيص مشفرة بتشفير مؤكد مع HMAC للتحقق من السلامة
- التحقق الدوري من الخادم (كل 30 يوماً)
"""

import os
import json
import base64
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime
from typing import Dict, Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ========== إعدادات ثابتة ==========
LICENSE_STORAGE_KEY = 'alrajhi_license_v10'
SERVER_URL = 'https://license.manhal-almasriiii199119.workers.dev/activate'
PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAqFo0vsRBik7fUVfVY3neK7YNfatWQKfq6IacPAOwfxM4C43+sOjxZyTB15eF8zU+KsBMj1bPhqtbKOrfhVrEYAGTaUc8+SK16+vJCeDWP2vzVhHKZPNdg1gFPjgChAJr1lp72XASiA1NKgRZrp6S/9OWnMzjKA3Is6jAIJKThZqTjb01k7jJRTO2XlX6PpIPLYd4sZlkYsIXVntU6LpZ0FCHPMKvtC/1IlwTZylUcrpPqKeToRdtYKNSqxiXQmqUedWe6PxPDS5SYmTdn00q/8Divm3tZRTLYgj/tvDjD27MWtvFDFa34tzRwo4xHBlAEwW8NPbg/+CR+rlkwneeYQIDAQAB
-----END PUBLIC KEY-----"""

# ثابت التشفير (يُستخدم مع PBKDF2، ليس مفتاحاً مباشراً)
ENCRYPTION_SALT = b'alrajhi_salt_2024_v2'
HMAC_SALT = b'alrajhi_hmac_salt_2024'
DEVICE_ID_SALT = b'fixed_salt_for_device_id'

# فترة الصلاحية المحلية للترخيص (بالأيام)
LOCAL_VALIDITY_DAYS = 30

def derive_key(password: bytes, salt: bytes, length: int = 32, iterations: int = 100000) -> bytes:
    """اشتقاق مفتاح باستخدام PBKDF2 (hashlib built-in)"""
    return hashlib.pbkdf2_hmac('sha256', password, salt, iterations, dklen=length)

def get_encryption_key(device_id: str) -> bytes:
    """اشتقاق مفتاح AES-256 من device_id + ثابت"""
    return derive_key(device_id.encode(), ENCRYPTION_SALT)

def get_hmac_key() -> bytes:
    """مفتاح HMAC ثابت (يمكن تغييره في كل إصدار)"""
    return derive_key(HMAC_SALT, b'hmac_salt', length=32)

def encrypt_data(data: str, device_id: str) -> str:
    """تشفير البيانات باستخدام AES-GCM، وإرجاع base64(nonce + ciphertext + tag)"""
    key = get_encryption_key(device_id)
    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(12)
    ciphertext = aesgcm.encrypt(nonce, data.encode(), None)
    # nonce + ciphertext (ciphertext يحتوي على الـ tag في نهايته)
    combined = nonce + ciphertext
    return base64.b64encode(combined).decode()

def decrypt_data(encrypted: str, device_id: str) -> str:
    """فك تشفير البيانات"""
    key = get_encryption_key(device_id)
    aesgcm = AESGCM(key)
    combined = base64.b64decode(encrypted)
    nonce = combined[:12]
    ciphertext = combined[12:]
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode()

def compute_hmac(data: str) -> str:
    """حساب HMAC للبيانات"""
    key = get_hmac_key()
    h = hmac.new(key, data.encode(), hashlib.sha256)
    return h.hexdigest()

def verify_hmac(data: str, signature: str) -> bool:
    """التحقق من HMAC"""
    return hmac.compare_digest(compute_hmac(data), signature)

def get_or_create_device_id() -> str:
    """الحصول على معرف الجهاز (مشفراً)"""
    device_file = os.path.join(os.path.dirname(__file__), 'data', 'device_id.enc')
    os.makedirs(os.path.dirname(device_file), exist_ok=True)
    
    if os.path.exists(device_file):
        try:
            with open(device_file, 'r') as f:
                encrypted = f.read().strip()
            # نستخدم مفتاح ثابت لتشفير device_id نفسه (مشتق من قيمة ثابتة)
            fixed_key = derive_key(b'fixed_key_for_device_id', DEVICE_ID_SALT)
            aesgcm = AESGCM(fixed_key)
            combined = base64.b64decode(encrypted)
            nonce = combined[:12]
            ciphertext = combined[12:]
            device_id = aesgcm.decrypt(nonce, ciphertext, None).decode()
            return device_id
        except Exception:
            pass
    
    device_id = str(uuid.uuid4())
    fixed_key = derive_key(b'fixed_key_for_device_id', DEVICE_ID_SALT)
    aesgcm = AESGCM(fixed_key)
    nonce = secrets.token_bytes(12)
    ciphertext = aesgcm.encrypt(nonce, device_id.encode(), None)
    combined = nonce + ciphertext
    with open(device_file, 'w') as f:
        f.write(base64.b64encode(combined).decode())
    return device_id

def verify_rsa_signature(data: str, signature_base64: str) -> bool:
    """التحقق من توقيع RSA (نفس الكود القديم)"""
    try:
        from cryptography.hazmat.primitives import serialization, hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.backends import default_backend
        public_key = serialization.load_pem_public_key(PUBLIC_KEY_PEM.encode(), backend=default_backend())
        signature = base64.b64decode(signature_base64)
        public_key.verify(signature, data.encode(), padding.PKCS1v15(), hashes.SHA256())
        return True
    except Exception:
        return False

def online_activate(license_code: str) -> Tuple[bool, str]:
    """تفعيل عبر الإنترنت، مع تخزين آمن"""
    try:
        import requests
    except ImportError:
        return False, "مكتبة requests غير مثبتة"
    fingerprint = get_or_create_device_id()
    try:
        response = requests.post(SERVER_URL, json={'licenseCode': license_code, 'fingerprint': fingerprint}, timeout=30)
        if response.status_code != 200:
            return False, response.text or "فشل التفعيل"
        result = response.json()
        data_to_verify = f"{fingerprint}|{result['expirationDate']}"
        if not verify_rsa_signature(data_to_verify, result['signature']):
            return False, "توقيع غير صالح"
        now = int(datetime.now().timestamp() * 1000)
        license_data = {
            'key': license_code,
            'device': fingerprint,
            'activationDate': now,
            'expirationDate': result['expirationDate'],
            'lastOpened': now,
            'remainingSeconds': result.get('durationHours', 365*24) * 3600,
            'onlineActivated': True,
            'lastServerCheck': now
        }
        # تحويل البيانات إلى JSON وتشفيرها
        json_data = json.dumps(license_data)
        encrypted = encrypt_data(json_data, fingerprint)
        # حساب HMAC للبيانات المشفرة (لضمان عدم التلاعب)
        hmac_sig = compute_hmac(encrypted)
        # تخزين البيانات المشفرة + HMAC
        license_file = os.path.join(os.path.dirname(__file__), 'data', LICENSE_STORAGE_KEY)
        with open(license_file, 'w') as f:
            f.write(f"{encrypted}\n{hmac_sig}")
        return True, ""
    except requests.exceptions.ConnectionError:
        return False, "لا يوجد اتصال بالإنترنت. يرجى التحقق من الاتصال."
    except requests.exceptions.Timeout:
        return False, "انتهت مهلة الاتصال بالخادم. حاول مرة أخرى أو تحقق من سرعة اتصالك."
    except Exception as e:
        return False, f"خطأ غير متوقع: {str(e)}"

def check_activation() -> Dict:
    """التحقق من الترخيص مع دعم المهلة المحلية والتحقق الدوري من الخادم"""
    try:
        import requests
    except ImportError:
        return {'valid': False, 'reason': 'requests_not_installed'}
    license_file = os.path.join(os.path.dirname(__file__), 'data', LICENSE_STORAGE_KEY)
    if not os.path.exists(license_file):
        return {'valid': False, 'reason': 'no_license'}
    try:
        with open(license_file, 'r') as f:
            lines = f.read().strip().split('\n')
            if len(lines) != 2:
                raise ValueError("ملف تالف")
            encrypted, hmac_sig = lines[0], lines[1]
        # التحقق من HMAC أولاً
        if not verify_hmac(encrypted, hmac_sig):
            os.remove(license_file)
            return {'valid': False, 'reason': 'corrupted'}
        # فك التشفير
        device_id = get_or_create_device_id()
        decrypted = decrypt_data(encrypted, device_id)
        data = json.loads(decrypted)
    except Exception:
        if os.path.exists(license_file):
            os.remove(license_file)
        return {'valid': False, 'reason': 'corrupted'}

    now = int(datetime.now().timestamp() * 1000)
    current_fingerprint = get_or_create_device_id()
    if data.get('device') != current_fingerprint:
        os.remove(license_file)
        return {'valid': False, 'reason': 'device_mismatch'}
    
    # التحقق من صلاحية الترخيص
    if now > data['expirationDate'] + 60000:
        os.remove(license_file)
        return {'valid': False, 'reason': 'expired'}
    
    # التحقق من عدم التلاعب بالوقت
    if data.get('lastOpened') and now < data.get('lastOpened', 0) - 60000:
        os.remove(license_file)
        return {'valid': False, 'reason': 'clock_tampered'}
    
    # تحديث آخر فتح
    data['lastOpened'] = now
    data['remainingSeconds'] = max(0, (data['expirationDate'] - now) // 1000)
    
    # المهلة المحلية: إذا مر أكثر من LOCAL_VALIDITY_DAYS منذ آخر اتصال بالخادم، نحتاج إلى إعادة التحقق عبر الإنترنت
    last_server_check = data.get('lastServerCheck', 0)
    if now - last_server_check > LOCAL_VALIDITY_DAYS * 24 * 3600 * 1000:
        try:
            # محاولة التحقق من الخادم
            response = requests.post(SERVER_URL, json={'licenseCode': data['key'], 'fingerprint': current_fingerprint}, timeout=10)
            if response.status_code == 200:
                result = response.json()
                # تحديث بيانات الترخيص من الخادم
                data['expirationDate'] = result['expirationDate']
                data['remainingSeconds'] = result.get('durationHours', 365*24) * 3600
                data['lastServerCheck'] = now
            # إذا فشل، لا نفعل شيئاً ونقبل الترخيص المحلي مؤقتاً
        except Exception:
            # لا يوجد اتصال، نقبل الترخيص المحلي مؤقتاً
            pass
    
    # إعادة حفظ البيانات بعد التحديث
    json_data = json.dumps(data)
    encrypted = encrypt_data(json_data, device_id)
    hmac_sig = compute_hmac(encrypted)
    with open(license_file, 'w') as f:
        f.write(f"{encrypted}\n{hmac_sig}")
    
    return {'valid': True, 'remainingSeconds': data['remainingSeconds']}
