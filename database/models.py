# database/models.py
# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional, List

@dataclass
class User:
    id: str
    username: str
    password_hash: str
    role: str = 'user'
    full_name: str = ''
    created_at: str = ''
    last_login: str = ''
    cash_balance: Decimal = Decimal('0')

@dataclass
class Customer:
    id: int
    user_id: str
    name: str
    phone: str = ''
    address: str = ''
    balance: Decimal = Decimal('0')

@dataclass
class Supplier:
    id: int
    user_id: str
    name: str
    phone: str = ''
    address: str = ''
    balance: Decimal = Decimal('0')

@dataclass
class Category:
    id: int
    user_id: str
    name: str

@dataclass
class ItemUnit:
    id: int
    item_id: int
    unit_name: str
    conversion_factor: Decimal = Decimal('1')

@dataclass
class Item:
    id: int
    user_id: str
    name: str
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    item_type: str = 'مخزون'
    purchase_price: Decimal = Decimal('0')
    selling_price: Decimal = Decimal('0')
    quantity: Decimal = Decimal('0')
    unit: str = ''
    average_cost: Decimal = Decimal('0')
    purchase_qty: Decimal = Decimal('0')
    sale_qty: Decimal = Decimal('0')
    purchase_count: int = 0
    sale_count: int = 0
    last_purchase_date: Optional[str] = None
    last_sale_date: Optional[str] = None
    barcode: Optional[str] = None
    units_data: Optional[str] = None
    item_units: List[ItemUnit] = field(default_factory=list)

    @property
    def available(self) -> Decimal:
        return self.quantity

    @property
    def total_value(self) -> Decimal:
        return self.available * self.average_cost

@dataclass
class InvoiceLine:
    id: int
    invoice_id: int
    item_id: int
    item_name: Optional[str] = None
    description: str = ''
    quantity: Decimal = Decimal('0')
    unit_price: Decimal = Decimal('0')
    total: Decimal = Decimal('0')
    unit: str = ''
    quantity_in_base: Decimal = Decimal('0')
    unit_cost: Decimal = Decimal('0')
    cost_amount: Decimal = Decimal('0')

@dataclass
class Invoice:
    id: int
    user_id: str
    type: str
    customer_id: Optional[int] = None
    supplier_id: Optional[int] = None
    customer_name: Optional[str] = None
    supplier_name: Optional[str] = None
    date: str = ''
    reference: str = ''
    notes: str = ''
    total: Decimal = Decimal('0')
    paid: Decimal = Decimal('0')
    status: str = 'active'
    deleted_at: Optional[str] = None
    lines: List[InvoiceLine] = field(default_factory=list)

@dataclass
class Voucher:
    id: int
    user_id: str
    type: str
    date: str
    amount: Decimal = Decimal('0')
    description: str = ''
    reference: str = ''
    customer_id: Optional[int] = None
    supplier_id: Optional[int] = None
    invoice_id: Optional[int] = None
    customer_name: Optional[str] = None
    supplier_name: Optional[str] = None

@dataclass
class Expense:
    id: int
    user_id: str
    amount: Decimal = Decimal('0')
    expense_date: str = ''
    description: str = ''

@dataclass
class ExchangeRate:
    currency_code: str
    rate_to_usd: Decimal
    updated_at: str = ''
