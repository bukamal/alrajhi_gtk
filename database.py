# -*- coding: utf-8 -*-
import sqlite3
import os
import json
from datetime import datetime
from typing import List, Dict, Optional
import hashlib
import secrets
from decimal import Decimal, getcontext

getcontext().prec = 28
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'alrajhi.db')

class Session:
    _instance = None
    _current_user_id = None
    _current_user_role = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def set_current_user(cls, user_id: str, role: str = 'user'):
        cls._current_user_id = user_id
        cls._current_user_role = role

    @classmethod
    def get_current_user_id(cls) -> Optional[str]:
        return cls._current_user_id

    @classmethod
    def get_current_user_role(cls) -> Optional[str]:
        return cls._current_user_role

    @classmethod
    def clear_current_user(cls):
        cls._current_user_id = None
        cls._current_user_role = None

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    return hashlib.sha256((password + salt).encode()).hexdigest() + ':' + salt

def verify_password(password: str, hashed: str) -> bool:
    try:
        hash_val, salt = hashed.split(':')
        return hash_val == hashlib.sha256((password + salt).encode()).hexdigest()
    except:
        return False

def decimal_to_storage(d: Decimal) -> str:
    return str(d) if d is not None else '0'

def storage_to_decimal(s: str) -> Decimal:
    try:
        return Decimal(s)
    except:
        return Decimal('0')

