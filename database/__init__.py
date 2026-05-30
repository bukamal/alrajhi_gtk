# database/__init__.py
# -*- coding: utf-8 -*-

from database.connection import DatabaseConnection, get_db_connection, init_db
from database.session import UserSession, get_current_user_id, get_current_user_role
from database.utils import (
    decimal_to_storage, storage_to_decimal, safe_decimal,
    hash_password, verify_password
)

Session = UserSession

# DAOs
from database.dao.user_dao import UserDAO
from database.dao.customer_dao import CustomerDAO
from database.dao.supplier_dao import SupplierDAO
from database.dao.category_dao import CategoryDAO
from database.dao.item_dao import ItemDAO
from database.dao.invoice_dao import InvoiceDAO
from database.dao.voucher_dao import VoucherDAO
from database.dao.expense_dao import ExpenseDAO
from database.dao.exchange_rate_dao import ExchangeRateDAO
from database.dao.inventory_movement_dao import InventoryMovementDAO
from database.dao.reporting_dao import ReportingDAO

user_dao = UserDAO()
customer_dao = CustomerDAO()
supplier_dao = SupplierDAO()
category_dao = CategoryDAO()
item_dao = ItemDAO()
invoice_dao = InvoiceDAO()
voucher_dao = VoucherDAO()
expense_dao = ExpenseDAO()
exchange_rate_dao = ExchangeRateDAO()
inventory_dao = InventoryMovementDAO()
reporting_dao = ReportingDAO()

__all__ = [
    'Session', 'UserSession',
    'DatabaseConnection', 'get_db_connection', 'init_db',
    'get_current_user_id', 'get_current_user_role',
    'decimal_to_storage', 'storage_to_decimal', 'safe_decimal',
    'hash_password', 'verify_password',
    'user_dao', 'customer_dao', 'supplier_dao', 'category_dao',
    'item_dao', 'invoice_dao', 'voucher_dao', 'expense_dao',
    'exchange_rate_dao', 'inventory_dao', 'reporting_dao',
]
