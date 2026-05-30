# database/dao/item_dao.py (الملف كاملاً مع get_count)
from decimal import Decimal
from typing import List, Optional, Dict, Any
import sqlite3
from database.dao.base_dao import BaseDAO
from database.utils import decimal_to_storage, storage_to_decimal, safe_decimal
from database.session import get_current_user_id
from database.models import Item, ItemUnit
from database.dao.inventory_movement_dao import InventoryMovementDAO

class ItemDAO(BaseDAO):
    def get_items(self, search: str = None, limit: int = None, offset: int = None) -> List[Item]:
        uid = get_current_user_id()
        if not uid:
            return []
        query = """
            SELECT 
                i.id, i.user_id, i.name, i.category_id, i.item_type,
                CAST(i.purchase_price AS TEXT) as purchase_price,
                CAST(i.selling_price AS TEXT) as selling_price,
                CAST(i.quantity AS TEXT) as quantity,
                i.unit,
                CAST(i.average_cost AS TEXT) as average_cost,
                i.barcode,
                c.name as category_name,
                COALESCE(p.purchase_qty, 0) as purchase_qty,
                COALESCE(s.sale_qty, 0) as sale_qty,
                COALESCE(p.purchase_count, 0) as purchase_count,
                COALESCE(s.sale_count, 0) as sale_count,
                p.last_purchase_date,
                s.last_sale_date,
                GROUP_CONCAT(u.unit_name || ':' || u.conversion_factor) as units_data
            FROM items i
            LEFT JOIN categories c ON i.category_id = c.id
            LEFT JOIN (
                SELECT 
                    il.item_id,
                    CAST(SUM(CAST(il.quantity_in_base AS TEXT)) AS TEXT) as purchase_qty,
                    COUNT(*) as purchase_count,
                    MAX(inv.date) as last_purchase_date
                FROM invoice_lines il
                JOIN invoices inv ON il.invoice_id = inv.id
                WHERE inv.type = 'purchase' AND inv.deleted_at IS NULL AND inv.user_id = ?
                GROUP BY il.item_id
            ) p ON i.id = p.item_id
            LEFT JOIN (
                SELECT 
                    il.item_id,
                    CAST(SUM(CAST(il.quantity_in_base AS TEXT)) AS TEXT) as sale_qty,
                    COUNT(*) as sale_count,
                    MAX(inv.date) as last_sale_date
                FROM invoice_lines il
                JOIN invoices inv ON il.invoice_id = inv.id
                WHERE inv.type = 'sale' AND inv.deleted_at IS NULL AND inv.user_id = ?
                GROUP BY il.item_id
            ) s ON i.id = s.item_id
            LEFT JOIN item_units u ON u.item_id = i.id
            WHERE i.user_id = ?
        """
        params = [uid, uid, uid]
        if search:
            query += " AND (i.name LIKE ? OR i.barcode LIKE ?)"
            params.append(f"%{search}%")
            params.append(f"%{search}%")
        query += " GROUP BY i.id ORDER BY i.name"
        if limit is not None:
            query += f" LIMIT {limit}"
            if offset is not None:
                query += f" OFFSET {offset}"
        rows = self._fetch_all(query, tuple(params))
        items = []
        for row in rows:
            item = Item(
                id=row['id'],
                user_id=row['user_id'],
                name=row['name'],
                category_id=row['category_id'],
                category_name=row.get('category_name'),
                item_type=row.get('item_type', 'مخزون'),
                purchase_price=storage_to_decimal(row.get('purchase_price', '0')),
                selling_price=storage_to_decimal(row.get('selling_price', '0')),
                quantity=storage_to_decimal(row.get('quantity', '0')),
                unit=row.get('unit', ''),
                average_cost=storage_to_decimal(row.get('average_cost', '0')),
                purchase_qty=storage_to_decimal(row.get('purchase_qty', '0')),
                sale_qty=storage_to_decimal(row.get('sale_qty', '0')),
                purchase_count=row.get('purchase_count', 0),
                sale_count=row.get('sale_count', 0),
                last_purchase_date=row.get('last_purchase_date'),
                last_sale_date=row.get('last_sale_date'),
                barcode=row.get('barcode'),
                units_data=row.get('units_data')
            )
            if row.get('units_data'):
                for unit_str in row['units_data'].split(','):
                    parts = unit_str.split(':')
                    if len(parts) == 2:
                        unit_name, factor = parts
                        item.item_units.append(ItemUnit(
                            id=0, item_id=item.id,
                            unit_name=unit_name,
                            conversion_factor=safe_decimal(factor)
                        ))
            items.append(item)
        return items

    def get_count(self, search: str = None) -> int:
        uid = get_current_user_id()
        if not uid:
            return 0
        query = "SELECT COUNT(*) as cnt FROM items WHERE user_id = ?"
        params = [uid]
        if search:
            query += " AND (name LIKE ? OR barcode LIKE ?)"
            params.append(f"%{search}%")
            params.append(f"%{search}%")
        row = self._fetch_one(query, tuple(params))
        return row['cnt'] if row else 0

    # باقي الدوال (get_by_barcode, add, update, delete, units) كما هي
    def get_by_barcode(self, barcode: str) -> Optional[Item]:
        uid = get_current_user_id()
        if not barcode:
            return None
        row = self._fetch_one("SELECT * FROM items WHERE barcode = ? AND user_id = ?", (barcode, uid))
        if row:
            return Item(
                id=row['id'], user_id=row['user_id'], name=row['name'],
                category_id=row['category_id'], item_type=row.get('item_type', 'مخزون'),
                purchase_price=storage_to_decimal(row.get('purchase_price', '0')),
                selling_price=storage_to_decimal(row.get('selling_price', '0')),
                quantity=storage_to_decimal(row.get('quantity', '0')),
                unit=row.get('unit', ''),
                average_cost=storage_to_decimal(row.get('average_cost', '0')),
                purchase_qty=storage_to_decimal(row.get('purchase_qty', '0')),
                sale_qty=storage_to_decimal(row.get('sale_qty', '0')),
                barcode=row.get('barcode')
            )
        return None

    def get_by_id(self, item_id: int) -> Optional[Item]:
        items = self.get_items()
        for it in items:
            if it.id == item_id:
                return it
        return None

    def add(self, data: Dict[str, Any]) -> int:
        uid = get_current_user_id()
        try:
            cur = self._execute("""
                INSERT INTO items (user_id, name, category_id, item_type, purchase_price, selling_price, quantity, unit, average_cost, purchase_qty, sale_qty, barcode)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (uid, data['name'], data.get('category_id'), data.get('item_type', 'مخزون'),
                  decimal_to_storage(safe_decimal(data.get('purchase_price', 0))),
                  decimal_to_storage(safe_decimal(data.get('selling_price', 0))),
                  decimal_to_storage(safe_decimal(data.get('quantity', 0))),
                  data.get('unit', ''),
                  decimal_to_storage(safe_decimal(data.get('average_cost', data.get('purchase_price', 0)))),
                  decimal_to_storage(safe_decimal(data.get('quantity', 0))), '0',
                  data.get('barcode')))
            self._commit()
            item_id = cur.lastrowid
            qty = safe_decimal(data.get('quantity', 0))
            if qty > 0:
                InventoryMovementDAO().record_movement(
                    item_id, 'adjustment', qty,
                    safe_decimal(data.get('purchase_price', 0)), None
                )
            return item_id
        except sqlite3.IntegrityError as e:
            if 'UNIQUE constraint failed: items.barcode' in str(e):
                raise Exception("الباركود موجود مسبقاً")
            raise Exception("اسم المادة موجود مسبقاً")

    def update(self, item_id: int, data: Dict[str, Any]):
        uid = get_current_user_id()
        try:
            self._execute("""
                UPDATE items SET name=?, category_id=?, item_type=?, purchase_price=?, selling_price=?, quantity=?, unit=?, average_cost=?, barcode=?
                WHERE id=? AND user_id=?
            """, (data['name'], data.get('category_id'), data.get('item_type'),
                  decimal_to_storage(safe_decimal(data.get('purchase_price', 0))),
                  decimal_to_storage(safe_decimal(data.get('selling_price', 0))),
                  decimal_to_storage(safe_decimal(data.get('quantity', 0))),
                  data.get('unit', ''),
                  decimal_to_storage(safe_decimal(data.get('average_cost', data.get('purchase_price', 0)))),
                  data.get('barcode'), item_id, uid))
            self._commit()
        except sqlite3.IntegrityError as e:
            if 'UNIQUE constraint failed: items.barcode' in str(e):
                raise Exception("الباركود موجود مسبقاً")
            raise Exception("اسم المادة موجود مسبقاً")

    def delete(self, item_id: int):
        uid = get_current_user_id()
        cur = self._execute("""
            SELECT il.id FROM invoice_lines il
            JOIN invoices inv ON il.invoice_id = inv.id
            WHERE il.item_id = ? AND inv.deleted_at IS NULL LIMIT 1
        """, (item_id,))
        if cur.fetchone():
            raise Exception("لا يمكن حذف المادة لاستخدامها في فواتير (غير ملغاة)")
        self._execute("DELETE FROM item_units WHERE item_id=?", (item_id,))
        self._execute("DELETE FROM inventory_movements WHERE item_id=?", (item_id,))
        self._execute("DELETE FROM items WHERE id=? AND user_id=?", (item_id, uid))
        self._commit()

    def get_units(self, item_id: int) -> List[ItemUnit]:
        rows = self._fetch_all("SELECT id, item_id, unit_name, CAST(conversion_factor AS TEXT) as conversion_factor FROM item_units WHERE item_id = ?", (item_id,))
        units = []
        for row in rows:
            units.append(ItemUnit(
                id=row['id'], item_id=row['item_id'],
                unit_name=row['unit_name'],
                conversion_factor=storage_to_decimal(row.get('conversion_factor', '1'))
            ))
        return units

    def add_unit(self, item_id: int, unit_name: str, conversion_factor: Decimal) -> int:
        cur = self._execute("INSERT INTO item_units (item_id, unit_name, conversion_factor) VALUES (?,?,?)",
                            (item_id, unit_name, decimal_to_storage(conversion_factor)))
        self._commit()
        return cur.lastrowid

    def delete_unit(self, unit_id: int):
        self._execute("DELETE FROM item_units WHERE id = ?", (unit_id,))
        self._commit()

    def clear_units(self, item_id: int):
        self._execute("DELETE FROM item_units WHERE item_id = ?", (item_id,))
        self._commit()
