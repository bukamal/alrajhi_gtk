# database/utils.py
# -*- coding: utf-8 -*-
"""
"""

from decimal import Decimal, getcontext
import hashlib
import secrets

# تعيين دقة عالية للعمليات المالية
getcontext().prec = 28

def decimal_to_storage(d: Decimal) -> str:
    """تحويل Decimal إلى نص للتخزين في قاعدة البيانات"""
    return str(d) if d is not None else '0'

def storage_to_decimal(s: str) -> Decimal:
    """تحويل نص مخزن إلى Decimal"""
    if s is None or s == '':
        return Decimal('0')
    try:
        return Decimal(s)
    except:
        return Decimal('0')

def safe_decimal(value) -> Decimal:
    """تحويل أي قيمة إلى Decimal بأمان"""
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except:
        return Decimal('0')

def hash_password(password: str) -> str:
    """تشفير كلمة المرور باستخدام SHA256 مع salt"""
    salt = secrets.token_hex(16)
    return hashlib.sha256((password + salt).encode()).hexdigest() + ':' + salt

def verify_password(password: str, hashed: str) -> bool:
    """التحقق من كلمة المرور"""
    try:
        hash_val, salt = hashed.split(':')
        return hash_val == hashlib.sha256((password + salt).encode()).hexdigest()
    except:
        return False
