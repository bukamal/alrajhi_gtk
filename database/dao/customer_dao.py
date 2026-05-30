from typing import List, Optional
import sqlite3
from database.dao.base_dao import BaseDAO
from database.utils import decimal_to_storage, storage_to_decimal, safe_decimal
from database.session import get_current_user_id
from database.models import Customer

class CustomerDAO(BaseDAO):
    def get_all(self, search: str = None, limit: int = None, offset: int = None) -> List[Customer]:
        uid = get_current_user_id()
        if not uid:
            return []
        query = "SELECT id, user_id, name, phone, address, CAST(balance AS TEXT) as balance FROM customers WHERE user_id = ?"
        params = [uid]
        if search:
            query += " AND (name LIKE ? OR phone LIKE ?)"
            params.append(f"%{search}%")
            params.append(f"%{search}%")
        query += " ORDER BY name"
        if limit is not None:
            query += f" LIMIT {limit}"
            if offset is not None:
                query += f" OFFSET {offset}"
        rows = self._fetch_all(query, tuple(params))
        customers = []
        for row in rows:
            customers.append(Customer(
                id=row['id'],
                user_id=row['user_id'],
                name=row['name'],
                phone=row.get('phone', ''),
                address=row.get('address', ''),
                balance=storage_to_decimal(row.get('balance', '0'))
            ))
        return customers

    def get_count(self, search: str = None) -> int:
        uid = get_current_user_id()
        if not uid:
            return 0
        query = "SELECT COUNT(*) as cnt FROM customers WHERE user_id = ?"
        params = [uid]
        if search:
            query += " AND (name LIKE ? OR phone LIKE ?)"
            params.append(f"%{search}%")
            params.append(f"%{search}%")
        row = self._fetch_one(query, tuple(params))
        return row['cnt'] if row else 0

    def get_by_id(self, cid: int) -> Optional[Customer]:
        uid = get_current_user_id()
        row = self._fetch_one("SELECT id, user_id, name, phone, address, CAST(balance AS TEXT) as balance FROM customers WHERE id=? AND user_id=?", (cid, uid))
        if row:
            return Customer(
                id=row['id'], user_id=row['user_id'], name=row['name'],
                phone=row.get('phone', ''), address=row.get('address', ''),
                balance=storage_to_decimal(row.get('balance', '0'))
            )
        return None

    def add(self, name: str, phone: str = '', address: str = '') -> int:
        uid = get_current_user_id()
        try:
            cur = self._execute("INSERT INTO customers (user_id, name, phone, address, balance) VALUES (?,?,?,?,?)",
                                (uid, name, phone, address, '0'))
            self._commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            raise Exception("اسم العميل موجود مسبقاً")

    def update(self, cid: int, name: str, phone: str, address: str):
        uid = get_current_user_id()
        try:
            self._execute("UPDATE customers SET name=?, phone=?, address=? WHERE id=? AND user_id=?",
                          (name, phone, address, cid, uid))
            self._commit()
        except sqlite3.IntegrityError:
            raise Exception("اسم العميل موجود مسبقاً")

    def delete(self, cid: int):
        uid = get_current_user_id()
        cur = self._execute("SELECT id FROM invoices WHERE customer_id=? AND user_id=? AND deleted_at IS NULL",
                            (cid, uid))
        if cur.fetchone():
            raise Exception("لا يمكن حذف العميل لوجود فواتير غير ملغاة مرتبطة به")
        self._execute("DELETE FROM customers WHERE id=? AND user_id=?", (cid, uid))
        self._commit()

    def update_balance(self, cid: int, delta: Decimal):
        uid = get_current_user_id()
        self._execute("UPDATE customers SET balance = CAST(COALESCE(balance, '0') AS TEXT) + ? WHERE id=? AND user_id=?",
                      (decimal_to_storage(delta), cid, uid))
        self._commit()
