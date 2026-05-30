# -*- coding: utf-8 -*-
from database import user_dao, Session, get_current_user_id, get_current_user_role
from database.utils import hash_password, verify_password
from typing import Optional, Dict

def login(username: str, password: str) -> bool:
    return user_dao.login(username, password)

def logout():
    Session.clear_current_user()

def get_current_user() -> Optional[Dict]:
    uid = Session.get_current_user_id()
    if not uid:
        return None
    user = user_dao.get_current_user()
    if user:
        return {
            'id': user.id,
            'username': user.username,
            'role': user.role,
            'full_name': user.full_name
        }
    return None

def is_authenticated() -> bool:
    return Session.get_current_user_id() is not None

def is_admin() -> bool:
    return Session.get_current_user_role() == 'admin'

def register_user(username: str, password: str, full_name: str = '', role: str = 'user') -> bool:
    return user_dao.register(username, password, full_name, role)

def delete_user(user_id: str) -> bool:
    return user_dao.delete(user_id)

def get_all_users() -> list:
    users = user_dao.get_all()
    return [{
        'id': u.id,
        'username': u.username,
        'role': u.role,
        'full_name': u.full_name,
        'created_at': u.created_at,
        'last_login': u.last_login,
        'cash_balance': u.cash_balance
    } for u in users]

def change_password(user_id: str, old_password: str, new_password: str) -> bool:
    return user_dao.change_password(user_id, old_password, new_password)

# ========== نظام الصلاحيات المتقدم ==========
PERMISSIONS = {
    'admin': ['*'],
    'accountant': [
        'view_dashboard', 'view_invoices', 'create_invoice', 'edit_invoice', 'delete_invoice',
        'view_items', 'create_item', 'edit_item', 'view_reports',
        'view_customers', 'edit_customers', 'view_suppliers', 'edit_suppliers',
        'view_vouchers', 'create_voucher', 'delete_voucher'
    ],
    'cashier': [
        'view_dashboard', 'view_invoices', 'create_invoice',
        'view_customers', 'view_suppliers', 'view_vouchers', 'create_voucher'
    ],
    'inventory': [
        'view_items', 'create_item', 'edit_item', 'delete_item', 'view_invoices'
    ],
    'viewer': [
        'view_dashboard', 'view_invoices', 'view_items', 'view_reports'
    ]
}

def has_permission(permission: str) -> bool:
    role = Session.get_current_user_role()
    if not role:
        return False
    perms = PERMISSIONS.get(role, [])
    if '*' in perms:
        return True
    return permission in perms

def can_view_dashboard() -> bool: return has_permission('view_dashboard')
def can_view_invoices() -> bool: return has_permission('view_invoices')
def can_create_invoice() -> bool: return has_permission('create_invoice')
def can_edit_invoice() -> bool: return has_permission('edit_invoice')
def can_delete_invoice() -> bool: return has_permission('delete_invoice')
def can_view_items() -> bool: return has_permission('view_items')
def can_create_item() -> bool: return has_permission('create_item')
def can_edit_item() -> bool: return has_permission('edit_item')
def can_delete_item() -> bool: return has_permission('delete_item')
def can_view_customers() -> bool: return has_permission('view_customers')
def can_edit_customers() -> bool: return has_permission('edit_customers')
def can_view_suppliers() -> bool: return has_permission('view_suppliers')
def can_edit_suppliers() -> bool: return has_permission('edit_suppliers')
def can_view_vouchers() -> bool: return has_permission('view_vouchers')
def can_create_voucher() -> bool: return has_permission('create_voucher')
def can_delete_voucher() -> bool: return has_permission('delete_voucher')
def can_view_reports() -> bool: return has_permission('view_reports')
