# -*- coding: utf-8 -*-
import sqlite3
import os
import json
from datetime import datetime
from typing import List, Dict, Optional
import hashlib
import secrets

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'alrajhi.db')
_current_user_id = None
_current_user_role = None

def set_current_user(user_id: str, role: str = 'user'):
    global _current_user_id, _current_user_role
    _current_user_id = user_id
    _current_user_role = role

def get_current_user_id() -> Optional[str]:
    return _current_user_id

def get_current_user_role() -> Optional[str]:
    return _current_user_role

def clear_current_user():
    global _current_user_id, _current_user_role
    _current_user_id = None
    _current_user_role = None

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    return hashlib.sha256((password + salt).encode()).hexdigest() + ':' + salt

def verify_password(password: str, hashed: str) -> bool:
    try:
        hash_val, salt = hashed.split(':')
        return hash_val == hashlib.sha256((password + salt).encode()).hexdigest()
    except:
        return False

class Database:
    def __init__(self):
        self.conn = None
        self.init_db()

    def connect(self):
        if self.conn is None:
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            self.conn = sqlite3.connect(DB_PATH, isolation_level=None)
            self.conn.row_factory = sqlite3.Row
        return self.conn

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def init_db(self):
        conn = self.connect()
        cursor = conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                full_name TEXT,
                created_at TEXT,
                last_login TEXT,
                cash_balance REAL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                phone TEXT,
                address TEXT,
                balance REAL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, name)
            );
            CREATE TABLE IF NOT EXISTS suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                phone TEXT,
                address TEXT,
                balance REAL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, name)
            );
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, name)
            );
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                category_id INTEGER,
                item_type TEXT,
                purchase_price REAL,
                selling_price REAL,
                quantity REAL,
                unit TEXT,
                average_cost REAL,
                purchase_qty REAL DEFAULT 0,
                sale_qty REAL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, name)
            );
            CREATE TABLE IF NOT EXISTS item_units (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER,
                unit_name TEXT NOT NULL,
                conversion_factor REAL DEFAULT 1,
                FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                type TEXT,
                customer_id INTEGER,
                supplier_id INTEGER,
                date TEXT,
                reference TEXT,
                notes TEXT,
                total REAL,
                paid REAL DEFAULT 0,
                status TEXT,
                deleted_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (customer_id) REFERENCES customers(id),
                FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
            );
            CREATE TABLE IF NOT EXISTS invoice_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER,
                item_id INTEGER,
                description TEXT,
                quantity REAL,
                unit_price REAL,
                total REAL,
                unit TEXT,
                quantity_in_base REAL,
                unit_cost REAL,
                cost_amount REAL,
                FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
                FOREIGN KEY (item_id) REFERENCES items(id)
            );
            CREATE TABLE IF NOT EXISTS vouchers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                type TEXT,
                date TEXT,
                amount REAL,
                description TEXT,
                reference TEXT,
                customer_id INTEGER,
                supplier_id INTEGER,
                invoice_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (customer_id) REFERENCES customers(id),
                FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
                FOREIGN KEY (invoice_id) REFERENCES invoices(id)
            );
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                amount REAL,
                expense_date TEXT,
                description TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                name TEXT,
                type TEXT,
                balance REAL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)
        # تحديث الجداول القديمة
        cursor.execute("PRAGMA table_info(users)")
        cols = [c[1] for c in cursor.fetchall()]
        if 'password_hash' not in cols: cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
        if 'role' not in cols: cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
        if 'full_name' not in cols: cursor.execute("ALTER TABLE users ADD COLUMN full_name TEXT")
        if 'created_at' not in cols: cursor.execute("ALTER TABLE users ADD COLUMN created_at TEXT")
        if 'last_login' not in cols: cursor.execute("ALTER TABLE users ADD COLUMN last_login TEXT")
        if 'cash_balance' not in cols: cursor.execute("ALTER TABLE users ADD COLUMN cash_balance REAL DEFAULT 0")

        cursor.execute("PRAGMA table_info(items)")
        item_cols = [c[1] for c in cursor.fetchall()]
        if 'unit' not in item_cols:
            cursor.execute("ALTER TABLE items ADD COLUMN unit TEXT")

        cursor.execute("PRAGMA table_info(invoice_lines)")
        inv_lines_cols = [c[1] for c in cursor.fetchall()]
        if 'unit' not in inv_lines_cols:
            cursor.execute("ALTER TABLE invoice_lines ADD COLUMN unit TEXT")

        # مستخدم admin افتراضي
        cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            default_hash = hash_password('admin123')
            now = datetime.now().isoformat()
            cursor.execute("INSERT INTO users (id, username, password_hash, role, full_name, created_at, cash_balance) VALUES (?,?,?,?,?,?,0)",
                           ('admin', 'admin', default_hash, 'admin', 'المدير العام', now))
        # حسابات افتراضية
        default_accounts = [
            ('الصندوق', 'asset'), ('المبيعات', 'income'), ('المشتريات', 'expense'),
            ('المخزون', 'asset'), ('مصاريف عامة', 'expense'), ('رأس المال', 'equity')
        ]
        for name, typ in default_accounts:
            cursor.execute("INSERT OR IGNORE INTO accounts (user_id, name, type, balance) VALUES (?,?,?,0)", ('local_user', name, typ))
        conn.commit()

    # ========== دوال المستخدمين ==========
    def register_user(self, username: str, password: str, full_name: str = '', role: str = 'user') -> bool:
        conn = self.connect()
        cur = conn.cursor()
        try:
            uid = secrets.token_hex(8)
            phash = hash_password(password)
            now = datetime.now().isoformat()
            cur.execute("INSERT INTO users (id, username, password_hash, role, full_name, created_at, cash_balance) VALUES (?,?,?,?,?,?,0)",
                        (uid, username, phash, role, full_name, now))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def login(self, username: str, password: str) -> bool:
        conn = self.connect()
        cur = conn.cursor()
        cur.execute("SELECT id, password_hash, role FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        if row and verify_password(password, row['password_hash']):
            cur.execute("UPDATE users SET last_login = datetime('now') WHERE id = ?", (row['id'],))
            conn.commit()
            set_current_user(row['id'], row['role'])
            return True
        return False

    def get_users(self) -> List[Dict]:
        if get_current_user_role() != 'admin':
            return []
        cur = self.connect().cursor()
        cur.execute("SELECT id, username, role, full_name, created_at, last_login FROM users")
        return [dict(row) for row in cur.fetchall()]

    def delete_user(self, user_id: str) -> bool:
        if get_current_user_role() != 'admin' or user_id == 'admin':
            return False
        cur = self.connect().cursor()
        # حذف كل البيانات المرتبطة بالمستخدم
        cur.execute("DELETE FROM customers WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM suppliers WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM categories WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM items WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM invoices WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM vouchers WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM expenses WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM accounts WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
        self.conn.commit()
        return True

    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        cur = self.connect().cursor()
        cur.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        if row and verify_password(old_password, row['password_hash']):
            new_hash = hash_password(new_password)
            cur.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
            self.conn.commit()
            return True
        return False

    def _get_user_filter(self, table: str = '') -> str:
        uid = get_current_user_id()
        if not uid:
            return "1=0"
        if table:
            return f"{table}.user_id = '{uid}'"
        return f"user_id = '{uid}'"

    # ========== العملاء ==========
    def get_customers(self) -> List[Dict]:
        cur = self.connect().cursor()
        cur.execute(f"SELECT * FROM customers WHERE {self._get_user_filter('customers')} ORDER BY name")
        return [dict(row) for row in cur.fetchall()]

    def add_customer(self, name: str, phone: str = '', address: str = '') -> int:
        cur = self.connect().cursor()
        try:
            cur.execute("INSERT INTO customers (user_id, name, phone, address, balance) VALUES (?,?,?,?,0)",
                        (get_current_user_id(), name, phone, address))
            self.conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            raise Exception("اسم العميل موجود مسبقاً")

    def update_customer(self, cid: int, name: str, phone: str, address: str):
        cur = self.connect().cursor()
        try:
            cur.execute(f"UPDATE customers SET name=?, phone=?, address=? WHERE id=? AND {self._get_user_filter('customers')}",
                        (name, phone, address, cid))
            self.conn.commit()
        except sqlite3.IntegrityError:
            raise Exception("اسم العميل موجود مسبقاً")

    def delete_customer(self, cid: int):
        cur = self.connect().cursor()
        cur.execute("SELECT id FROM invoices WHERE customer_id=? AND user_id=?", (cid, get_current_user_id()))
        if cur.fetchone():
            raise Exception("لا يمكن حذف العميل لوجود فواتير مرتبطة به")
        cur.execute(f"DELETE FROM customers WHERE id=? AND {self._get_user_filter('customers')}", (cid,))
        self.conn.commit()

    # ========== الموردين ==========
    def get_suppliers(self) -> List[Dict]:
        cur = self.connect().cursor()
        cur.execute(f"SELECT * FROM suppliers WHERE {self._get_user_filter('suppliers')} ORDER BY name")
        return [dict(row) for row in cur.fetchall()]

    def add_supplier(self, name: str, phone: str = '', address: str = '') -> int:
        cur = self.connect().cursor()
        try:
            cur.execute("INSERT INTO suppliers (user_id, name, phone, address, balance) VALUES (?,?,?,?,0)",
                        (get_current_user_id(), name, phone, address))
            self.conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            raise Exception("اسم المورد موجود مسبقاً")

    def update_supplier(self, sid: int, name: str, phone: str, address: str):
        cur = self.connect().cursor()
        try:
            cur.execute(f"UPDATE suppliers SET name=?, phone=?, address=? WHERE id=? AND {self._get_user_filter('suppliers')}",
                        (name, phone, address, sid))
            self.conn.commit()
        except sqlite3.IntegrityError:
            raise Exception("اسم المورد موجود مسبقاً")

    def delete_supplier(self, sid: int):
        cur = self.connect().cursor()
        cur.execute("SELECT id FROM invoices WHERE supplier_id=? AND user_id=?", (sid, get_current_user_id()))
        if cur.fetchone():
            raise Exception("لا يمكن حذف المورد لوجود فواتير مرتبطة به")
        cur.execute(f"DELETE FROM suppliers WHERE id=? AND {self._get_user_filter('suppliers')}", (sid,))
        self.conn.commit()

    # ========== التصنيفات ==========
    def get_categories(self) -> List[Dict]:
        cur = self.connect().cursor()
        cur.execute(f"SELECT * FROM categories WHERE {self._get_user_filter('categories')} ORDER BY name")
        return [dict(row) for row in cur.fetchall()]

    def add_category(self, name: str) -> int:
        cur = self.connect().cursor()
        try:
            cur.execute("INSERT INTO categories (user_id, name) VALUES (?,?)", (get_current_user_id(), name))
            self.conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            raise Exception("اسم التصنيف موجود مسبقاً")

    def update_category(self, cid: int, name: str):
        cur = self.connect().cursor()
        try:
            cur.execute(f"UPDATE categories SET name=? WHERE id=? AND {self._get_user_filter('categories')}", (name, cid))
            self.conn.commit()
        except sqlite3.IntegrityError:
            raise Exception("اسم التصنيف موجود مسبقاً")

    def delete_category(self, cid: int):
        cur = self.connect().cursor()
        cur.execute("SELECT id FROM items WHERE category_id=? AND user_id=?", (cid, get_current_user_id()))
        if cur.fetchone():
            raise Exception("لا يمكن حذف التصنيف لوجود مواد مرتبطة به")
        cur.execute(f"DELETE FROM categories WHERE id=? AND {self._get_user_filter('categories')}", (cid,))
        self.conn.commit()

    # ========== المواد ==========
    def get_items(self) -> List[Dict]:
        cur = self.connect().cursor()
        cur.execute(f"""
            SELECT i.*, c.name as category_name
            FROM items i
            LEFT JOIN categories c ON i.category_id = c.id
            WHERE i.user_id = ?
            ORDER BY i.name
        """, (get_current_user_id(),))
        items = [dict(row) for row in cur.fetchall()]
        for item in items:
            cur.execute("SELECT id, unit_name, conversion_factor FROM item_units WHERE item_id = ?", (item['id'],))
            item['item_units'] = [dict(row) for row in cur.fetchall()]
            cur.execute("""
                SELECT 
                    SUM(CASE WHEN inv.type='purchase' THEN il.quantity_in_base ELSE 0 END) as purchase_qty,
                    SUM(CASE WHEN inv.type='sale' THEN il.quantity_in_base ELSE 0 END) as sale_qty,
                    COUNT(CASE WHEN inv.type='purchase' THEN 1 END) as purchase_count,
                    COUNT(CASE WHEN inv.type='sale' THEN 1 END) as sale_count,
                    MAX(CASE WHEN inv.type='purchase' THEN inv.date END) as last_purchase_date,
                    MAX(CASE WHEN inv.type='sale' THEN inv.date END) as last_sale_date
                FROM invoice_lines il
                JOIN invoices inv ON il.invoice_id = inv.id
                WHERE il.item_id = ? AND inv.user_id = ? AND inv.deleted_at IS NULL
            """, (item['id'], get_current_user_id()))
            stats = cur.fetchone()
            item['purchase_qty'] = stats['purchase_qty'] or 0
            item['sale_qty'] = stats['sale_qty'] or 0
            item['purchase_count'] = stats['purchase_count'] or 0
            item['sale_count'] = stats['sale_count'] or 0
            item['last_purchase_date'] = stats['last_purchase_date']
            item['last_sale_date'] = stats['last_sale_date']
            item['available'] = item['quantity'] or 0
            item['total_value'] = item['available'] * (item['average_cost'] or 0)
        return items

    def add_item(self, data: Dict) -> int:
        cur = self.connect().cursor()
        try:
            cur.execute("""
                INSERT INTO items (user_id, name, category_id, item_type, purchase_price, selling_price, quantity, unit, average_cost, purchase_qty, sale_qty)
                VALUES (?,?,?,?,?,?,?,?,?,?,0)
            """, (get_current_user_id(), data['name'], data.get('category_id'), data.get('item_type', 'مخزون'),
                  data.get('purchase_price', 0), data.get('selling_price', 0), data.get('quantity', 0),
                  data.get('unit', ''), data.get('average_cost', data.get('purchase_price', 0)),
                  data.get('quantity', 0)))
            self.conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            raise Exception("اسم المادة موجود مسبقاً")

    def update_item(self, item_id: int, data: Dict):
        cur = self.connect().cursor()
        try:
            cur.execute(f"""
                UPDATE items SET name=?, category_id=?, item_type=?, purchase_price=?, selling_price=?, quantity=?, unit=?, average_cost=?
                WHERE id=? AND user_id=?
            """, (data['name'], data.get('category_id'), data.get('item_type'),
                  data.get('purchase_price', 0), data.get('selling_price', 0), data.get('quantity', 0),
                  data.get('unit', ''), data.get('average_cost', data.get('purchase_price', 0)), item_id, get_current_user_id()))
            self.conn.commit()
        except sqlite3.IntegrityError:
            raise Exception("اسم المادة موجود مسبقاً")

    def delete_item(self, item_id: int):
        cur = self.connect().cursor()
        cur.execute("SELECT id FROM invoice_lines WHERE item_id=? LIMIT 1", (item_id,))
        if cur.fetchone():
            raise Exception("لا يمكن حذف المادة لاستخدامها في فواتير")
        cur.execute("DELETE FROM item_units WHERE item_id=?", (item_id,))
        cur.execute("DELETE FROM items WHERE id=? AND user_id=?", (item_id, get_current_user_id()))
        self.conn.commit()

    # ========== الوحدات الفرعية ==========
    def add_item_unit(self, item_id: int, unit_name: str, conversion_factor: float) -> int:
        cur = self.connect().cursor()
        cur.execute("INSERT INTO item_units (item_id, unit_name, conversion_factor) VALUES (?,?,?)",
                    (item_id, unit_name, conversion_factor))
        self.conn.commit()
        return cur.lastrowid

    def get_item_units(self, item_id: int) -> List[Dict]:
        cur = self.connect().cursor()
        cur.execute("SELECT id, unit_name, conversion_factor FROM item_units WHERE item_id = ?", (item_id,))
        return [dict(row) for row in cur.fetchall()]

    def delete_item_unit(self, unit_id: int):
        cur = self.connect().cursor()
        cur.execute("DELETE FROM item_units WHERE id = ?", (unit_id,))
        self.conn.commit()

    def clear_item_units(self, item_id: int):
        cur = self.connect().cursor()
        cur.execute("DELETE FROM item_units WHERE item_id = ?", (item_id,))
        self.conn.commit()

    # ========== المخزون ==========
    def _update_item_average_cost(self, item_id: int, new_qty_base: float, unit_cost: float, is_purchase: bool):
        cur = self.connect().cursor()
        cur.execute("SELECT quantity, average_cost, purchase_qty FROM items WHERE id=? AND user_id=?", (item_id, get_current_user_id()))
        row = cur.fetchone()
        if not row:
            return
        current_qty = row['quantity'] or 0
        current_avg = row['average_cost'] or 0
        if is_purchase:
            new_qty = current_qty + new_qty_base
            new_purchase_qty = (row['purchase_qty'] or 0) + new_qty_base
            new_avg = ((current_avg * current_qty) + (unit_cost * new_qty_base)) / (current_qty + new_qty_base) if (current_qty + new_qty_base) > 0 else unit_cost
            cur.execute("UPDATE items SET quantity=?, average_cost=?, purchase_qty=? WHERE id=?",
                        (new_qty, new_avg, new_purchase_qty, item_id))
        else:
            new_qty = current_qty - new_qty_base
            cur.execute("UPDATE items SET quantity=?, sale_qty = sale_qty + ? WHERE id=?", (new_qty, new_qty_base, item_id))

    def _reverse_item_average_cost(self, item_id: int, old_qty_base: float, old_unit_cost: float, is_purchase: bool):
        cur = self.connect().cursor()
        cur.execute("SELECT quantity, average_cost, purchase_qty, sale_qty FROM items WHERE id=? AND user_id=?", (item_id, get_current_user_id()))
        row = cur.fetchone()
        if not row:
            return
        current_qty = row['quantity'] or 0
        if is_purchase:
            new_qty = current_qty - old_qty_base
            new_purchase_qty = (row['purchase_qty'] or 0) - old_qty_base
            cur.execute("UPDATE items SET quantity=?, purchase_qty=? WHERE id=?", (new_qty, new_purchase_qty, item_id))
        else:
            new_qty = current_qty + old_qty_base
            cur.execute("UPDATE items SET quantity=?, sale_qty = sale_qty - ? WHERE id=?", (new_qty, old_qty_base, item_id))

    # ========== الفواتير ==========
    def create_invoice(self, data: Dict) -> int:
        conn = self.connect()
        cur = conn.cursor()
        try:
            cur.execute("BEGIN TRANSACTION")
            cur.execute("""
                INSERT INTO invoices (user_id, type, customer_id, supplier_id, date, reference, notes, total, paid, status)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (get_current_user_id(), data['type'], data.get('customer_id'), data.get('supplier_id'),
                  data['date'], data.get('reference', ''), data.get('notes', ''),
                  data['total'], data.get('paid_amount', 0), 'active'))
            invoice_id = cur.lastrowid
            for line in data['lines']:
                base_qty = line.get('base_qty', line['quantity'])
                unit_cost = line['unit_price']
                cur.execute("""
                    INSERT INTO invoice_lines (invoice_id, item_id, quantity, unit_price, total, unit, quantity_in_base, unit_cost, cost_amount)
                    VALUES (?,?,?,?,?,?,?,?,?)
                """, (invoice_id, line['item_id'], line['quantity'], line['unit_price'], line['total'],
                      line.get('unit', ''), base_qty, unit_cost, 0))
                line_id = cur.lastrowid
                if data['type'] == 'purchase':
                    self._update_item_average_cost(line['item_id'], base_qty, unit_cost, True)
                    cur.execute("UPDATE invoice_lines SET cost_amount = ? WHERE id = ?", (unit_cost * base_qty, line_id))
                else:
                    cur.execute("SELECT average_cost FROM items WHERE id=? AND user_id=?", (line['item_id'], get_current_user_id()))
                    avg_cost = cur.fetchone()['average_cost'] or 0
                    cost_amt = base_qty * avg_cost
                    cur.execute("UPDATE invoice_lines SET cost_amount = ? WHERE id = ?", (cost_amt, line_id))
                    self._update_item_average_cost(line['item_id'], base_qty, unit_cost, False)
            if data['type'] == 'sale' and data.get('customer_id'):
                cur.execute("UPDATE customers SET balance = balance + ? WHERE id=? AND user_id=?",
                            (data['total'] - data.get('paid_amount', 0), data['customer_id'], get_current_user_id()))
            elif data['type'] == 'purchase' and data.get('supplier_id'):
                cur.execute("UPDATE suppliers SET balance = balance + ? WHERE id=? AND user_id=?",
                            (data['total'] - data.get('paid_amount', 0), data['supplier_id'], get_current_user_id()))
            if data.get('paid_amount', 0) > 0:
                cur.execute("UPDATE users SET cash_balance = cash_balance + ? WHERE id=?",
                            (data['paid_amount'] if data['type'] == 'sale' else -data['paid_amount'], get_current_user_id()))
            conn.commit()
            return invoice_id
        except Exception as e:
            conn.rollback()
            raise e

    def get_invoices(self) -> List[Dict]:
        cur = self.connect().cursor()
        cur.execute("""
            SELECT i.*, c.name as customer_name, s.name as supplier_name
            FROM invoices i
            LEFT JOIN customers c ON i.customer_id = c.id
            LEFT JOIN suppliers s ON i.supplier_id = s.id
            WHERE i.user_id=? AND i.deleted_at IS NULL
            ORDER BY i.id DESC
        """, (get_current_user_id(),))
        invoices = [dict(row) for row in cur.fetchall()]
        for inv in invoices:
            cur.execute("""
                SELECT il.*, it.name as item_name
                FROM invoice_lines il
                LEFT JOIN items it ON il.item_id = it.id
                WHERE il.invoice_id=?
            """, (inv['id'],))
            inv['lines'] = [dict(row) for row in cur.fetchall()]
        return invoices

    def get_invoices_by_id(self, invoice_id: int) -> Dict:
        cur = self.connect().cursor()
        cur.execute("""
            SELECT i.*, c.name as customer_name, s.name as supplier_name
            FROM invoices i
            LEFT JOIN customers c ON i.customer_id = c.id
            LEFT JOIN suppliers s ON i.supplier_id = s.id
            WHERE i.id=? AND i.user_id=?
        """, (invoice_id, get_current_user_id()))
        inv = cur.fetchone()
        if not inv:
            return None
        inv = dict(inv)
        cur.execute("""
            SELECT il.*, it.name as item_name
            FROM invoice_lines il
            LEFT JOIN items it ON il.item_id = it.id
            WHERE il.invoice_id=?
        """, (invoice_id,))
        inv['lines'] = [dict(row) for row in cur.fetchall()]
        return inv

    def _reverse_invoice_effects(self, inv: Dict):
        cur = self.connect().cursor()
        for line in inv['lines']:
            base_qty = line['quantity_in_base']
            if inv['type'] == 'purchase':
                self._reverse_item_average_cost(line['item_id'], base_qty, line['unit_cost'], True)
            else:
                self._reverse_item_average_cost(line['item_id'], base_qty, line['unit_price'], False)
        if inv['type'] == 'sale' and inv.get('customer_id'):
            cur.execute("UPDATE customers SET balance = balance - ? WHERE id=? AND user_id=?",
                        (inv['total'] - inv['paid'], inv['customer_id'], get_current_user_id()))
        elif inv['type'] == 'purchase' and inv.get('supplier_id'):
            cur.execute("UPDATE suppliers SET balance = balance - ? WHERE id=? AND user_id=?",
                        (inv['total'] - inv['paid'], inv['supplier_id'], get_current_user_id()))
        if inv.get('paid', 0) > 0:
            cur.execute("UPDATE users SET cash_balance = cash_balance - ? WHERE id=?",
                        (inv['paid'] if inv['type'] == 'sale' else -inv['paid'], get_current_user_id()))

    def update_invoice(self, invoice_id: int, new_data: Dict):
        conn = self.connect()
        cur = conn.cursor()
        try:
            cur.execute("BEGIN TRANSACTION")
            old_inv = self.get_invoices_by_id(invoice_id)
            if not old_inv:
                raise Exception("الفاتورة غير موجودة")
            self._reverse_invoice_effects(old_inv)
            cur.execute("UPDATE invoices SET deleted_at = datetime('now') WHERE id=?", (invoice_id,))
            new_data['id'] = None
            new_id = self.create_invoice(new_data)
            conn.commit()
            return new_id
        except Exception as e:
            conn.rollback()
            raise e

    def delete_invoice(self, invoice_id: int):
        conn = self.connect()
        cur = conn.cursor()
        try:
            cur.execute("BEGIN TRANSACTION")
            inv = self.get_invoices_by_id(invoice_id)
            if not inv:
                raise Exception("الفاتورة غير موجودة")
            self._reverse_invoice_effects(inv)
            cur.execute("UPDATE invoices SET deleted_at = datetime('now') WHERE id=? AND user_id=?", (invoice_id, get_current_user_id()))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e

    # ========== المصاريف ==========
    def get_expenses(self) -> List[Dict]:
        cur = self.connect().cursor()
        cur.execute("SELECT * FROM expenses WHERE user_id=? ORDER BY id DESC", (get_current_user_id(),))
        return [dict(row) for row in cur.fetchall()]

    def add_expense(self, amount: float, date: str, desc: str) -> int:
        cur = self.connect().cursor()
        cur.execute("INSERT INTO expenses (user_id, amount, expense_date, description) VALUES (?,?,?,?)",
                    (get_current_user_id(), amount, date, desc))
        cur.execute("UPDATE users SET cash_balance = cash_balance - ? WHERE id=?", (amount, get_current_user_id()))
        self.conn.commit()
        return cur.lastrowid

    def delete_expense(self, exp_id: int):
        cur = self.connect().cursor()
        cur.execute("SELECT amount FROM expenses WHERE id=? AND user_id=?", (exp_id, get_current_user_id()))
        row = cur.fetchone()
        if row:
            cur.execute("UPDATE users SET cash_balance = cash_balance + ? WHERE id=?", (row['amount'], get_current_user_id()))
        cur.execute("DELETE FROM expenses WHERE id=? AND user_id=?", (exp_id, get_current_user_id()))
        self.conn.commit()

    # ========== السندات ==========
    def get_vouchers(self) -> List[Dict]:
        cur = self.connect().cursor()
        cur.execute("SELECT * FROM vouchers WHERE user_id=? ORDER BY id DESC", (get_current_user_id(),))
        return [dict(row) for row in cur.fetchall()]

    def add_voucher(self, data: Dict) -> int:
        cur = self.connect().cursor()
        cur.execute("""
            INSERT INTO vouchers (user_id, type, date, amount, description, reference, customer_id, supplier_id, invoice_id)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (get_current_user_id(), data['type'], data['date'], data['amount'], data.get('description',''),
              data.get('reference',''), data.get('customer_id'), data.get('supplier_id'), data.get('invoice_id')))
        vid = cur.lastrowid
        sign = 1 if data['type'] == 'receipt' else -1
        cur.execute("UPDATE users SET cash_balance = cash_balance + ? WHERE id=?", (sign * data['amount'], get_current_user_id()))
        if data.get('customer_id'):
            cur.execute("UPDATE customers SET balance = balance - ? WHERE id=? AND user_id=?", (data['amount'], data['customer_id'], get_current_user_id()))
        elif data.get('supplier_id'):
            cur.execute("UPDATE suppliers SET balance = balance - ? WHERE id=? AND user_id=?", (data['amount'], data['supplier_id'], get_current_user_id()))
        self.conn.commit()
        return vid

    def delete_voucher(self, vid: int):
        cur = self.connect().cursor()
        cur.execute("SELECT type, amount, customer_id, supplier_id FROM vouchers WHERE id=? AND user_id=?", (vid, get_current_user_id()))
        row = cur.fetchone()
        if row:
            sign = -1 if row['type'] == 'receipt' else 1
            cur.execute("UPDATE users SET cash_balance = cash_balance + ? WHERE id=?", (sign * row['amount'], get_current_user_id()))
            if row['customer_id']:
                cur.execute("UPDATE customers SET balance = balance + ? WHERE id=? AND user_id=?", (row['amount'], row['customer_id'], get_current_user_id()))
            elif row['supplier_id']:
                cur.execute("UPDATE suppliers SET balance = balance + ? WHERE id=? AND user_id=?", (row['amount'], row['supplier_id'], get_current_user_id()))
        cur.execute("DELETE FROM vouchers WHERE id=? AND user_id=?", (vid, get_current_user_id()))
        self.conn.commit()

    # ========== الإحصائيات والتقارير ==========
    def get_summary(self) -> Dict:
        cur = self.connect().cursor()
        cur.execute("SELECT SUM(total) as sales FROM invoices WHERE type='sale' AND user_id=? AND deleted_at IS NULL", (get_current_user_id(),))
        sales = cur.fetchone()['sales'] or 0
        cur.execute("SELECT SUM(total) as purchases FROM invoices WHERE type='purchase' AND user_id=? AND deleted_at IS NULL", (get_current_user_id(),))
        purchases = cur.fetchone()['purchases'] or 0
        cur.execute("SELECT SUM(amount) as expenses FROM expenses WHERE user_id=?", (get_current_user_id(),))
        expenses = cur.fetchone()['expenses'] or 0
        net = sales - purchases - expenses
        cur.execute("SELECT SUM(balance) as receivables FROM customers WHERE user_id=?", (get_current_user_id(),))
        receivables = cur.fetchone()['receivables'] or 0
        cur.execute("SELECT SUM(balance) as payables FROM suppliers WHERE user_id=?", (get_current_user_id(),))
        payables = cur.fetchone()['payables'] or 0
        cur.execute("SELECT cash_balance FROM users WHERE id=?", (get_current_user_id(),))
        cash = cur.fetchone()['cash_balance'] or 0
        return {
            'net_profit': net, 'cash_balance': cash, 'receivables': receivables, 'payables': payables,
            'total_sales': sales, 'total_purchases': purchases, 'total_expenses': expenses
        }

    def get_trial_balance(self) -> List[Dict]:
        cur = self.connect().cursor()
        sales = cur.execute("SELECT SUM(total) FROM invoices WHERE type='sale' AND user_id=? AND deleted_at IS NULL", (get_current_user_id(),)).fetchone()[0] or 0
        purchases = cur.execute("SELECT SUM(total) FROM invoices WHERE type='purchase' AND user_id=? AND deleted_at IS NULL", (get_current_user_id(),)).fetchone()[0] or 0
        expenses = cur.execute("SELECT SUM(amount) FROM expenses WHERE user_id=?", (get_current_user_id(),)).fetchone()[0] or 0
        cash = cur.execute("SELECT cash_balance FROM users WHERE id=?", (get_current_user_id(),)).fetchone()[0] or 0
        receivables = cur.execute("SELECT SUM(balance) FROM customers WHERE user_id=?", (get_current_user_id(),)).fetchone()[0] or 0
        payables = cur.execute("SELECT SUM(balance) FROM suppliers WHERE user_id=?", (get_current_user_id(),)).fetchone()[0] or 0
        return [
            {'name': 'الصندوق', 'debit': cash if cash>0 else 0, 'credit': -cash if cash<0 else 0},
            {'name': 'الذمم المدينة', 'debit': receivables, 'credit': 0},
            {'name': 'الذمم الدائنة', 'debit': 0, 'credit': payables},
            {'name': 'المبيعات', 'debit': 0, 'credit': sales},
            {'name': 'المشتريات', 'debit': purchases, 'credit': 0},
            {'name': 'المصاريف', 'debit': expenses, 'credit': 0}
        ]

    def get_income_statement(self) -> Dict:
        trial = self.get_trial_balance()
        inc = [t for t in trial if t['name'] == 'المبيعات']
        exp = [t for t in trial if t['name'] in ('المشتريات', 'المصاريف')]
        total_income = sum(i['credit'] for i in inc)
        total_expenses = sum(e['debit'] for e in exp)
        net = total_income - total_expenses
        return {'income': [{'name': i['name'], 'balance': i['credit']} for i in inc],
                'expenses': [{'name': e['name'], 'balance': e['debit']} for e in exp],
                'total_income': total_income, 'total_expenses': total_expenses, 'net_profit': net}

    def get_balance_sheet(self) -> Dict:
        trial = self.get_trial_balance()
        assets = [t for t in trial if t['name'] in ('الصندوق', 'الذمم المدينة')]
        liabilities = [t for t in trial if t['name'] == 'الذمم الدائنة']
        equity = [{'name': 'رأس المال', 'credit': sum(a['debit'] for a in assets) - sum(l['credit'] for l in liabilities)}]
        return {
            'assets': assets, 'liabilities': liabilities, 'equity': equity,
            'total_assets': sum(a['debit'] for a in assets),
            'total_liabilities': sum(l['credit'] for l in liabilities),
            'total_equity': equity[0]['credit']
        }

    def get_customer_statement(self, cust_id: int) -> List[Dict]:
        cur = self.connect().cursor()
        cur.execute("""
            SELECT date, reference, total as amount, 'فاتورة' as description, total as debit, 0 as credit
            FROM invoices WHERE customer_id=? AND type='sale' AND user_id=? AND deleted_at IS NULL
            UNION ALL
            SELECT date, reference, amount, 'سند قبض', 0, amount
            FROM vouchers WHERE customer_id=? AND type='receipt' AND user_id=?
            ORDER BY date
        """, (cust_id, get_current_user_id(), cust_id, get_current_user_id()))
        rows = [dict(row) for row in cur.fetchall()]
        balance = 0
        for r in rows:
            balance += r['debit'] - r['credit']
            r['balance'] = balance
        return rows

    def get_supplier_statement(self, supp_id: int) -> List[Dict]:
        cur = self.connect().cursor()
        cur.execute("""
            SELECT date, reference, total as amount, 'فاتورة' as description, 0 as debit, total as credit
            FROM invoices WHERE supplier_id=? AND type='purchase' AND user_id=? AND deleted_at IS NULL
            UNION ALL
            SELECT date, reference, amount, 'سند دفع', amount, 0
            FROM vouchers WHERE supplier_id=? AND type='payment' AND user_id=?
            ORDER BY date
        """, (supp_id, get_current_user_id(), supp_id, get_current_user_id()))
        rows = [dict(row) for row in cur.fetchall()]
        balance = 0
        for r in rows:
            balance += r['credit'] - r['debit']
            r['balance'] = balance
        return rows

    # ========== النسخ الاحتياطي ==========
    def export_full_database(self) -> bytes:
        tables = ['customers', 'suppliers', 'categories', 'items', 'item_units', 'invoices', 'invoice_lines', 'vouchers', 'expenses', 'users']
        data = {}
        uid = get_current_user_id()
        for tbl in tables:
            cur = self.connect().cursor()
            if tbl == 'item_units':
                # جدول item_units لا يحتوي على user_id، نربطه عبر items
                cur.execute("""
                    SELECT iu.* FROM item_units iu
                    JOIN items i ON iu.item_id = i.id
                    WHERE i.user_id = ?
                """, (uid,))
            else:
                cur.execute(f"SELECT * FROM {tbl} WHERE user_id=?", (uid,))
            rows = cur.fetchall()
            data[tbl] = [dict(row) for row in rows]
        return json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')

    def import_full_database(self, json_bytes: bytes):
        data = json.loads(json_bytes.decode('utf-8'))
        conn = self.connect()
        cur = conn.cursor()
        try:
            cur.execute("BEGIN TRANSACTION")
            uid = get_current_user_id()
            for tbl, rows in data.items():
                if tbl == 'item_units':
                    # حذف الوحدات القديمة المرتبطة بهذا المستخدم
                    cur.execute("DELETE FROM item_units WHERE item_id IN (SELECT id FROM items WHERE user_id=?)", (uid,))
                else:
                    cur.execute(f"DELETE FROM {tbl} WHERE user_id=?", (uid,))
                for row in rows:
                    if 'user_id' in row and tbl != 'item_units':
                        row['user_id'] = uid
                    cols = ', '.join(row.keys())
                    ph = ', '.join(['?' for _ in row])
                    cur.execute(f"INSERT INTO {tbl} ({cols}) VALUES ({ph})", list(row.values()))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e

    def get_monthly_sales(self):
        cur = self.connect().cursor()
        cur.execute("""
            SELECT strftime('%Y-%m', date) as month, SUM(total) as total
            FROM invoices
            WHERE type='sale' AND user_id=? AND deleted_at IS NULL
            GROUP BY month
            ORDER BY month
        """, (get_current_user_id(),))
        rows = cur.fetchall()
        return [{'month': row['month'], 'total': row['total'] or 0} for row in rows]

    def get_monthly_profit(self):
        cur = self.connect().cursor()
        cur.execute("""
            SELECT strftime('%Y-%m', i.date) as month,
                   SUM(CASE WHEN i.type='sale' THEN i.total ELSE 0 END) -
                   SUM(CASE WHEN i.type='purchase' THEN i.total ELSE 0 END) -
                   COALESCE((SELECT SUM(amount) FROM expenses WHERE user_id=? AND strftime('%Y-%m', expense_date)=strftime('%Y-%m', i.date)), 0) as profit
            FROM invoices i
            WHERE i.user_id=? AND i.deleted_at IS NULL
            GROUP BY month
            ORDER BY month
        """, (get_current_user_id(), get_current_user_id()))
        rows = cur.fetchall()
        return [{'month': row['month'], 'profit': row['profit'] or 0} for row in rows]

    def get_next_invoice_reference(self, inv_type):
        year = datetime.now().strftime("%Y")
        prefix = f"{inv_type[:3].upper()}-{year}-"
        cur = self.connect().cursor()
        cur.execute("SELECT MAX(reference) FROM invoices WHERE reference LIKE ?", (prefix + '%',))
        max_ref = cur.fetchone()[0]
        if max_ref:
            try:
                num = int(max_ref.split('-')[-1]) + 1
            except:
                num = 1
        else:
            num = 1
        return f"{prefix}{num:04d}"

db = Database()
