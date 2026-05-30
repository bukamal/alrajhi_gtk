# database/dao/category_dao.py
# -*- coding: utf-8 -*-

from typing import List, Dict, Optional
import sqlite3
from database.dao.base_dao import BaseDAO
from database.session import get_current_user_id

class CategoryDAO(BaseDAO):
    def get_all(self, search: str = None) -> List[Dict]:
        uid = get_current_user_id()
        if not uid:
            return []
        query = f"SELECT * FROM categories WHERE user_id = ?"
        params = [uid]
        if search:
            query += " AND name LIKE ?"
            params.append(f"%{search}%")
        query += " ORDER BY name"
        return self._fetch_all(query, tuple(params))

    def add(self, name: str) -> int:
        uid = get_current_user_id()
        try:
            cur = self._execute("INSERT INTO categories (user_id, name) VALUES (?,?)", (uid, name))
            self._commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            raise Exception("اسم التصنيف موجود مسبقاً")

    def update(self, cid: int, name: str):
        uid = get_current_user_id()
        try:
            self._execute(f"UPDATE categories SET name=? WHERE id=? AND user_id=?", (name, cid, uid))
            self._commit()
        except sqlite3.IntegrityError:
            raise Exception("اسم التصنيف موجود مسبقاً")

    def delete(self, cid: int):
        uid = get_current_user_id()
        cur = self._execute("SELECT id FROM items WHERE category_id=? AND user_id=?", (cid, uid))
        if cur.fetchone():
            raise Exception("لا يمكن حذف التصنيف لوجود مواد مرتبطة به")
        self._execute(f"DELETE FROM categories WHERE id=? AND user_id=?", (cid, uid))
        self._commit()
