# database/dao/exchange_rate_dao.py
# -*- coding: utf-8 -*-

from decimal import Decimal
from typing import List, Dict, Optional
from datetime import datetime
from database.dao.base_dao import BaseDAO
from database.utils import decimal_to_storage, storage_to_decimal, safe_decimal

class ExchangeRateDAO(BaseDAO):
    def get_all(self) -> List[Dict]:
        rows = self._fetch_all("SELECT currency_code, CAST(rate_to_usd AS TEXT) as rate_to_usd, updated_at FROM exchange_rates ORDER BY currency_code")
        for row in rows:
            row['rate_to_usd'] = storage_to_decimal(row['rate_to_usd'])
        return rows

    def get_rate(self, currency_code: str) -> Decimal:
        row = self._fetch_one("SELECT CAST(rate_to_usd AS TEXT) as rate_to_usd FROM exchange_rates WHERE currency_code = ?", (currency_code,))
        if row:
            return storage_to_decimal(row['rate_to_usd'])
        return Decimal('1.0')

    def add(self, currency_code: str, rate_to_usd: Decimal):
        self._execute("INSERT INTO exchange_rates (currency_code, rate_to_usd, updated_at) VALUES (?,?,?)",
                      (currency_code, decimal_to_storage(rate_to_usd), datetime.now().isoformat()))
        self._commit()

    def update(self, currency_code: str, rate_to_usd: Decimal):
        self._execute("UPDATE exchange_rates SET rate_to_usd = ?, updated_at = ? WHERE currency_code = ?",
                      (decimal_to_storage(rate_to_usd), datetime.now().isoformat(), currency_code))
        self._commit()

    def delete(self, currency_code: str) -> bool:
        if currency_code == 'USD':
            return False
        self._execute("DELETE FROM exchange_rates WHERE currency_code = ?", (currency_code,))
        self._commit()
        return True
