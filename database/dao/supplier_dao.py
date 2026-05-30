from typing import List, Optional
import sqlite3
from database.dao.base_dao import BaseDAO
from database.utils import decimal_to_storage, storage_to_decimal, safe_decimal
from database.session import get_current_user_id
from database.models import Supplier

class SupplierDAO(BaseDAO):
    def get_all(self, search: str = None, limit: int = None, offset: int = None) -> List[Supplier]:
        uid = get_current_user_id()
        if not uid:
            return []
        query = "SELECT id, user_id, name, phone, address, CAST(balance AS TEXT) as balance FROM suppliers WHERE user_id = ?"
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
        suppliers = []
        for row in rows:
            suppliers.append(Supplier(
                id=row['id'],
                user_id=row['user_id'],
                name=row['name'],
                phone=row.get('phone', ''),
                address=row.get('address', ''),
                balance=storage_to_decimal(row.get('balance', '0'))
            ))
        return suppliers

    def get_count(self, search: str = None) -> int:
        uid = get_current_user_id()
        if not uid:
            return 0
        query = "SELECT COUNT(*) as cnt FROM suppliers WHERE user_id = ?"
        params = [uid]
        if search:
            query += " AND (name LIKE ? OR phone LIKE ?)"
            params.append(f"%{search}%")
            params.append(f"%{search}%")
        row = self._fetch_one(query, tuple(params))
        return row['cnt'] if row else 0

    def get_by_id(self, sid: int) -> Optional[Supplier]:
        uid = get_current_user_id()
        row = self._fetch_one("SELECT id, user_id, name, phone, address, CAST(balance AS TEXT) as balance FROM suppliers WHERE id=? AND user_id=?", (sid, uid))
        if row:
            return Supplier(
                id=row['id'], user_id=row['user_id'], name=row['name'],
                phone=row.get('phone', ''), address=row.get('address', ''),
                balance=storage_to_decimal(row.get('balance', '0'))
            )
        return None

    def add(self, name: str, phone: str = '', address: str = '') -> int:
        uid = get_current_user_id()
        try:
            cur = self._execute("INSERT INTO suppliers (user_id, name, phone, address, balance) VALUES (?,?,?,?,?)",
                                (uid, name, phone, address, '0'))
            self._commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            raise Exception("اسم المورد موجود مسبقاً")

    def update(self, sid: int, name: str, phone: str, address: str):
        uid = get_current_user_id()
        try:
            self._execute("UPDATE suppliers SET name=?, phone=?, address=? WHERE id=? AND user_id=?",
                          (name, phone, address, sid, uid))
            self._commit()
        except sqlite3.IntegrityError:
            raise Exception("اسم المورد موجود مسبقاً")

    def delete(self, sid: int):
        uid = get_current_user_id()
        cur = self._execute("SELECT id FROM invoices WHERE supplier_id=? AND user_id=? AND deleted_at IS NULL",
                            (sid, uid))
        if cur.fetchone():
            raise Exception("لا يمكن حذف المورد لوجود فواتير غير ملغاة مرتبطة به")
        self._execute("DELETE FROM suppliers WHERE id=? AND user_id=?", (sid, uid))
        self._commit()

    def update_balance(self, sid: int, delta: Decimal):
        uid = get_current_user_id()
        self._execute("UPDATE suppliers SET balance = CAST(COALESCE(balance, '0') AS TEXT) + ? WHERE id=? AND user_id=?",
                      (decimal_to_storage(delta), sid, uid))
        self._commit()
