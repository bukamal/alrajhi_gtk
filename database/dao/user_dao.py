# database/dao/user_dao.py
# -*- coding: utf-8 -*-

from typing import Optional, Dict, List
import secrets
from datetime import datetime
from decimal import Decimal
from database.dao.base_dao import BaseDAO
from database.utils import hash_password, verify_password, decimal_to_storage, storage_to_decimal, safe_decimal
from database.session import get_current_user_id, get_current_user_role, UserSession
from database.models import User

class UserDAO(BaseDAO):
    def login(self, username: str, password: str) -> bool:
        cur = self._execute("SELECT id, password_hash, role FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        if row and verify_password(password, row['password_hash']):
            cur.execute("UPDATE users SET last_login = datetime('now') WHERE id = ?", (row['id'],))
            self._commit()
            UserSession.set_current_user(row['id'], row['role'])
            return True
        return False

    def get_current_user(self) -> Optional[User]:
        uid = UserSession.get_current_user_id()
        if not uid:
            return None
        row = self._fetch_one("SELECT id, username, password_hash, role, full_name, created_at, last_login, CAST(cash_balance AS TEXT) as cash_balance FROM users WHERE id = ?", (uid,))
        if row:
            return User(
                id=row['id'],
                username=row['username'],
                password_hash=row['password_hash'],
                role=row['role'],
                full_name=row.get('full_name', ''),
                created_at=row.get('created_at', ''),
                last_login=row.get('last_login', ''),
                cash_balance=storage_to_decimal(row.get('cash_balance', '0'))
            )
        return None

    def register(self, username: str, password: str, full_name: str = '', role: str = 'user') -> bool:
        try:
            uid = secrets.token_hex(8)
            phash = hash_password(password)
            now = datetime.now().isoformat()
            self._execute("""
                INSERT INTO users (id, username, password_hash, role, full_name, created_at, cash_balance)
                VALUES (?,?,?,?,?,?,?)
            """, (uid, username, phash, role, full_name, now, '0'))
            self._commit()
            return True
        except Exception:
            return False

    def get_all(self) -> List[User]:
        if UserSession.get_current_user_role() != 'admin':
            return []
        rows = self._fetch_all("SELECT id, username, role, full_name, created_at, last_login, CAST(cash_balance AS TEXT) as cash_balance FROM users")
        users = []
        for row in rows:
            users.append(User(
                id=row['id'],
                username=row['username'],
                password_hash='',  # لا نعيد كلمة المرور
                role=row['role'],
                full_name=row.get('full_name', ''),
                created_at=row.get('created_at', ''),
                last_login=row.get('last_login', ''),
                cash_balance=storage_to_decimal(row.get('cash_balance', '0'))
            ))
        return users

    def delete(self, user_id: str) -> bool:
        if UserSession.get_current_user_role() != 'admin' or user_id == 'admin':
            return False
        for tbl in ['customers','suppliers','categories','items','invoices','vouchers','expenses','accounts','inventory_movements']:
            self._execute(f"DELETE FROM {tbl} WHERE user_id = ?", (user_id,))
        self._execute("DELETE FROM users WHERE id = ?", (user_id,))
        self._commit()
        return True

    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        cur = self._execute("SELECT password_hash FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        if row and verify_password(old_password, row['password_hash']):
            new_hash = hash_password(new_password)
            self._execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
            self._commit()
            return True
        return False

    def get_cash_balance(self) -> Decimal:
        uid = UserSession.get_current_user_id()
        if not uid:
            return Decimal('0')
        row = self._fetch_one("SELECT CAST(cash_balance AS TEXT) FROM users WHERE id = ?", (uid,))
        return storage_to_decimal(row['cash_balance']) if row else Decimal('0')

    def update_cash_balance(self, amount: Decimal, add: bool = True):
        uid = UserSession.get_current_user_id()
        if not uid:
            return
        sign = 1 if add else -1
        self._execute("UPDATE users SET cash_balance = CAST(COALESCE(cash_balance, '0') AS TEXT) + ? WHERE id = ?",
                      (decimal_to_storage(sign * amount), uid))
        self._commit()
