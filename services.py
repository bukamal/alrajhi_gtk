# -*- coding: utf-8 -*-
from database import customer_dao, supplier_dao, item_dao

def calculate_invoice_total(lines):
    return sum(line['total'] for line in lines)

def validate_customer_balance(customer_id, amount):
    customer = customer_dao.get_by_id(customer_id)
    return customer.balance >= amount if customer else False

def validate_supplier_balance(supplier_id, amount):
    supplier = supplier_dao.get_by_id(supplier_id)
    return supplier.balance >= amount if supplier else False

def get_item_stock(item_id):
    item = item_dao.get_by_id(item_id)
    return item.available if item else 0
