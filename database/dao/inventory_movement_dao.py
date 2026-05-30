# database/dao/inventory_movement_dao.py
# -*- coding: utf-8 -*-

from decimal import Decimal
from datetime import datetime
from typing import Optional, List, Dict
from database.dao.base_dao import BaseDAO
from database.utils import decimal_to_storage, storage_to_decimal, safe_decimal
from database.session import get_current_user_id

class InventoryMovementDAO(BaseDAO):
    def record_movement(self, item_id: int, movement_type: str, quantity: Decimal,
                        unit_cost: Decimal, reference_id: Optional[int] = None):
        """تسجيل حركة مخزون جديدة وإعادة حساب متوسط التكلفة والكمية"""
        uid = get_current_user_id()
        self._execute("""
            INSERT INTO inventory_movements (item_id, user_id, movement_type, quantity, unit_cost, reference_id, movement_date)
            VALUES (?,?,?,?,?,?,?)
        """, (item_id, uid, movement_type, decimal_to_storage(quantity),
              decimal_to_storage(unit_cost), reference_id, datetime.now().isoformat()))
        self._commit()
        self._recalculate_average_cost(item_id)
        self._update_quantity(item_id)

    def _recalculate_average_cost(self, item_id: int) -> Decimal:
        """إعادة حساب متوسط التكلفة للمادة بناءً على حركات الشراء"""
        # استخدام CAST(... AS TEXT) ثم التحويل في Python لتجنب فقدان الدقة
        cur = self._execute("""
            SELECT 
                CAST(SUM(CAST(quantity AS TEXT)) AS TEXT) as total_qty,
                CAST(SUM(CAST(quantity AS TEXT) * CAST(unit_cost AS TEXT)) AS TEXT) as total_cost
            FROM inventory_movements
            WHERE item_id = ? AND movement_type = 'purchase'
        """, (item_id,))
        row = cur.fetchone()
        total_qty = storage_to_decimal(row['total_qty'] or '0')
        total_cost = storage_to_decimal(row['total_cost'] or '0')
        avg = total_cost / total_qty if total_qty > 0 else Decimal('0')
        self._execute("UPDATE items SET average_cost = ? WHERE id = ?", (decimal_to_storage(avg), item_id))
        self._commit()
        return avg

    def _update_quantity(self, item_id: int) -> Decimal:
        """تحديث الكمية الحالية للمادة بناءً على جميع الحركات"""
        cur = self._execute("""
            SELECT CAST(SUM(
                CASE 
                    WHEN movement_type IN ('purchase','adjustment') 
                    THEN CAST(quantity AS TEXT)
                    ELSE CAST(CAST(quantity AS TEXT) AS TEXT) * -1
                END
            ) AS TEXT) as total_qty
            FROM inventory_movements
            WHERE item_id = ?
        """, (item_id,))
        row = cur.fetchone()
        new_qty = storage_to_decimal(row['total_qty'] or '0')
        self._execute("UPDATE items SET quantity = ? WHERE id = ?", (decimal_to_storage(new_qty), item_id))
        self._commit()
        return new_qty

    def get_movements(self, item_id: int) -> List[Dict]:
        uid = get_current_user_id()
        rows = self._fetch_all("""
            SELECT movement_type, 
                   CAST(quantity AS TEXT) as quantity,
                   CAST(unit_cost AS TEXT) as unit_cost,
                   movement_date, reference_id
            FROM inventory_movements
            WHERE item_id = ? AND user_id = ?
            ORDER BY movement_date DESC
        """, (item_id, uid))
        for row in rows:
            row['quantity'] = storage_to_decimal(row['quantity'])
            row['unit_cost'] = storage_to_decimal(row['unit_cost'] or '0')
        return rows

    def reverse_last_movement(self, item_id: int, movement_type: str):
        """حذف آخر حركة من نوع معين (لتراجع الفاتورة)"""
        if movement_type == 'purchase':
            self._execute("""
                DELETE FROM inventory_movements
                WHERE item_id = ? AND movement_type = 'purchase'
                ORDER BY id DESC LIMIT 1
            """, (item_id,))
        elif movement_type == 'sale':
            self._execute("""
                DELETE FROM inventory_movements
                WHERE item_id = ? AND movement_type = 'sale'
                ORDER BY id DESC LIMIT 1
            """, (item_id,))
        else:
            return
        self._commit()
        self._recalculate_average_cost(item_id)
        self._update_quantity(item_id)