class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.conn = None
            cls._instance.init_db()
        return cls._instance

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
                cash_balance TEXT DEFAULT '0'
            );
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                phone TEXT,
                address TEXT,
                balance TEXT DEFAULT '0',
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, name)
            );
            CREATE TABLE IF NOT EXISTS suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                phone TEXT,
                address TEXT,
                balance TEXT DEFAULT '0',
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
                purchase_price TEXT DEFAULT '0',
                selling_price TEXT DEFAULT '0',
                quantity TEXT DEFAULT '0',
                unit TEXT,
                average_cost TEXT DEFAULT '0',
                purchase_qty TEXT DEFAULT '0',
                sale_qty TEXT DEFAULT '0',
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, name)
            );
            CREATE TABLE IF NOT EXISTS item_units (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER,
                unit_name TEXT NOT NULL,
                conversion_factor TEXT DEFAULT '1',
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
                total TEXT DEFAULT '0',
                paid TEXT DEFAULT '0',
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
                quantity TEXT DEFAULT '0',
                unit_price TEXT DEFAULT '0',
                total TEXT DEFAULT '0',
                unit TEXT,
                quantity_in_base TEXT DEFAULT '0',
                unit_cost TEXT DEFAULT '0',
                cost_amount TEXT DEFAULT '0',
                FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
                FOREIGN KEY (item_id) REFERENCES items(id)
            );
            CREATE TABLE IF NOT EXISTS vouchers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                type TEXT,
                date TEXT,
                amount TEXT DEFAULT '0',
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
                amount TEXT DEFAULT '0',
                expense_date TEXT,
                description TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                name TEXT,
                type TEXT,
                balance TEXT DEFAULT '0',
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS inventory_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                movement_type TEXT NOT NULL,
                quantity TEXT NOT NULL,
                unit_cost TEXT,
                reference_id INTEGER,
                movement_date TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (item_id) REFERENCES items(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS exchange_rates (
                currency_code TEXT PRIMARY KEY,
                rate_to_usd TEXT NOT NULL,
                updated_at TEXT
            );
        """)

        # إضافة عمود barcode إذا لم يكن موجوداً (بدون UNIQUE أولاً)
        cursor.execute("PRAGMA table_info(items)")
        item_cols = [c[1] for c in cursor.fetchall()]
        if 'barcode' not in item_cols:
            cursor.execute("ALTER TABLE items ADD COLUMN barcode TEXT")
        # إنشاء فهرس فريد للباركود (لضمان عدم التكرار)
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_items_barcode ON items(barcode) WHERE barcode IS NOT NULL")

        # تحويل الأعمدة القديمة من REAL إلى TEXT
        cursor.execute("PRAGMA table_info(users)")
        cols = [c[1] for c in cursor.fetchall()]
        if 'cash_balance' in cols and 'cash_balance_old' not in cols:
            cursor.execute("ALTER TABLE users RENAME COLUMN cash_balance TO cash_balance_old")
            cursor.execute("ALTER TABLE users ADD COLUMN cash_balance TEXT DEFAULT '0'")
            cursor.execute("UPDATE users SET cash_balance = CAST(cash_balance_old AS TEXT) WHERE cash_balance_old IS NOT NULL")
            cursor.execute("ALTER TABLE users DROP COLUMN cash_balance_old")
        if 'password_hash' not in cols: cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
        if 'role' not in cols: cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
        if 'full_name' not in cols: cursor.execute("ALTER TABLE users ADD COLUMN full_name TEXT")
        if 'created_at' not in cols: cursor.execute("ALTER TABLE users ADD COLUMN created_at TEXT")
        if 'last_login' not in cols: cursor.execute("ALTER TABLE users ADD COLUMN last_login TEXT")

        cursor.execute("PRAGMA table_info(customers)")
        if 'balance' in [c[1] for c in cursor.fetchall()]:
            cursor.execute("ALTER TABLE customers RENAME COLUMN balance TO balance_old")
            cursor.execute("ALTER TABLE customers ADD COLUMN balance TEXT DEFAULT '0'")
            cursor.execute("UPDATE customers SET balance = CAST(balance_old AS TEXT) WHERE balance_old IS NOT NULL")
            cursor.execute("ALTER TABLE customers DROP COLUMN balance_old")

        cursor.execute("PRAGMA table_info(suppliers)")
        if 'balance' in [c[1] for c in cursor.fetchall()]:
            cursor.execute("ALTER TABLE suppliers RENAME COLUMN balance TO balance_old")
            cursor.execute("ALTER TABLE suppliers ADD COLUMN balance TEXT DEFAULT '0'")
            cursor.execute("UPDATE suppliers SET balance = CAST(balance_old AS TEXT) WHERE balance_old IS NOT NULL")
            cursor.execute("ALTER TABLE suppliers DROP COLUMN balance_old")

        for col in ['purchase_price', 'selling_price', 'quantity', 'average_cost', 'purchase_qty', 'sale_qty']:
            if col in item_cols:
                cursor.execute(f"ALTER TABLE items RENAME COLUMN {col} TO {col}_old")
                cursor.execute(f"ALTER TABLE items ADD COLUMN {col} TEXT DEFAULT '0'")
                cursor.execute(f"UPDATE items SET {col} = CAST({col}_old AS TEXT) WHERE {col}_old IS NOT NULL")
                cursor.execute(f"ALTER TABLE items DROP COLUMN {col}_old")
        if 'unit' not in item_cols:
            cursor.execute("ALTER TABLE items ADD COLUMN unit TEXT")

        cursor.execute("PRAGMA table_info(invoice_lines)")
        inv_lines_cols = [c[1] for c in cursor.fetchall()]
        for col in ['quantity', 'unit_price', 'total', 'quantity_in_base', 'unit_cost', 'cost_amount']:
            if col in inv_lines_cols:
                cursor.execute(f"ALTER TABLE invoice_lines RENAME COLUMN {col} TO {col}_old")
                cursor.execute(f"ALTER TABLE invoice_lines ADD COLUMN {col} TEXT DEFAULT '0'")
                cursor.execute(f"UPDATE invoice_lines SET {col} = CAST({col}_old AS TEXT) WHERE {col}_old IS NOT NULL")
                cursor.execute(f"ALTER TABLE invoice_lines DROP COLUMN {col}_old")
        if 'unit' not in inv_lines_cols:
            cursor.execute("ALTER TABLE invoice_lines ADD COLUMN unit TEXT")

        cursor.execute("PRAGMA table_info(invoices)")
        inv_cols = [c[1] for c in cursor.fetchall()]
        for col in ['total', 'paid']:
            if col in inv_cols:
                cursor.execute(f"ALTER TABLE invoices RENAME COLUMN {col} TO {col}_old")
                cursor.execute(f"ALTER TABLE invoices ADD COLUMN {col} TEXT DEFAULT '0'")
                cursor.execute(f"UPDATE invoices SET {col} = CAST({col}_old AS TEXT) WHERE {col}_old IS NOT NULL")
                cursor.execute(f"ALTER TABLE invoices DROP COLUMN {col}_old")

        cursor.execute("PRAGMA table_info(vouchers)")
        if 'amount' in [c[1] for c in cursor.fetchall()]:
            cursor.execute("ALTER TABLE vouchers RENAME COLUMN amount TO amount_old")
            cursor.execute("ALTER TABLE vouchers ADD COLUMN amount TEXT DEFAULT '0'")
            cursor.execute("UPDATE vouchers SET amount = CAST(amount_old AS TEXT) WHERE amount_old IS NOT NULL")
            cursor.execute("ALTER TABLE vouchers DROP COLUMN amount_old")

        cursor.execute("PRAGMA table_info(expenses)")
        if 'amount' in [c[1] for c in cursor.fetchall()]:
            cursor.execute("ALTER TABLE expenses RENAME COLUMN amount TO amount_old")
            cursor.execute("ALTER TABLE expenses ADD COLUMN amount TEXT DEFAULT '0'")
            cursor.execute("UPDATE expenses SET amount = CAST(amount_old AS TEXT) WHERE amount_old IS NOT NULL")
            cursor.execute("ALTER TABLE expenses DROP COLUMN amount_old")

        cursor.execute("PRAGMA table_info(exchange_rates)")
        if 'rate_to_usd' in [c[1] for c in cursor.fetchall()]:
            cursor.execute("ALTER TABLE exchange_rates RENAME COLUMN rate_to_usd TO rate_to_usd_old")
            cursor.execute("ALTER TABLE exchange_rates ADD COLUMN rate_to_usd TEXT NOT NULL DEFAULT '1.0'")
            cursor.execute("UPDATE exchange_rates SET rate_to_usd = CAST(rate_to_usd_old AS TEXT) WHERE rate_to_usd_old IS NOT NULL")
            cursor.execute("ALTER TABLE exchange_rates DROP COLUMN rate_to_usd_old")

        cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            default_hash = hash_password('admin123')
            now = datetime.now().isoformat()
            cursor.execute("INSERT INTO users (id, username, password_hash, role, full_name, created_at, cash_balance) VALUES (?,?,?,?,?,?,?)",
                           ('admin', 'admin', default_hash, 'admin', 'المدير العام', now, '0'))
        default_accounts = [
            ('الصندوق', 'asset'), ('المبيعات', 'income'), ('المشتريات', 'expense'),
            ('المخزون', 'asset'), ('مصاريف عامة', 'expense'), ('رأس المال', 'equity')
        ]
        for name, typ in default_accounts:
            cursor.execute("INSERT OR IGNORE INTO accounts (user_id, name, type, balance) VALUES (?,?,?,?)", ('local_user', name, typ, '0'))

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_user_id ON items(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_name ON items(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_user_id ON invoices(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_customer_id ON invoices(customer_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_supplier_id ON invoices(supplier_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_date ON invoices(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_type ON invoices(type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoice_lines_invoice_id ON invoice_lines(invoice_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoice_lines_item_id ON invoice_lines(item_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vouchers_user_id ON vouchers(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_user_id ON expenses(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_customers_user_id ON customers(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_suppliers_user_id ON suppliers(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_suppliers_name ON suppliers(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_categories_user_id ON categories(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_categories_name ON categories(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_item_units_item_id ON item_units(item_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_movements_item_id ON inventory_movements(item_id)")

        default_rates = {'USD':'1.0','EUR':'1.08','GBP':'1.25','SAR':'0.266','AED':'0.272','SYP':'0.0000729927'}
        now = datetime.now().isoformat()
        for code, rate in default_rates.items():
            cursor.execute("INSERT OR IGNORE INTO exchange_rates (currency_code, rate_to_usd, updated_at) VALUES (?,?,?)",
                           (code, rate, now))
        conn.commit()

    # ========== دوال العملات ==========
    def get_exchange_rate(self, currency_code):
        cur = self.connect().cursor()
        cur.execute("SELECT rate_to_usd FROM exchange_rates WHERE currency_code = ?", (currency_code,))
        row = cur.fetchone()
        return float(row['rate_to_usd']) if row else 1.0

    def get_all_exchange_rates(self):
        cur = self.connect().cursor()
        cur.execute("SELECT currency_code, rate_to_usd, updated_at FROM exchange_rates ORDER BY currency_code")
        rows = cur.fetchall()
        return [{'currency_code': r['currency_code'], 'rate_to_usd': float(r['rate_to_usd']), 'updated_at': r['updated_at']} for r in rows]

    def update_exchange_rate(self, currency_code, rate_to_usd):
        cur = self.connect().cursor()
        cur.execute("UPDATE exchange_rates SET rate_to_usd = ?, updated_at = ? WHERE currency_code = ?",
                    (str(rate_to_usd), datetime.now().isoformat(), currency_code))
        self.conn.commit()

    def add_exchange_rate(self, currency_code, rate_to_usd):
        cur = self.connect().cursor()
        cur.execute("INSERT INTO exchange_rates (currency_code, rate_to_usd, updated_at) VALUES (?,?,?)",
                    (currency_code, str(rate_to_usd), datetime.now().isoformat()))
        self.conn.commit()

    def delete_exchange_rate(self, currency_code):
        if currency_code == 'USD': return False
        cur = self.connect().cursor()
        cur.execute("DELETE FROM exchange_rates WHERE currency_code = ?", (currency_code,))
        self.conn.commit()
        return True

    # ========== دوال المستخدمين ==========
    def register_user(self, username, password, full_name='', role='user') -> bool:
        conn = self.connect()
        cur = conn.cursor()
        try:
            uid = secrets.token_hex(8)
            phash = hash_password(password)
            now = datetime.now().isoformat()
            cur.execute("INSERT INTO users (id, username, password_hash, role, full_name, created_at, cash_balance) VALUES (?,?,?,?,?,?,?)",
                        (uid, username, phash, role, full_name, now, '0'))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def login(self, username, password) -> bool:
        conn = self.connect()
        cur = conn.cursor()
        cur.execute("SELECT id, password_hash, role FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        if row and verify_password(password, row['password_hash']):
            cur.execute("UPDATE users SET last_login = datetime('now') WHERE id = ?", (row['id'],))
            conn.commit()
            Session.set_current_user(row['id'], row['role'])
            return True
        return False

    def get_users(self) -> List[Dict]:
        if Session.get_current_user_role() != 'admin':
            return []
        cur = self.connect().cursor()
        cur.execute("SELECT id, username, role, full_name, created_at, last_login FROM users")
        return [dict(row) for row in cur.fetchall()]

    def delete_user(self, user_id: str) -> bool:
        if Session.get_current_user_role() != 'admin' or user_id == 'admin':
            return False
        cur = self.connect().cursor()
        for tbl in ['customers','suppliers','categories','items','invoices','vouchers','expenses','accounts','inventory_movements']:
            cur.execute(f"DELETE FROM {tbl} WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
        self.conn.commit()
        return True

    def change_password(self, user_id, old_password, new_password) -> bool:
        cur = self.connect().cursor()
        cur.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        if row and verify_password(old_password, row['password_hash']):
            new_hash = hash_password(new_password)
            cur.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
            self.conn.commit()
            return True
        return False

    def _get_user_filter(self, table='') -> str:
        uid = Session.get_current_user_id()
        if not uid: return "1=0"
        return f"{table}.user_id = '{uid}'" if table else f"user_id = '{uid}'"

    # ========== العملاء والموردين ==========
    def get_customers(self, search: str = None) -> List[Dict]:
        cur = self.connect().cursor()
        query = f"SELECT * FROM customers WHERE {self._get_user_filter('customers')}"
        params = []
        if search:
            query += " AND (name LIKE ? OR phone LIKE ?)"
            params.append(f"%{search}%")
            params.append(f"%{search}%")
        query += " ORDER BY name"
        cur.execute(query, params)
        rows = cur.fetchall()
        customers = []
        for row in rows:
            d = dict(row)
            d['balance'] = float(d.get('balance', '0'))
            customers.append(d)
        return customers

    def add_customer(self, name, phone='', address='') -> int:
        cur = self.connect().cursor()
        try:
            cur.execute("INSERT INTO customers (user_id, name, phone, address, balance) VALUES (?,?,?,?,?)",
                        (Session.get_current_user_id(), name, phone, address, '0'))
            self.conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            raise Exception("اسم العميل موجود مسبقاً")

    def update_customer(self, cid, name, phone, address):
        cur = self.connect().cursor()
        try:
            cur.execute(f"UPDATE customers SET name=?, phone=?, address=? WHERE id=? AND {self._get_user_filter('customers')}",
                        (name, phone, address, cid))
            self.conn.commit()
        except sqlite3.IntegrityError:
            raise Exception("اسم العميل موجود مسبقاً")

    def delete_customer(self, cid):
        cur = self.connect().cursor()
        cur.execute("SELECT id FROM invoices WHERE customer_id=? AND user_id=? AND deleted_at IS NULL", (cid, Session.get_current_user_id()))
        if cur.fetchone():
            raise Exception("لا يمكن حذف العميل لوجود فواتير غير ملغاة مرتبطة به")
        cur.execute(f"DELETE FROM customers WHERE id=? AND {self._get_user_filter('customers')}", (cid,))
        self.conn.commit()

    def get_suppliers(self, search: str = None) -> List[Dict]:
        cur = self.connect().cursor()
        query = f"SELECT * FROM suppliers WHERE {self._get_user_filter('suppliers')}"
        params = []
        if search:
            query += " AND (name LIKE ? OR phone LIKE ?)"
            params.append(f"%{search}%")
            params.append(f"%{search}%")
        query += " ORDER BY name"
        cur.execute(query, params)
        rows = cur.fetchall()
        suppliers = []
        for row in rows:
            d = dict(row)
            d['balance'] = float(d.get('balance', '0'))
            suppliers.append(d)
        return suppliers

    def add_supplier(self, name, phone='', address='') -> int:
        cur = self.connect().cursor()
        try:
            cur.execute("INSERT INTO suppliers (user_id, name, phone, address, balance) VALUES (?,?,?,?,?)",
                        (Session.get_current_user_id(), name, phone, address, '0'))
            self.conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            raise Exception("اسم المورد موجود مسبقاً")

    def update_supplier(self, sid, name, phone, address):
        cur = self.connect().cursor()
        try:
            cur.execute(f"UPDATE suppliers SET name=?, phone=?, address=? WHERE id=? AND {self._get_user_filter('suppliers')}",
                        (name, phone, address, sid))
            self.conn.commit()
        except sqlite3.IntegrityError:
            raise Exception("اسم المورد موجود مسبقاً")

    def delete_supplier(self, sid):
        cur = self.connect().cursor()
        cur.execute("SELECT id FROM invoices WHERE supplier_id=? AND user_id=? AND deleted_at IS NULL", (sid, Session.get_current_user_id()))
        if cur.fetchone():
            raise Exception("لا يمكن حذف المورد لوجود فواتير غير ملغاة مرتبطة به")
        cur.execute(f"DELETE FROM suppliers WHERE id=? AND {self._get_user_filter('suppliers')}", (sid,))
        self.conn.commit()

    def get_categories(self, search: str = None) -> List[Dict]:
        cur = self.connect().cursor()
        query = f"SELECT * FROM categories WHERE {self._get_user_filter('categories')}"
        if search:
            query += " AND name LIKE ?"
            cur.execute(query, (f"%{search}%",))
        else:
            cur.execute(query)
        return [dict(row) for row in cur.fetchall()]

    def add_category(self, name) -> int:
        cur = self.connect().cursor()
        try:
            cur.execute("INSERT INTO categories (user_id, name) VALUES (?,?)", (Session.get_current_user_id(), name))
            self.conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            raise Exception("اسم التصنيف موجود مسبقاً")

    def update_category(self, cid, name):
        cur = self.connect().cursor()
        try:
            cur.execute(f"UPDATE categories SET name=? WHERE id=? AND {self._get_user_filter('categories')}", (name, cid))
            self.conn.commit()
        except sqlite3.IntegrityError:
            raise Exception("اسم التصنيف موجود مسبقاً")

    def delete_category(self, cid):
        cur = self.connect().cursor()
        cur.execute("SELECT id FROM items WHERE category_id=? AND user_id=?", (cid, Session.get_current_user_id()))
        if cur.fetchone():
            raise Exception("لا يمكن حذف التصنيف لوجود مواد مرتبطة به")
        cur.execute(f"DELETE FROM categories WHERE id=? AND {self._get_user_filter('categories')}", (cid,))
        self.conn.commit()

    # ========== المواد (مع دعم الباركود والبحث) ==========
    def get_items(self, search: str = None) -> List[Dict]:
        cur = self.connect().cursor()
        query = """
            SELECT 
                i.*,
                c.name as category_name,
                COALESCE(p.purchase_qty, 0) as purchase_qty,
                COALESCE(s.sale_qty, 0) as sale_qty,
                COALESCE(p.purchase_count, 0) as purchase_count,
                COALESCE(s.sale_count, 0) as sale_count,
                p.last_purchase_date,
                s.last_sale_date
            FROM items i
            LEFT JOIN categories c ON i.category_id = c.id
            LEFT JOIN (
                SELECT 
                    il.item_id,
                    SUM(CAST(il.quantity_in_base AS REAL)) as purchase_qty,
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
                    SUM(CAST(il.quantity_in_base AS REAL)) as sale_qty,
                    COUNT(*) as sale_count,
                    MAX(inv.date) as last_sale_date
                FROM invoice_lines il
                JOIN invoices inv ON il.invoice_id = inv.id
                WHERE inv.type = 'sale' AND inv.deleted_at IS NULL AND inv.user_id = ?
                GROUP BY il.item_id
            ) s ON i.id = s.item_id
            WHERE i.user_id = ?
        """
        params = [Session.get_current_user_id(), Session.get_current_user_id(), Session.get_current_user_id()]
        if search:
            query += " AND (i.name LIKE ? OR i.barcode LIKE ?)"
            params.append(f"%{search}%")
            params.append(f"%{search}%")
        query += " ORDER BY i.name"
        cur.execute(query, params)
        items = []
        for row in cur.fetchall():
            item = dict(row)
            for field in ['purchase_price', 'selling_price', 'average_cost']:
                item[field] = float(item.get(field, '0'))
            item['quantity'] = float(item.get('quantity', '0'))
            item['available'] = item['quantity']
            item['total_value'] = item['available'] * item['average_cost']
            cur2 = self.connect().cursor()
            cur2.execute("SELECT id, unit_name, conversion_factor FROM item_units WHERE item_id = ?", (item['id'],))
            subunits = cur2.fetchall()
            item['item_units'] = [{'id': su['id'], 'unit_name': su['unit_name'], 'conversion_factor': float(su['conversion_factor'])} for su in subunits]
            items.append(item)
        return items

    def get_item_by_barcode(self, barcode: str) -> Optional[Dict]:
        if not barcode:
            return None
        cur = self.connect().cursor()
        cur.execute("SELECT * FROM items WHERE barcode = ? AND user_id = ?", (barcode, Session.get_current_user_id()))
        row = cur.fetchone()
        if row:
            item = dict(row)
            for field in ['purchase_price', 'selling_price', 'average_cost', 'quantity']:
                item[field] = float(item.get(field, '0'))
            return item
        return None

    def add_item(self, data):
        cur = self.connect().cursor()
        try:
            cur.execute("""
                INSERT INTO items (user_id, name, category_id, item_type, purchase_price, selling_price, quantity, unit, average_cost, purchase_qty, sale_qty, barcode)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (Session.get_current_user_id(), data['name'], data.get('category_id'), data.get('item_type','مخزون'),
                  decimal_to_storage(Decimal(str(data.get('purchase_price', 0)))),
                  decimal_to_storage(Decimal(str(data.get('selling_price', 0)))),
                  decimal_to_storage(Decimal(str(data.get('quantity', 0)))),
                  data.get('unit', ''),
                  decimal_to_storage(Decimal(str(data.get('average_cost', data.get('purchase_price', 0))))),
                  decimal_to_storage(Decimal(str(data.get('quantity', 0)))), '0',
                  data.get('barcode')))
            self.conn.commit()
            if Decimal(str(data.get('quantity', 0))) > 0:
                self._record_inventory_movement(cur.lastrowid, 'adjustment', Decimal(str(data['quantity'])), Decimal(str(data.get('purchase_price', 0))), None, datetime.now().isoformat())
            return cur.lastrowid
        except sqlite3.IntegrityError as e:
            if 'UNIQUE constraint failed: items.barcode' in str(e):
                raise Exception("الباركود موجود مسبقاً")
            raise Exception("اسم المادة موجود مسبقاً")

    def update_item(self, item_id, data):
        cur = self.connect().cursor()
        try:
            cur.execute(f"""
                UPDATE items SET name=?, category_id=?, item_type=?, purchase_price=?, selling_price=?, quantity=?, unit=?, average_cost=?, barcode=?
                WHERE id=? AND user_id=?
            """, (data['name'], data.get('category_id'), data.get('item_type'),
                  decimal_to_storage(Decimal(str(data.get('purchase_price', 0)))),
                  decimal_to_storage(Decimal(str(data.get('selling_price', 0)))),
                  decimal_to_storage(Decimal(str(data.get('quantity', 0)))),
                  data.get('unit', ''),
                  decimal_to_storage(Decimal(str(data.get('average_cost', data.get('purchase_price', 0))))),
                  data.get('barcode'), item_id, Session.get_current_user_id()))
            self.conn.commit()
        except sqlite3.IntegrityError as e:
            if 'UNIQUE constraint failed: items.barcode' in str(e):
                raise Exception("الباركود موجود مسبقاً")
            raise Exception("اسم المادة موجود مسبقاً")

    def delete_item(self, item_id):
        cur = self.connect().cursor()
        cur.execute("""
            SELECT il.id FROM invoice_lines il
            JOIN invoices inv ON il.invoice_id = inv.id
            WHERE il.item_id = ? AND inv.deleted_at IS NULL LIMIT 1
        """, (item_id,))
        if cur.fetchone():
            raise Exception("لا يمكن حذف المادة لاستخدامها في فواتير (غير ملغاة)")
        cur.execute("DELETE FROM item_units WHERE item_id=?", (item_id,))
        cur.execute("DELETE FROM inventory_movements WHERE item_id=?", (item_id,))
        cur.execute("DELETE FROM items WHERE id=? AND user_id=?", (item_id, Session.get_current_user_id()))
        self.conn.commit()

    def _record_inventory_movement(self, item_id, movement_type, quantity: Decimal, unit_cost: Decimal, reference_id, date_str):
        cur = self.connect().cursor()
        cur.execute("""
            INSERT INTO inventory_movements (item_id, user_id, movement_type, quantity, unit_cost, reference_id, movement_date)
            VALUES (?,?,?,?,?,?,?)
        """, (item_id, Session.get_current_user_id(), movement_type, decimal_to_storage(quantity), decimal_to_storage(unit_cost), reference_id, date_str))
        self.conn.commit()

    def add_item_unit(self, item_id, unit_name, conversion_factor: Decimal):
        cur = self.connect().cursor()
        cur.execute("INSERT INTO item_units (item_id, unit_name, conversion_factor) VALUES (?,?,?)",
                    (item_id, unit_name, decimal_to_storage(conversion_factor)))
        self.conn.commit()
        return cur.lastrowid

    def get_item_units(self, item_id):
        cur = self.connect().cursor()
        cur.execute("SELECT id, unit_name, conversion_factor FROM item_units WHERE item_id = ?", (item_id,))
        rows = cur.fetchall()
        return [{'id': r['id'], 'unit_name': r['unit_name'], 'conversion_factor': float(r['conversion_factor'])} for r in rows]

    def delete_item_unit(self, unit_id):
        cur = self.connect().cursor()
        cur.execute("DELETE FROM item_units WHERE id = ?", (unit_id,))
        self.conn.commit()

    def clear_item_units(self, item_id):
        cur = self.connect().cursor()
        cur.execute("DELETE FROM item_units WHERE item_id = ?", (item_id,))
        self.conn.commit()

    def _recalculate_item_average_cost(self, item_id):
        cur = self.connect().cursor()
        cur.execute("""
            SELECT SUM(CAST(quantity AS REAL)) as total_qty, SUM(CAST(quantity AS REAL) * CAST(unit_cost AS REAL)) as total_cost
            FROM inventory_movements
            WHERE item_id = ? AND movement_type = 'purchase'
        """, (item_id,))
        row = cur.fetchone()
        total_qty = row['total_qty'] or 0
        total_cost = row['total_cost'] or 0
        avg = total_cost / total_qty if total_qty > 0 else 0
        cur.execute("UPDATE items SET average_cost = ? WHERE id = ?", (str(avg), item_id))
        return avg

    def _update_item_quantity(self, item_id):
        cur = self.connect().cursor()
        cur.execute("""
            SELECT SUM(CASE WHEN movement_type IN ('purchase','adjustment') THEN CAST(quantity AS REAL) ELSE -CAST(quantity AS REAL) END) as total_qty
            FROM inventory_movements
            WHERE item_id = ?
        """, (item_id,))
        row = cur.fetchone()
        new_qty = row['total_qty'] or 0
        cur.execute("UPDATE items SET quantity = ? WHERE id = ?", (str(new_qty), item_id))
        return new_qty

    def _update_item_average_cost(self, item_id, new_qty_base: Decimal, unit_cost: Decimal, is_purchase):
        if is_purchase:
            self._record_inventory_movement(item_id, 'purchase', new_qty_base, unit_cost, None, datetime.now().isoformat())
        else:
            self._record_inventory_movement(item_id, 'sale', new_qty_base, unit_cost, None, datetime.now().isoformat())
        self._recalculate_item_average_cost(item_id)
        self._update_item_quantity(item_id)

    def _reverse_item_average_cost(self, item_id, old_qty_base: Decimal, old_unit_cost: Decimal, is_purchase):
        cur = self.connect().cursor()
        if is_purchase:
            cur.execute("""
                DELETE FROM inventory_movements
                WHERE item_id = ? AND movement_type = 'purchase'
                ORDER BY id DESC LIMIT 1
            """, (item_id,))
        else:
            cur.execute("""
                DELETE FROM inventory_movements
                WHERE item_id = ? AND movement_type = 'sale'
                ORDER BY id DESC LIMIT 1
            """, (item_id,))
        self.conn.commit()
        self._recalculate_item_average_cost(item_id)
        self._update_item_quantity(item_id)

    # ========== الفواتير ==========
    def create_invoice(self, data):
        conn = self.connect()
        cur = conn.cursor()
        paid_amount = Decimal(str(data.get('paid_amount', 0)))
        total = Decimal(str(data['total']))
        if paid_amount < 0: paid_amount = Decimal('0')
        if data['type'] == 'sale' and paid_amount > total: paid_amount = total
        elif data['type'] == 'purchase' and paid_amount > total: paid_amount = total
        try:
            cur.execute("BEGIN TRANSACTION")
            cur.execute("""
                INSERT INTO invoices (user_id, type, customer_id, supplier_id, date, reference, notes, total, paid, status)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (Session.get_current_user_id(), data['type'], data.get('customer_id'), data.get('supplier_id'),
                  data['date'], data.get('reference', ''), data.get('notes', ''),
                  decimal_to_storage(total), decimal_to_storage(paid_amount), 'active'))
            invoice_id = cur.lastrowid
            for line in data['lines']:
                base_qty = Decimal(str(line.get('base_qty', line['quantity'])))
                unit_cost = Decimal(str(line['unit_price']))
                cur.execute("""
                    INSERT INTO invoice_lines (invoice_id, item_id, quantity, unit_price, total, unit, quantity_in_base, unit_cost, cost_amount)
                    VALUES (?,?,?,?,?,?,?,?,?)
                """, (invoice_id, line['item_id'],
                      decimal_to_storage(Decimal(str(line['quantity']))),
                      decimal_to_storage(unit_cost),
                      decimal_to_storage(Decimal(str(line['total']))),
                      line.get('unit', ''),
                      decimal_to_storage(base_qty),
                      decimal_to_storage(unit_cost), '0'))
                line_id = cur.lastrowid
                if data['type'] == 'purchase':
                    self._update_item_average_cost(line['item_id'], base_qty, unit_cost, True)
                    cost_amt = unit_cost * base_qty
                    cur.execute("UPDATE invoice_lines SET cost_amount = ? WHERE id = ?", (decimal_to_storage(cost_amt), line_id))
                else:
                    cur.execute("SELECT average_cost FROM items WHERE id=? AND user_id=?", (line['item_id'], Session.get_current_user_id()))
                    avg_cost = Decimal(str(cur.fetchone()['average_cost']))
                    cost_amt = base_qty * avg_cost
                    cur.execute("UPDATE invoice_lines SET cost_amount = ? WHERE id = ?", (decimal_to_storage(cost_amt), line_id))
                    self._update_item_average_cost(line['item_id'], base_qty, unit_cost, False)
            if data['type'] == 'sale' and data.get('customer_id'):
                cur.execute("UPDATE customers SET balance = balance + ? WHERE id=? AND user_id=?",
                            (decimal_to_storage(total - paid_amount), data['customer_id'], Session.get_current_user_id()))
            elif data['type'] == 'purchase' and data.get('supplier_id'):
                cur.execute("UPDATE suppliers SET balance = balance + ? WHERE id=? AND user_id=?",
                            (decimal_to_storage(total - paid_amount), data['supplier_id'], Session.get_current_user_id()))
            if paid_amount > 0:
                if data['type'] == 'sale':
                    cur.execute("UPDATE users SET cash_balance = cash_balance + ? WHERE id=?",
                                (decimal_to_storage(paid_amount), Session.get_current_user_id()))
                else:
                    cur.execute("UPDATE users SET cash_balance = cash_balance - ? WHERE id=?",
                                (decimal_to_storage(paid_amount), Session.get_current_user_id()))
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
        """, (Session.get_current_user_id(),))
        invoices = []
        for row in cur.fetchall():
            inv = dict(row)
            inv['total'] = float(inv.get('total', '0'))
            inv['paid'] = float(inv.get('paid', '0'))
            invoices.append(inv)
        for inv in invoices:
            cur.execute("""
                SELECT il.*, it.name as item_name
                FROM invoice_lines il
                LEFT JOIN items it ON il.item_id = it.id
                WHERE il.invoice_id=?
            """, (inv['id'],))
            lines = []
            for lrow in cur.fetchall():
                line = dict(lrow)
                for field in ['quantity', 'unit_price', 'total', 'quantity_in_base', 'unit_cost', 'cost_amount']:
                    if field in line:
                        line[field] = float(line[field] or 0)
                lines.append(line)
            inv['lines'] = lines
        return invoices

    def get_invoices_by_id(self, invoice_id):
        cur = self.connect().cursor()
        cur.execute("""
            SELECT i.*, c.name as customer_name, s.name as supplier_name
            FROM invoices i
            LEFT JOIN customers c ON i.customer_id = c.id
            LEFT JOIN suppliers s ON i.supplier_id = s.id
            WHERE i.id=? AND i.user_id=?
        """, (invoice_id, Session.get_current_user_id()))
        inv = cur.fetchone()
        if not inv: return None
        inv = dict(inv)
        inv['total'] = float(inv.get('total', '0'))
        inv['paid'] = float(inv.get('paid', '0'))
        cur.execute("""
            SELECT il.*, it.name as item_name
            FROM invoice_lines il
            LEFT JOIN items it ON il.item_id = it.id
            WHERE il.invoice_id=?
        """, (invoice_id,))
        lines = []
        for lrow in cur.fetchall():
            line = dict(lrow)
            for field in ['quantity', 'unit_price', 'total', 'quantity_in_base', 'unit_cost', 'cost_amount']:
                if field in line:
                    line[field] = float(line[field] or 0)
            lines.append(line)
        inv['lines'] = lines
        return inv

    def get_invoices_filtered(self, search: str = None, inv_type: str = None,
                              start_date: str = None, end_date: str = None,
                              customer_id: int = None, supplier_id: int = None) -> List[Dict]:
        conn = self.connect()
        cur = conn.cursor()
        query = """
            SELECT i.*, c.name as customer_name, s.name as supplier_name
            FROM invoices i
            LEFT JOIN customers c ON i.customer_id = c.id
            LEFT JOIN suppliers s ON i.supplier_id = s.id
            WHERE i.user_id = ? AND i.deleted_at IS NULL
        """
        params = [Session.get_current_user_id()]
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
        cur.execute(query, params)
        invoices = []
        for row in cur.fetchall():
            inv = dict(row)
            inv['total'] = float(inv.get('total', '0'))
            inv['paid'] = float(inv.get('paid', '0'))
            invoices.append(inv)
        return invoices

    def _reverse_invoice_effects(self, inv):
        cur = self.connect().cursor()
        for line in inv['lines']:
            base_qty = Decimal(str(line['quantity_in_base']))
            if inv['type'] == 'purchase':
                self._reverse_item_average_cost(line['item_id'], base_qty, Decimal(str(line['unit_cost'])), True)
            else:
                self._reverse_item_average_cost(line['item_id'], base_qty, Decimal(str(line['unit_price'])), False)
        total = Decimal(str(inv['total']))
        paid = Decimal(str(inv['paid']))
        if inv['type'] == 'sale' and inv.get('customer_id'):
            cur.execute("UPDATE customers SET balance = balance - ? WHERE id=? AND user_id=?",
                        (decimal_to_storage(total - paid), inv['customer_id'], Session.get_current_user_id()))
        elif inv['type'] == 'purchase' and inv.get('supplier_id'):
            cur.execute("UPDATE suppliers SET balance = balance - ? WHERE id=? AND user_id=?",
                        (decimal_to_storage(total - paid), inv['supplier_id'], Session.get_current_user_id()))
        if paid > 0:
            if inv['type'] == 'sale':
                cur.execute("UPDATE users SET cash_balance = cash_balance - ? WHERE id=?",
                            (decimal_to_storage(paid), Session.get_current_user_id()))
            else:
                cur.execute("UPDATE users SET cash_balance = cash_balance + ? WHERE id=?",
                            (decimal_to_storage(paid), Session.get_current_user_id()))

    def update_invoice(self, invoice_id, new_data):
        conn = self.connect()
        cur = conn.cursor()
        try:
            cur.execute("BEGIN TRANSACTION")
            old_inv = self.get_invoices_by_id(invoice_id)
            if not old_inv: raise Exception("الفاتورة غير موجودة")
            self._reverse_invoice_effects(old_inv)
            cur.execute("UPDATE invoices SET deleted_at = datetime('now') WHERE id=?", (invoice_id,))
            new_data['id'] = None
            new_id = self.create_invoice(new_data)
            conn.commit()
            return new_id
        except Exception as e:
            conn.rollback()
            raise e

    def delete_invoice(self, invoice_id):
        conn = self.connect()
        cur = conn.cursor()
        try:
            cur.execute("BEGIN TRANSACTION")
            inv = self.get_invoices_by_id(invoice_id)
            if not inv: raise Exception("الفاتورة غير موجودة")
            self._reverse_invoice_effects(inv)
            cur.execute("UPDATE invoices SET deleted_at = datetime('now') WHERE id=? AND user_id=?", (invoice_id, Session.get_current_user_id()))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e

    # ========== المصاريف ==========
    def get_expenses(self, search: str = None) -> List[Dict]:
        cur = self.connect().cursor()
        query = "SELECT * FROM expenses WHERE user_id=?"
        params = [Session.get_current_user_id()]
        if search:
            query += " AND description LIKE ?"
            params.append(f"%{search}%")
        query += " ORDER BY id DESC"
        cur.execute(query, params)
        expenses = []
        for row in cur.fetchall():
            exp = dict(row)
            exp['amount'] = float(exp.get('amount', '0'))
            expenses.append(exp)
        return expenses

    def add_expense(self, amount: Decimal, date, desc):
        cur = self.connect().cursor()
        cur.execute("INSERT INTO expenses (user_id, amount, expense_date, description) VALUES (?,?,?,?)",
                    (Session.get_current_user_id(), decimal_to_storage(amount), date, desc))
        cur.execute("UPDATE users SET cash_balance = cash_balance - ? WHERE id=?", (decimal_to_storage(amount), Session.get_current_user_id()))
        self.conn.commit()
        return cur.lastrowid

    def delete_expense(self, exp_id):
        cur = self.connect().cursor()
        cur.execute("SELECT amount FROM expenses WHERE id=? AND user_id=?", (exp_id, Session.get_current_user_id()))
        row = cur.fetchone()
        if row:
            amount = Decimal(str(row['amount']))
            cur.execute("UPDATE users SET cash_balance = cash_balance + ? WHERE id=?", (decimal_to_storage(amount), Session.get_current_user_id()))
        cur.execute("DELETE FROM expenses WHERE id=? AND user_id=?", (exp_id, Session.get_current_user_id()))
        self.conn.commit()

    # ========== السندات ==========
    def get_vouchers(self, search: str = None) -> List[Dict]:
        cur = self.connect().cursor()
        query = "SELECT * FROM vouchers WHERE user_id=?"
        params = [Session.get_current_user_id()]
        if search:
            query += " AND (description LIKE ? OR reference LIKE ?)"
            params.append(f"%{search}%")
            params.append(f"%{search}%")
        query += " ORDER BY id DESC"
        cur.execute(query, params)
        vouchers = []
        for row in cur.fetchall():
            v = dict(row)
            v['amount'] = float(v.get('amount', '0'))
            vouchers.append(v)
        return vouchers

    def add_voucher(self, data):
        cur = self.connect().cursor()
        cur.execute("""
            INSERT INTO vouchers (user_id, type, date, amount, description, reference, customer_id, supplier_id, invoice_id)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (Session.get_current_user_id(), data['type'], data['date'], decimal_to_storage(Decimal(str(data['amount']))), data.get('description',''),
              data.get('reference',''), data.get('customer_id'), data.get('supplier_id'), data.get('invoice_id')))
        vid = cur.lastrowid
        sign = 1 if data['type'] == 'receipt' else -1
        cur.execute("UPDATE users SET cash_balance = cash_balance + ? WHERE id=?", (decimal_to_storage(Decimal(str(sign * data['amount']))), Session.get_current_user_id()))
        if data.get('customer_id'):
            cur.execute("UPDATE customers SET balance = balance - ? WHERE id=? AND user_id=?", (decimal_to_storage(Decimal(str(data['amount']))), data['customer_id'], Session.get_current_user_id()))
        elif data.get('supplier_id'):
            cur.execute("UPDATE suppliers SET balance = balance - ? WHERE id=? AND user_id=?", (decimal_to_storage(Decimal(str(data['amount']))), data['supplier_id'], Session.get_current_user_id()))
        self.conn.commit()
        return vid

    def delete_voucher(self, vid):
        cur = self.connect().cursor()
        cur.execute("SELECT type, amount, customer_id, supplier_id FROM vouchers WHERE id=? AND user_id=?", (vid, Session.get_current_user_id()))
        row = cur.fetchone()
        if row:
            amount = Decimal(str(row['amount']))
            sign = -1 if row['type'] == 'receipt' else 1
            cur.execute("UPDATE users SET cash_balance = cash_balance + ? WHERE id=?", (decimal_to_storage(Decimal(str(sign * amount))), Session.get_current_user_id()))
            if row['customer_id']:
                cur.execute("UPDATE customers SET balance = balance + ? WHERE id=? AND user_id=?", (decimal_to_storage(amount), row['customer_id'], Session.get_current_user_id()))
            elif row['supplier_id']:
                cur.execute("UPDATE suppliers SET balance = balance + ? WHERE id=? AND user_id=?", (decimal_to_storage(amount), row['supplier_id'], Session.get_current_user_id()))
        cur.execute("DELETE FROM vouchers WHERE id=? AND user_id=?", (vid, Session.get_current_user_id()))
        self.conn.commit()

    # ========== الإحصائيات والتقارير ==========
    def get_summary(self) -> Dict:
        cur = self.connect().cursor()
        sales = cur.execute("SELECT SUM(CAST(total AS REAL)) FROM invoices WHERE type='sale' AND user_id=? AND deleted_at IS NULL", (Session.get_current_user_id(),)).fetchone()[0] or 0
        purchases = cur.execute("SELECT SUM(CAST(total AS REAL)) FROM invoices WHERE type='purchase' AND user_id=? AND deleted_at IS NULL", (Session.get_current_user_id(),)).fetchone()[0] or 0
        expenses = cur.execute("SELECT SUM(CAST(amount AS REAL)) FROM expenses WHERE user_id=?", (Session.get_current_user_id(),)).fetchone()[0] or 0
        net = sales - purchases - expenses
        receivables = cur.execute("SELECT SUM(CAST(balance AS REAL)) FROM customers WHERE user_id=?", (Session.get_current_user_id(),)).fetchone()[0] or 0
        payables = cur.execute("SELECT SUM(CAST(balance AS REAL)) FROM suppliers WHERE user_id=?", (Session.get_current_user_id(),)).fetchone()[0] or 0
        cash = cur.execute("SELECT CAST(cash_balance AS REAL) FROM users WHERE id=?", (Session.get_current_user_id(),)).fetchone()[0] or 0
        return {'net_profit': net, 'cash_balance': cash, 'receivables': receivables, 'payables': payables,
                'total_sales': sales, 'total_purchases': purchases, 'total_expenses': expenses}

    def get_trial_balance(self) -> List[Dict]:
        cur = self.connect().cursor()
        sales = cur.execute("SELECT SUM(CAST(total AS REAL)) FROM invoices WHERE type='sale' AND user_id=? AND deleted_at IS NULL", (Session.get_current_user_id(),)).fetchone()[0] or 0
        purchases = cur.execute("SELECT SUM(CAST(total AS REAL)) FROM invoices WHERE type='purchase' AND user_id=? AND deleted_at IS NULL", (Session.get_current_user_id(),)).fetchone()[0] or 0
        expenses = cur.execute("SELECT SUM(CAST(amount AS REAL)) FROM expenses WHERE user_id=?", (Session.get_current_user_id(),)).fetchone()[0] or 0
        cash = cur.execute("SELECT CAST(cash_balance AS REAL) FROM users WHERE id=?", (Session.get_current_user_id(),)).fetchone()[0] or 0
        receivables = cur.execute("SELECT SUM(CAST(balance AS REAL)) FROM customers WHERE user_id=?", (Session.get_current_user_id(),)).fetchone()[0] or 0
        payables = cur.execute("SELECT SUM(CAST(balance AS REAL)) FROM suppliers WHERE user_id=?", (Session.get_current_user_id(),)).fetchone()[0] or 0
        return [
            {'name':'الصندوق','debit':cash if cash>0 else 0,'credit':-cash if cash<0 else 0},
            {'name':'الذمم المدينة','debit':receivables,'credit':0},
            {'name':'الذمم الدائنة','debit':0,'credit':payables},
            {'name':'المبيعات','debit':0,'credit':sales},
            {'name':'المشتريات','debit':purchases,'credit':0},
            {'name':'المصاريف','debit':expenses,'credit':0}
        ]

    def get_income_statement(self) -> Dict:
        trial = self.get_trial_balance()
        inc = [t for t in trial if t['name']=='المبيعات']
        exp = [t for t in trial if t['name'] in ('المشتريات','المصاريف')]
        total_income = sum(i['credit'] for i in inc)
        total_expenses = sum(e['debit'] for e in exp)
        net = total_income - total_expenses
        return {'income':[{'name':i['name'],'balance':i['credit']} for i in inc],
                'expenses':[{'name':e['name'],'balance':e['debit']} for e in exp],
                'total_income':total_income,'total_expenses':total_expenses,'net_profit':net}

    def get_balance_sheet(self) -> Dict:
        trial = self.get_trial_balance()
        assets = [t for t in trial if t['name'] in ('الصندوق','الذمم المدينة')]
        liabilities = [t for t in trial if t['name']=='الذمم الدائنة']
        equity = [{'name':'رأس المال','credit':sum(a['debit'] for a in assets)-sum(l['credit'] for l in liabilities)}]
        return {
            'assets':assets,'liabilities':liabilities,'equity':equity,
            'total_assets':sum(a['debit'] for a in assets),
            'total_liabilities':sum(l['credit'] for l in liabilities),
            'total_equity':equity[0]['credit']
        }

    def get_customer_statement(self, cust_id):
        cur = self.connect().cursor()
        cur.execute("""
            SELECT date, reference, total as amount, 'فاتورة' as description, CAST(total AS REAL) as debit, 0 as credit
            FROM invoices WHERE customer_id=? AND type='sale' AND user_id=? AND deleted_at IS NULL
            UNION ALL
            SELECT date, reference, amount, 'سند قبض', 0, CAST(amount AS REAL)
            FROM vouchers WHERE customer_id=? AND type='receipt' AND user_id=?
            ORDER BY date
        """, (cust_id, Session.get_current_user_id(), cust_id, Session.get_current_user_id()))
        rows = [dict(row) for row in cur.fetchall()]
        balance = 0
        for r in rows:
            balance += r['debit'] - r['credit']
            r['balance'] = balance
        return rows

    def get_supplier_statement(self, supp_id):
        cur = self.connect().cursor()
        cur.execute("""
            SELECT date, reference, total as amount, 'فاتورة' as description, 0 as debit, CAST(total AS REAL) as credit
            FROM invoices WHERE supplier_id=? AND type='purchase' AND user_id=? AND deleted_at IS NULL
            UNION ALL
            SELECT date, reference, amount, 'سند دفع', CAST(amount AS REAL), 0
            FROM vouchers WHERE supplier_id=? AND type='payment' AND user_id=?
            ORDER BY date
        """, (supp_id, Session.get_current_user_id(), supp_id, Session.get_current_user_id()))
        rows = [dict(row) for row in cur.fetchall()]
        balance = 0
        for r in rows:
            balance += r['credit'] - r['debit']
            r['balance'] = balance
        return rows

    def export_full_database(self) -> bytes:
        tables = ['customers','suppliers','categories','items','item_units','invoices','invoice_lines','vouchers','expenses','users','inventory_movements','exchange_rates']
        data = {}
        uid = Session.get_current_user_id()
        for tbl in tables:
            cur = self.connect().cursor()
            if tbl == 'item_units':
                cur.execute("""
                    SELECT iu.* FROM item_units iu
                    JOIN items i ON iu.item_id = i.id
                    WHERE i.user_id = ?
                """, (uid,))
            elif tbl in ('inventory_movements', 'exchange_rates'):
                cur.execute(f"SELECT * FROM {tbl}")
            else:
                cur.execute(f"SELECT * FROM {tbl} WHERE user_id=?", (uid,))
            rows = cur.fetchall()
            data[tbl] = [dict(row) for row in rows]
        return json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')

    def import_full_database(self, json_bytes):
        data = json.loads(json_bytes.decode('utf-8'))
        conn = self.connect()
        cur = conn.cursor()
        try:
            cur.execute("BEGIN TRANSACTION")
            uid = Session.get_current_user_id()
            for tbl, rows in data.items():
                if tbl == 'item_units':
                    cur.execute("DELETE FROM item_units WHERE item_id IN (SELECT id FROM items WHERE user_id=?)", (uid,))
                elif tbl in ('inventory_movements', 'exchange_rates'):
                    cur.execute(f"DELETE FROM {tbl}")
                else:
                    cur.execute(f"DELETE FROM {tbl} WHERE user_id=?", (uid,))
                for row in rows:
                    if 'user_id' in row and tbl not in ('item_units','inventory_movements','exchange_rates'):
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
            SELECT strftime('%Y-%m', date) as month, SUM(CAST(total AS REAL)) as total
            FROM invoices
            WHERE type='sale' AND user_id=? AND deleted_at IS NULL
            GROUP BY month
            ORDER BY month
        """, (Session.get_current_user_id(),))
        rows = cur.fetchall()
        return [{'month':row['month'], 'total':row['total'] or 0} for row in rows]

    def get_monthly_profit(self):
        cur = self.connect().cursor()
        cur.execute("""
            SELECT strftime('%Y-%m', i.date) as month,
                   SUM(CASE WHEN i.type='sale' THEN CAST(i.total AS REAL) ELSE 0 END) -
                   SUM(CASE WHEN i.type='purchase' THEN CAST(i.total AS REAL) ELSE 0 END) -
                   COALESCE((SELECT SUM(CAST(amount AS REAL)) FROM expenses WHERE user_id=? AND strftime('%Y-%m', expense_date)=strftime('%Y-%m', i.date)), 0) as profit
            FROM invoices i
            WHERE i.user_id=? AND i.deleted_at IS NULL
            GROUP BY month
            ORDER BY month
        """, (Session.get_current_user_id(), Session.get_current_user_id()))
        rows = cur.fetchall()
        return [{'month':row['month'], 'profit':row['profit'] or 0} for row in rows]

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

    def get_trial_balance_filtered(self, start_date=None, end_date=None):
        cur = self.connect().cursor()
        sales = cur.execute("SELECT SUM(CAST(total AS REAL)) FROM invoices WHERE type='sale' AND user_id=? AND deleted_at IS NULL AND (date BETWEEN ? AND ?)",
                            (Session.get_current_user_id(), start_date, end_date)).fetchone()[0] or 0 if start_date and end_date else 0
        purchases = cur.execute("SELECT SUM(CAST(total AS REAL)) FROM invoices WHERE type='purchase' AND user_id=? AND deleted_at IS NULL AND (date BETWEEN ? AND ?)",
                                (Session.get_current_user_id(), start_date, end_date)).fetchone()[0] or 0 if start_date and end_date else 0
        expenses = cur.execute("SELECT SUM(CAST(amount AS REAL)) FROM expenses WHERE user_id=? AND (expense_date BETWEEN ? AND ?)",
                               (Session.get_current_user_id(), start_date, end_date)).fetchone()[0] or 0 if start_date and end_date else 0
        cash = cur.execute("SELECT CAST(cash_balance AS REAL) FROM users WHERE id=?", (Session.get_current_user_id(),)).fetchone()[0] or 0
        receivables = cur.execute("SELECT SUM(CAST(balance AS REAL)) FROM customers WHERE user_id=?", (Session.get_current_user_id(),)).fetchone()[0] or 0
        payables = cur.execute("SELECT SUM(CAST(balance AS REAL)) FROM suppliers WHERE user_id=?", (Session.get_current_user_id(),)).fetchone()[0] or 0
        return [
            {'name':'الصندوق','debit':cash if cash>0 else 0,'credit':-cash if cash<0 else 0},
            {'name':'الذمم المدينة','debit':receivables,'credit':0},
            {'name':'الذمم الدائنة','debit':0,'credit':payables},
            {'name':'المبيعات','debit':0,'credit':sales},
            {'name':'المشتريات','debit':purchases,'credit':0},
            {'name':'المصاريف','debit':expenses,'credit':0}
        ]

    def get_income_statement_filtered(self, start_date=None, end_date=None):
        trial = self.get_trial_balance_filtered(start_date, end_date)
        inc = [t for t in trial if t['name']=='المبيعات']
        exp = [t for t in trial if t['name'] in ('المشتريات','المصاريف')]
        total_income = sum(i['credit'] for i in inc)
        total_expenses = sum(e['debit'] for e in exp)
        net = total_income - total_expenses
        return {'income':[{'name':i['name'],'balance':i['credit']} for i in inc],
                'expenses':[{'name':e['name'],'balance':e['debit']} for e in exp],
                'total_income':total_income,'total_expenses':total_expenses,'net_profit':net}

    def get_balance_sheet_filtered(self, start_date=None, end_date=None):
        trial = self.get_trial_balance_filtered(start_date, end_date)
        assets = [t for t in trial if t['name'] in ('الصندوق','الذمم المدينة')]
        liabilities = [t for t in trial if t['name']=='الذمم الدائنة']
        equity = [{'name':'رأس المال','credit':sum(a['debit'] for a in assets)-sum(l['credit'] for l in liabilities)}]
        return {
            'assets':assets,'liabilities':liabilities,'equity':equity,
            'total_assets':sum(a['debit'] for a in assets),
            'total_liabilities':sum(l['credit'] for l in liabilities),
            'total_equity':equity[0]['credit']
        }

db = Database()
