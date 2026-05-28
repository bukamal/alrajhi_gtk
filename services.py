# -*- coding: utf-8 -*-
from database import db

def calculate_invoice_total(lines):
    return sum(line['total'] for line in lines)

def validate_customer_balance(customer_id, amount):
    customers = db.get_customers()
    customer = next((c for c in customers if c['id'] == customer_id), None)
    return customer['balance'] >= amount if customer else False

def validate_supplier_balance(supplier_id, amount):
    suppliers = db.get_suppliers()
    supplier = next((s for s in suppliers if s['id'] == supplier_id), None)
    return supplier['balance'] >= amount if supplier else False

def get_item_stock(item_id):
    items = db.get_items()
    item = next((i for i in items if i['id'] == item_id), None)
    return item['available'] if item else 0
