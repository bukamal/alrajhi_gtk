# database/utils.py
# -*- coding: utf-8 -*-
from decimal import Decimal, getcontext
import hashlib
import secrets
import base64

getcontext().prec = 28

def decimal_to_storage(d: Decimal) -> str:
    return str(d) if d is not None else '0'

def storage_to_decimal(s: str) -> Decimal:
    if s is None or s == '':
        return Decimal('0')
    try:
        return Decimal(s)
    except:
        return Decimal('0')

def safe_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except:
        return Decimal('0')

def hash_password(password: str) -> str:
    """تشفير كلمة المرور باستخدام PBKDF2 (تنسيق: pbkdf2:iterations:salt:hash)"""
    salt = secrets.token_hex(16)
    iterations = 100000
    dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), iterations, dklen=32)
    hash_b64 = base64.b64encode(dk).decode()
    return f"pbkdf2:{iterations}:{salt}:{hash_b64}"

def verify_password(password: str, hashed: str) -> bool:
    """التحقق من كلمة المرور مع دعم التنسيق القديم (hash:salt) والجديد (pbkdf2)"""
    try:
        if hashed.startswith('pbkdf2:'):
            parts = hashed.split(':')
            if len(parts) != 4:
                return False
            iterations = int(parts[1])
            salt = parts[2]
            stored_hash = parts[3]
            dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), iterations, dklen=32)
            computed = base64.b64encode(dk).decode()
            return computed == stored_hash
        else:
            # التنسيق القديم: hash:salt
            hash_val, salt = hashed.split(':')
            return hash_val == hashlib.sha256((password + salt).encode()).hexdigest()
    except:
        return False

def needs_upgrade(hashed: str) -> bool:
    """التحقق مما إذا كان الهاش قديماً (لا يبدأ بـ pbkdf2:)"""
    return not hashed.startswith('pbkdf2:')
