# database/dao/voucher_dao.py
# -*- coding: utf-8 -*-

from decimal import Decimal
from typing import List, Dict, Optional
from database.dao.base_dao import BaseDAO
from database.utils import decimal_to_storage, storage_to_decimal, safe_decimal
from database.session import get_current_user_id
from database.dao.customer_dao import CustomerDAO
from database.dao.supplier_dao import SupplierDAO
from database.dao.user_dao import UserDAO

class VoucherDAO(BaseDAO):
    def get_all(self, search: str = None) -> List[Dict]:
        uid = get_current_user_id()
        query = "SELECT * FROM vouchers WHERE user_id=?"
        params = [uid]
        if search:
            query += " AND (description LIKE ? OR reference LIKE ?)"
            params.append(f"%{search}%")
            params.append(f"%{search}%")
        query += " ORDER BY id DESC"
        rows = self._fetch_all(query, tuple(params))
        vouchers = []
        for row in rows:
            v = dict(row)
            v['amount'] = storage_to_decimal(v.get('amount', '0'))
            vouchers.append(v)
        return vouchers

    def add(self, data: Dict) -> int:
        uid = get_current_user_id()
        amount = safe_decimal(data['amount'])
        voucher_type = data['type']

        cur = self._execute("""
            INSERT INTO vouchers (user_id, type, date, amount, description, reference, customer_id, supplier_id, invoice_id)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (uid, voucher_type, data['date'], decimal_to_storage(amount),
              data.get('description', ''), data.get('reference', ''),
              data.get('customer_id'), data.get('supplier_id'), data.get('invoice_id')))
        vid = cur.lastrowid

        sign = 1 if voucher_type == 'receipt' else -1
        UserDAO().update_cash_balance(amount, add=(sign == 1))

        if data.get('customer_id'):
            CustomerDAO().update_balance(data['customer_id'], -amount)
        elif data.get('supplier_id'):
            SupplierDAO().update_balance(data['supplier_id'], -amount)

        self._commit()
        return vid

    def delete(self, vid: int):
        uid = get_current_user_id()
        row = self._fetch_one("SELECT type, amount, customer_id, supplier_id FROM vouchers WHERE id=? AND user_id=?", (vid, uid))
        if row:
            amount = storage_to_decimal(row['amount'])
            voucher_type = row['type']
            sign = -1 if voucher_type == 'receipt' else 1
            UserDAO().update_cash_balance(amount, add=(sign == 1))
            if row['customer_id']:
                CustomerDAO().update_balance(row['customer_id'], amount)
            elif row['supplier_id']:
                SupplierDAO().update_balance(row['supplier_id'], amount)
        self._execute("DELETE FROM vouchers WHERE id=? AND user_id=?", (vid, uid))
        self._commit()
