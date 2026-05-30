# -*- coding: utf-8 -*-
"""
- تخزين معرف الجهاز مشفراً مع نسخة احتياطية وHMAC
- تخزين بيانات الترخيص مشفرة بتشفير مؤكد مع دعم الإصدارات
- التحقق الدوري من الخادم (كل 60 يوماً)
- دعم التشفير القديم للتوافق مع الإصدارات السابقة
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

# ثوابت التشفير
ENCRYPTION_SALT = b'alrajhi_salt_2024_v2'
HMAC_SALT = b'alrajhi_hmac_salt_2024'
DEVICE_ID_SALT = b'fixed_salt_for_device_id'
DEVICE_ID_FIXED_KEY = b'fixed_key_for_device_id_v2'
DEVICE_ID_BACKUP_FILE = os.path.join(os.path.dirname(__file__), 'data', 'device_id_backup.txt')

# فترة الصلاحية المحلية للترخيص (بالأيام)
LOCAL_VALIDITY_DAYS = 60

# إصدار التشفير الحالي وعدد تكرارات PBKDF2
ENCRYPTION_VERSION = 1
CURRENT_ITERATIONS = 200000  # زيادة الأمان

_CACHED_DEVICE_ID = None


def derive_key(password: bytes, salt: bytes, length: int = 32, iterations: int = CURRENT_ITERATIONS) -> bytes:
    """اشتقاق مفتاح باستخدام PBKDF2 (hashlib built-in)"""
    return hashlib.pbkdf2_hmac('sha256', password, salt, iterations, dklen=length)


def get_encryption_key(device_id: str, version: int = ENCRYPTION_VERSION) -> bytes:
    """اشتقاق مفتاح AES-256 من device_id + ثابت حسب الإصدار"""
    if version == 1:
        return derive_key(device_id.encode(), ENCRYPTION_SALT, length=32, iterations=CURRENT_ITERATIONS)
    else:
        raise ValueError(f"إصدار تشفير غير مدعوم: {version}")


def get_hmac_key() -> bytes:
    """مفتاح HMAC ثابت (يمكن تغييره في كل إصدار)"""
    return derive_key(HMAC_SALT, b'hmac_salt', length=32)


def encrypt_data(data: str, device_id: str) -> str:
    """
    تشفير البيانات باستخدام AES-GCM، وإرجاع base64(version + nonce + ciphertext)
    حيث version هو بايت واحد (1 للإصدار الحالي)
    """
    version = ENCRYPTION_VERSION
    key = get_encryption_key(device_id, version)
    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(12)
    ciphertext = aesgcm.encrypt(nonce, data.encode(), None)
    # تجميع: [version (1 byte)] + [nonce (12 bytes)] + [ciphertext]
    combined = bytes([version]) + nonce + ciphertext
    return base64.b64encode(combined).decode()


def decrypt_data(encrypted: str, device_id: str) -> str:
    """
    فك تشفير البيانات مع دعم الإصدارات المختلفة والتوافق مع البيانات القديمة.
    """
    combined = base64.b64decode(encrypted)
    if len(combined) < 13:
        # بيانات قديمة (بدون version) - محاولة فك تشفير بالطريقة القديمة
        key = get_encryption_key(device_id, version=1)
        if len(combined) >= 12:
            nonce = combined[:12]
            ciphertext = combined[12:]
            aesgcm = AESGCM(key)
            try:
                plaintext = aesgcm.decrypt(nonce, ciphertext, None)
                return plaintext.decode()
            except Exception:
                pass
        raise ValueError("البيانات المشفرة تالفة أو غير متوافقة")

    version = combined[0]
    nonce = combined[1:13]
    ciphertext = combined[13:]

    if version == 1:
        key = get_encryption_key(device_id, version)
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode()
    else:
        raise ValueError(f"إصدار تشفير غير مدعوم: {version}")


def compute_hmac(data: str) -> str:
    """حساب HMAC للبيانات"""
    key = get_hmac_key()
    h = hmac.new(key, data.encode(), hashlib.sha256)
    return h.hexdigest()


def verify_hmac(data: str, signature: str) -> bool:
    """التحقق من HMAC"""
    return hmac.compare_digest(compute_hmac(data), signature)


def get_cached_device_id() -> str:
    """الحصول على معرف الجهاز المخبأ (للاستخدام المتكرر)"""
    global _CACHED_DEVICE_ID
    if _CACHED_DEVICE_ID is None:
        _CACHED_DEVICE_ID = get_or_create_device_id()
    return _CACHED_DEVICE_ID


def get_or_create_device_id() -> str:
    """الحصول على معرف الجهاز (مشفراً) مع آلية استرجاع من نسخة احتياطية"""
    device_file = os.path.join(os.path.dirname(__file__), 'data', 'device_id.enc')
    os.makedirs(os.path.dirname(device_file), exist_ok=True)

    # محاولة فك التشفير أولاً
    if os.path.exists(device_file):
        try:
            with open(device_file, 'r') as f:
                encrypted = f.read().strip()
            fixed_key = derive_key(DEVICE_ID_FIXED_KEY, DEVICE_ID_SALT)
            aesgcm = AESGCM(fixed_key)
            combined = base64.b64decode(encrypted)
            nonce = combined[:12]
            ciphertext = combined[12:]
            device_id = aesgcm.decrypt(nonce, ciphertext, None).decode()
            if device_id and len(device_id) >= 32:
                return device_id
        except Exception as e:
            print(f"فشل فك تشفير device_id: {e}")

    # محاولة القراءة من النسخة الاحتياطية (نص عادي مع HMAC)
    if os.path.exists(DEVICE_ID_BACKUP_FILE):
        try:
            with open(DEVICE_ID_BACKUP_FILE, 'r') as f:
                backup_data = f.read().strip()
                parts = backup_data.split('|')
                if len(parts) == 2:
                    device_id, hmac_sig = parts
                    key = derive_key(DEVICE_ID_FIXED_KEY, b'backup_hmac_salt')
                    computed = hmac.new(key, device_id.encode(), hashlib.sha256).hexdigest()
                    if hmac.compare_digest(computed, hmac_sig):
                        # إعادة تشفير device_id وحفظه في الملف الأصلي
                        fixed_key = derive_key(DEVICE_ID_FIXED_KEY, DEVICE_ID_SALT)
                        aesgcm = AESGCM(fixed_key)
                        nonce = secrets.token_bytes(12)
                        ciphertext = aesgcm.encrypt(nonce, device_id.encode(), None)
                        combined = nonce + ciphertext
                        with open(device_file, 'w') as f:
                            f.write(base64.b64encode(combined).decode())
                        return device_id
        except Exception as e:
            print(f"فشل قراءة النسخة الاحتياطية: {e}")

    # إنشاء device_id جديد
    device_id = str(uuid.uuid4())
    fixed_key = derive_key(DEVICE_ID_FIXED_KEY, DEVICE_ID_SALT)
    aesgcm = AESGCM(fixed_key)
    nonce = secrets.token_bytes(12)
    ciphertext = aesgcm.encrypt(nonce, device_id.encode(), None)
    combined = nonce + ciphertext
    with open(device_file, 'w') as f:
        f.write(base64.b64encode(combined).decode())

    # حفظ نسخة احتياطية مع HMAC
    key = derive_key(DEVICE_ID_FIXED_KEY, b'backup_hmac_salt')
    hmac_sig = hmac.new(key, device_id.encode(), hashlib.sha256).hexdigest()
    with open(DEVICE_ID_BACKUP_FILE, 'w') as f:
        f.write(f"{device_id}|{hmac_sig}")

    return device_id


def verify_rsa_signature(data: str, signature_base64: str) -> bool:
    """التحقق من توقيع RSA"""
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
            'remainingSeconds': result.get('durationHours', 60 * 24) * 3600,  # 60 يوماً افتراضياً
            'onlineActivated': True,
            'lastServerCheck': now
        }
        json_data = json.dumps(license_data)
        encrypted = encrypt_data(json_data, fingerprint)
        hmac_sig = compute_hmac(encrypted)
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

        if not verify_hmac(encrypted, hmac_sig):
            os.remove(license_file)
            return {'valid': False, 'reason': 'corrupted'}

        device_id = get_or_create_device_id()
        decrypted = decrypt_data(encrypted, device_id)
        data = json.loads(decrypted)

        # ترقية التشفير القديم إذا كان بدون version
        if len(base64.b64decode(encrypted)) < 13:
            json_data = json.dumps(data)
            new_encrypted = encrypt_data(json_data, device_id)
            new_hmac = compute_hmac(new_encrypted)
            with open(license_file, 'w') as f:
                f.write(f"{new_encrypted}\n{new_hmac}")

    except Exception:
        if os.path.exists(license_file):
            os.remove(license_file)
        return {'valid': False, 'reason': 'corrupted'}

    now = int(datetime.now().timestamp() * 1000)
    current_fingerprint = get_or_create_device_id()
    if data.get('device') != current_fingerprint:
        os.remove(license_file)
        return {'valid': False, 'reason': 'device_mismatch'}

    # التحقق من صلاحية الترخيص - تصحيح: لا نضيف 60000
    if now > data['expirationDate']:
        os.remove(license_file)
        return {'valid': False, 'reason': 'expired'}

    # التحقق من عدم التلاعب بالوقت
    if data.get('lastOpened') and now < data.get('lastOpened', 0) - 60000:
        os.remove(license_file)
        return {'valid': False, 'reason': 'clock_tampered'}

    # تحديث آخر فتح
    data['lastOpened'] = now
    data['remainingSeconds'] = max(0, (data['expirationDate'] - now) // 1000)

    # المهلة المحلية
    last_server_check = data.get('lastServerCheck', 0)
    if now - last_server_check > LOCAL_VALIDITY_DAYS * 24 * 3600 * 1000:
        try:
            response = requests.post(SERVER_URL, json={'licenseCode': data['key'], 'fingerprint': current_fingerprint}, timeout=10)
            if response.status_code == 200:
                result = response.json()
                data['expirationDate'] = result['expirationDate']
                data['remainingSeconds'] = result.get('durationHours', 60 * 24) * 3600
                data['lastServerCheck'] = now
        except Exception:
            pass

    # إعادة حفظ البيانات بعد التحديث
    json_data = json.dumps(data)
    encrypted = encrypt_data(json_data, device_id)
    hmac_sig = compute_hmac(encrypted)
    with open(license_file, 'w') as f:
        f.write(f"{encrypted}\n{hmac_sig}")

    return {'valid': True, 'remainingSeconds': data['remainingSeconds']}
