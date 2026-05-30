# database/dao/expense_dao.py
# -*- coding: utf-8 -*-

from decimal import Decimal
from typing import List, Dict, Optional
from database.dao.base_dao import BaseDAO
from database.utils import decimal_to_storage, storage_to_decimal, safe_decimal
from database.session import get_current_user_id
from database.dao.user_dao import UserDAO

class ExpenseDAO(BaseDAO):
    def get_all(self, search: str = None) -> List[Dict]:
        uid = get_current_user_id()
        query = "SELECT * FROM expenses WHERE user_id=?"
        params = [uid]
        if search:
            query += " AND description LIKE ?"
            params.append(f"%{search}%")
        query += " ORDER BY id DESC"
        rows = self._fetch_all(query, tuple(params))
        for row in rows:
            row['amount'] = storage_to_decimal(row.get('amount', '0'))
        return rows

    def add(self, amount: Decimal, date: str, description: str) -> int:
        uid = get_current_user_id()
        cur = self._execute("INSERT INTO expenses (user_id, amount, expense_date, description) VALUES (?,?,?,?)",
                            (uid, decimal_to_storage(amount), date, description))
        UserDAO().update_cash_balance(amount, add=False)
        self._commit()
        return cur.lastrowid

    def delete(self, exp_id: int):
        uid = get_current_user_id()
        row = self._fetch_one("SELECT amount FROM expenses WHERE id=? AND user_id=?", (exp_id, uid))
        if row:
            amount = storage_to_decimal(row['amount'])
            UserDAO().update_cash_balance(amount, add=True)
        self._execute("DELETE FROM expenses WHERE id=? AND user_id=?", (exp_id, uid))
        self._commit()
