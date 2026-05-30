from decimal import Decimal
from datetime import datetime
from typing import List, Dict, Optional
from database.dao.base_dao import BaseDAO
from database.utils import decimal_to_storage, storage_to_decimal, safe_decimal
from database.session import get_current_user_id
from database.models import Invoice, InvoiceLine
from database.dao.inventory_movement_dao import InventoryMovementDAO
from database.dao.customer_dao import CustomerDAO
from database.dao.supplier_dao import SupplierDAO
from database.dao.user_dao import UserDAO

class InvoiceDAO(BaseDAO):
    def create_invoice(self, data: Dict) -> int:
        uid = get_current_user_id()
        total = safe_decimal(data['total'])
        paid = safe_decimal(data.get('paid_amount', 0))
        if paid < 0:
            paid = Decimal('0')
        if data['type'] == 'sale' and paid > total:
            paid = total
        elif data['type'] == 'purchase' and paid > total:
            paid = total

        self.begin_transaction()
        try:
            cur = self._execute("""
                INSERT INTO invoices (user_id, type, customer_id, supplier_id, date, reference, notes, total, paid, status)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (uid, data['type'], data.get('customer_id'), data.get('supplier_id'),
                  data['date'], data.get('reference', ''), data.get('notes', ''),
                  decimal_to_storage(total), decimal_to_storage(paid), 'active'))
            invoice_id = cur.lastrowid

            for line in data['lines']:
                base_qty = safe_decimal(line.get('base_qty', line['quantity']))
                unit_cost = safe_decimal(line['unit_price'])
                self._execute("""
                    INSERT INTO invoice_lines (invoice_id, item_id, quantity, unit_price, total, unit, quantity_in_base, unit_cost, cost_amount)
                    VALUES (?,?,?,?,?,?,?,?,?)
                """, (invoice_id, line['item_id'],
                      decimal_to_storage(safe_decimal(line['quantity'])),
                      decimal_to_storage(unit_cost),
                      decimal_to_storage(safe_decimal(line['total'])),
                      line.get('unit', ''),
                      decimal_to_storage(base_qty),
                      decimal_to_storage(unit_cost), '0'))
                line_id = cur.lastrowid
                if data['type'] == 'purchase':
                    InventoryMovementDAO().record_movement(line['item_id'], 'purchase', base_qty, unit_cost, invoice_id)
                    cost_amt = unit_cost * base_qty
                    self._execute("UPDATE invoice_lines SET cost_amount = ? WHERE id = ?", (decimal_to_storage(cost_amt), line_id))
                else:
                    item = self._fetch_one("SELECT CAST(average_cost AS TEXT) as average_cost FROM items WHERE id=? AND user_id=?", (line['item_id'], uid))
                    avg_cost = storage_to_decimal(item['average_cost']) if item else Decimal('0')
                    cost_amt = base_qty * avg_cost
                    self._execute("UPDATE invoice_lines SET cost_amount = ? WHERE id = ?", (decimal_to_storage(cost_amt), line_id))
                    InventoryMovementDAO().record_movement(line['item_id'], 'sale', base_qty, unit_cost, invoice_id)

            if data['type'] == 'sale' and data.get('customer_id'):
                CustomerDAO().update_balance(data['customer_id'], total - paid)
            elif data['type'] == 'purchase' and data.get('supplier_id'):
                SupplierDAO().update_balance(data['supplier_id'], total - paid)

            if paid > 0:
                if data['type'] == 'sale':
                    UserDAO().update_cash_balance(paid, add=True)
                else:
                    UserDAO().update_cash_balance(paid, add=False)

            self._commit()
            return invoice_id
        except Exception as e:
            self._rollback()
            raise e

    def get_all(self, search: str = None, inv_type: str = None,
                start_date: str = None, end_date: str = None,
                customer_id: int = None, supplier_id: int = None) -> List[Invoice]:
        uid = get_current_user_id()
        query = """
            SELECT i.*, c.name as customer_name, s.name as supplier_name
            FROM invoices i
            LEFT JOIN customers c ON i.customer_id = c.id
            LEFT JOIN suppliers s ON i.supplier_id = s.id
            WHERE i.user_id = ? AND i.deleted_at IS NULL
        """
        params = [uid]
        if search:
            query += " AND (i.reference LIKE ? OR c.name LIKE ? OR s.name LIKE ?)"
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param])
        if inv_type and inv_type in ('sale', 'purchase'):
            query += " AND i.type = ?"
            params.append(inv_type)
        if start_date:
            query += " AND i.date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND i.date <= ?"
            params.append(end_date)
        if customer_id:
            query += " AND i.customer_id = ?"
            params.append(customer_id)
        if supplier_id:
            query += " AND i.supplier_id = ?"
            params.append(supplier_id)
        query += " ORDER BY i.id DESC"
        rows = self._fetch_all(query, tuple(params))
        invoices = []
        for row in rows:
            inv = Invoice(
                id=row['id'],
                user_id=row['user_id'],
                type=row['type'],
                customer_id=row['customer_id'],
                supplier_id=row['supplier_id'],
                customer_name=row.get('customer_name'),
                supplier_name=row.get('supplier_name'),
                date=row.get('date', ''),
                reference=row.get('reference', ''),
                notes=row.get('notes', ''),
                total=storage_to_decimal(row.get('total', '0')),
                paid=storage_to_decimal(row.get('paid', '0')),
                status=row.get('status', 'active'),
                deleted_at=row.get('deleted_at')
            )
            invoices.append(inv)
        return invoices

    def get_by_id(self, invoice_id: int) -> Optional[Invoice]:
        uid = get_current_user_id()
        inv_row = self._fetch_one("""
            SELECT i.*, c.name as customer_name, s.name as supplier_name
            FROM invoices i
            LEFT JOIN customers c ON i.customer_id = c.id
            LEFT JOIN suppliers s ON i.supplier_id = s.id
            WHERE i.id=? AND i.user_id=?
        """, (invoice_id, uid))
        if not inv_row:
            return None
        inv = Invoice(
            id=inv_row['id'], user_id=inv_row['user_id'], type=inv_row['type'],
            customer_id=inv_row['customer_id'], supplier_id=inv_row['supplier_id'],
            customer_name=inv_row.get('customer_name'), supplier_name=inv_row.get('supplier_name'),
            date=inv_row.get('date', ''), reference=inv_row.get('reference', ''),
            notes=inv_row.get('notes', ''), total=storage_to_decimal(inv_row.get('total', '0')),
            paid=storage_to_decimal(inv_row.get('paid', '0')), status=inv_row.get('status', 'active'),
            deleted_at=inv_row.get('deleted_at')
        )
        lines = self._fetch_all("""
            SELECT il.*, it.name as item_name
            FROM invoice_lines il
            LEFT JOIN items it ON il.item_id = it.id
            WHERE il.invoice_id=?
        """, (invoice_id,))
        inv_lines = []
        for line in lines:
            inv_line = InvoiceLine(
                id=line['id'], invoice_id=line['invoice_id'], item_id=line['item_id'],
                item_name=line.get('item_name'), description=line.get('description', ''),
                quantity=storage_to_decimal(line.get('quantity', '0')),
                unit_price=storage_to_decimal(line.get('unit_price', '0')),
                total=storage_to_decimal(line.get('total', '0')),
                unit=line.get('unit', ''),
                quantity_in_base=storage_to_decimal(line.get('quantity_in_base', '0')),
                unit_cost=storage_to_decimal(line.get('unit_cost', '0')),
                cost_amount=storage_to_decimal(line.get('cost_amount', '0'))
            )
            inv_lines.append(inv_line)
        inv.lines = inv_lines
        return inv

    def delete_invoice(self, invoice_id: int):
        uid = get_current_user_id()
        inv = self.get_by_id(invoice_id)
        if not inv:
            raise Exception("الفاتورة غير موجودة")
        self._reverse_invoice_effects(inv)
        self._execute("UPDATE invoices SET deleted_at = datetime('now') WHERE id=? AND user_id=?", (invoice_id, uid))
        self._commit()

    def _reverse_invoice_effects(self, inv: Invoice):
        for line in inv.lines:
            base_qty = line.quantity_in_base
            if inv.type == 'purchase':
                InventoryMovementDAO().reverse_last_movement(line.item_id, 'purchase')
            else:
                InventoryMovementDAO().reverse_last_movement(line.item_id, 'sale')
        total = inv.total
        paid = inv.paid
        if inv.type == 'sale' and inv.customer_id:
            CustomerDAO().update_balance(inv.customer_id, -(total - paid))
        elif inv.type == 'purchase' and inv.supplier_id:
            SupplierDAO().update_balance(inv.supplier_id, -(total - paid))
        if paid > 0:
            if inv.type == 'sale':
                UserDAO().update_cash_balance(paid, add=False)
            else:
                UserDAO().update_cash_balance(paid, add=True)

    def get_next_reference(self, inv_type: str) -> str:
        year = datetime.now().strftime("%Y")
        prefix = f"{inv_type[:3].upper()}-{year}-"
        cur = self._execute("SELECT MAX(reference) FROM invoices WHERE reference LIKE ?", (prefix + '%',))
        max_ref = cur.fetchone()[0]
        if max_ref:
            try:
                num = int(max_ref.split('-')[-1]) + 1
            except:
                num = 1
        else:
            num = 1
        return f"{prefix}{num:04d}"
