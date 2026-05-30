# database/dao/base_dao.py
# -*- coding: utf-8 -*-
"""
"""

from typing import List, Dict, Any, Optional, Tuple, Union
from database.connection import DatabaseConnection

class BaseDAO:
    def __init__(self):
        self.db = DatabaseConnection()

    def _execute(self, sql: str, params: Union[tuple, list] = ()):
        """تنفيذ استعلام وإرجاع cursor"""
        return self.db.execute(sql, params)

    def _executemany(self, sql: str, params_list: list):
        return self.db.executemany(sql, params_list)

    def _executescript(self, script: str):
        return self.db.executescript(script)

    def _fetch_one(self, sql: str, params: Union[tuple, list] = ()) -> Optional[Dict]:
        cur = self._execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None

    def _fetch_all(self, sql: str, params: Union[tuple, list] = ()) -> List[Dict]:
        cur = self._execute(sql, params)
        return [dict(row) for row in cur.fetchall()]

    def _commit(self):
        self.db.commit()

    def _rollback(self):
        self.db.rollback()

    def begin_transaction(self):
        self.db.begin_transaction()
