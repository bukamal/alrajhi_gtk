# database/connection.py
import sqlcipher3 as sqlite3
import os
from typing import Optional
from datetime import datetime
import hashlib
import gc

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'alrajhi.db')

def _get_encryption_key() -> bytes:
    """اشتقاق مفتاح التشفير من معرف الجهاز (لضمان فريد لكل جهاز)"""
    from activation import get_or_create_device_id
    device_id = get_or_create_device_id()
    salt = b'sqlcipher_salt_v1'
    return hashlib.pbkdf2_hmac('sha256', device_id.encode(), salt, 100000, dklen=32)

class DatabaseConnection:
    _instance = None
    _conn: Optional[sqlite3.Connection] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_db()
        return cls._instance

    def _init_db(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        # الاتصال بقاعدة البيانات (سيتم إنشاؤها إذا لم تكن موجودة)
        self._conn = sqlite3.connect(DB_PATH, isolation_level=None)
        key = _get_encryption_key()
        # تعيين مفتاح التشفير فوراً بعد فتح الاتصال
        self._conn.execute(f"PRAGMA key = \"x'{key.hex()}'\"")
        # الآن يمكن تنفيذ أوامر PRAGMA الأخرى
        self._conn.execute("PRAGMA cache_size = -2000")
        self._conn.execute("PRAGMA temp_store = MEMORY")
        self._conn.row_factory = sqlite3.Row
        self.init_tables()
        self._add_indexes()

    def get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._init_db()
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def execute(self, sql: str, params: tuple = ()):
        cur = self.get_connection().cursor()
        cur.execute(sql, params)
        return cur

    def executemany(self, sql: str, params_list: list):
        cur = self.get_connection().cursor()
        cur.executemany(sql, params_list)
        return cur

    def executescript(self, script: str):
        cur = self.get_connection().cursor()
        cur.executescript(script)
        return cur

    def commit(self):
        self.get_connection().commit()

    def rollback(self):
        self.get_connection().rollback()

    def begin_transaction(self):
        self.execute("BEGIN TRANSACTION")

    def init_tables(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        # إنشاء الجداول تباعاً
        tables_sql = [
            "CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT DEFAULT 'user', full_name TEXT, created_at TEXT, last_login TEXT, cash_balance TEXT DEFAULT '0');",
            "CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, name TEXT NOT NULL, phone TEXT, address TEXT, balance TEXT DEFAULT '0', FOREIGN KEY (user_id) REFERENCES users(id), UNIQUE(user_id, name));",
            "CREATE TABLE IF NOT EXISTS suppliers (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, name TEXT NOT NULL, phone TEXT, address TEXT, balance TEXT DEFAULT '0', FOREIGN KEY (user_id) REFERENCES users(id), UNIQUE(user_id, name));",
            "CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, name TEXT NOT NULL, FOREIGN KEY (user_id) REFERENCES users(id), UNIQUE(user_id, name));",
            "CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, name TEXT NOT NULL, category_id INTEGER, item_type TEXT, purchase_price TEXT DEFAULT '0', selling_price TEXT DEFAULT '0', quantity TEXT DEFAULT '0', unit TEXT, average_cost TEXT DEFAULT '0', purchase_qty TEXT DEFAULT '0', sale_qty TEXT DEFAULT '0', barcode TEXT, FOREIGN KEY (user_id) REFERENCES users(id), UNIQUE(user_id, name));",
            "CREATE TABLE IF NOT EXISTS item_units (id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER, unit_name TEXT NOT NULL, conversion_factor TEXT DEFAULT '1', FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE);",
            "CREATE TABLE IF NOT EXISTS invoices (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, type TEXT, customer_id INTEGER, supplier_id INTEGER, date TEXT, reference TEXT, notes TEXT, total TEXT DEFAULT '0', paid TEXT DEFAULT '0', status TEXT, deleted_at TEXT, FOREIGN KEY (user_id) REFERENCES users(id), FOREIGN KEY (customer_id) REFERENCES customers(id), FOREIGN KEY (supplier_id) REFERENCES suppliers(id));",
            "CREATE TABLE IF NOT EXISTS invoice_lines (id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_id INTEGER, item_id INTEGER, description TEXT, quantity TEXT DEFAULT '0', unit_price TEXT DEFAULT '0', total TEXT DEFAULT '0', unit TEXT, quantity_in_base TEXT DEFAULT '0', unit_cost TEXT DEFAULT '0', cost_amount TEXT DEFAULT '0', FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE, FOREIGN KEY (item_id) REFERENCES items(id));",
            "CREATE TABLE IF NOT EXISTS vouchers (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, type TEXT, date TEXT, amount TEXT DEFAULT '0', description TEXT, reference TEXT, customer_id INTEGER, supplier_id INTEGER, invoice_id INTEGER, FOREIGN KEY (user_id) REFERENCES users(id), FOREIGN KEY (customer_id) REFERENCES customers(id), FOREIGN KEY (supplier_id) REFERENCES suppliers(id), FOREIGN KEY (invoice_id) REFERENCES invoices(id));",
            "CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, amount TEXT DEFAULT '0', expense_date TEXT, description TEXT, FOREIGN KEY (user_id) REFERENCES users(id));",
            "CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, name TEXT, type TEXT, balance TEXT DEFAULT '0', FOREIGN KEY (user_id) REFERENCES users(id));",
            "CREATE TABLE IF NOT EXISTS inventory_movements (id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER NOT NULL, user_id TEXT NOT NULL, movement_type TEXT NOT NULL, quantity TEXT NOT NULL, unit_cost TEXT, reference_id INTEGER, movement_date TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (item_id) REFERENCES items(id), FOREIGN KEY (user_id) REFERENCES users(id));",
            "CREATE TABLE IF NOT EXISTS exchange_rates (currency_code TEXT PRIMARY KEY, rate_to_usd TEXT NOT NULL, updated_at TEXT);"
        ]

        for sql in tables_sql:
            cursor.execute(sql)
            conn.commit()
            gc.collect()

        # إضافة المستخدم admin إذا لم يكن موجوداً
        cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            from database.utils import hash_password
            admin_hash = hash_password('admin123')
            now = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO users (id, username, password_hash, role, full_name, created_at, cash_balance)
                VALUES (?,?,?,?,?,?,?)
            """, ('admin', 'admin', admin_hash, 'admin', 'المدير العام', now, '0'))
            conn.commit()

        # الحسابات الافتراضية
        default_accounts = [
            ('local_user', 'الصندوق', 'asset', '0'),
            ('local_user', 'المبيعات', 'income', '0'),
            ('local_user', 'المشتريات', 'expense', '0'),
            ('local_user', 'المخزون', 'asset', '0'),
            ('local_user', 'مصاريف عامة', 'expense', '0'),
            ('local_user', 'رأس المال', 'equity', '0')
        ]
        for acc in default_accounts:
            cursor.execute("INSERT OR IGNORE INTO accounts (user_id, name, type, balance) VALUES (?,?,?,?)", acc)
        conn.commit()

        # أسعار الصرف الافتراضية
        now = datetime.now().isoformat()
        default_rates = [
            ('USD', '1.0'), ('EUR', '1.08'), ('GBP', '1.25'),
            ('SAR', '0.266'), ('AED', '0.272'), ('SYP', '0.0000729927')
        ]
        for code, rate in default_rates:
            cursor.execute("INSERT OR IGNORE INTO exchange_rates (currency_code, rate_to_usd, updated_at) VALUES (?,?,?)", (code, rate, now))
        conn.commit()

    def _add_indexes(self):
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_customers_user_id ON customers(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name);",
            "CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone);",
            "CREATE INDEX IF NOT EXISTS idx_suppliers_user_id ON suppliers(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_suppliers_name ON suppliers(name);",
            "CREATE INDEX IF NOT EXISTS idx_suppliers_phone ON suppliers(phone);",
            "CREATE INDEX IF NOT EXISTS idx_categories_user_id ON categories(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_categories_name ON categories(name);",
            "CREATE INDEX IF NOT EXISTS idx_items_user_id ON items(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_items_name ON items(name);",
            "CREATE INDEX IF NOT EXISTS idx_items_barcode ON items(barcode) WHERE barcode IS NOT NULL;",
            "CREATE INDEX IF NOT EXISTS idx_invoices_user_id ON invoices(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_invoices_customer_id ON invoices(customer_id);",
            "CREATE INDEX IF NOT EXISTS idx_invoices_supplier_id ON invoices(supplier_id);",
            "CREATE INDEX IF NOT EXISTS idx_invoices_date ON invoices(date);",
            "CREATE INDEX IF NOT EXISTS idx_invoices_type ON invoices(type);",
            "CREATE INDEX IF NOT EXISTS idx_invoices_reference ON invoices(reference);",
            "CREATE INDEX IF NOT EXISTS idx_invoice_lines_invoice_id ON invoice_lines(invoice_id);",
            "CREATE INDEX IF NOT EXISTS idx_invoice_lines_item_id ON invoice_lines(item_id);",
            "CREATE INDEX IF NOT EXISTS idx_vouchers_user_id ON vouchers(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_vouchers_date ON vouchers(date);",
            "CREATE INDEX IF NOT EXISTS idx_vouchers_type ON vouchers(type);",
            "CREATE INDEX IF NOT EXISTS idx_expenses_user_id ON expenses(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_expenses_expense_date ON expenses(expense_date);",
            "CREATE INDEX IF NOT EXISTS idx_accounts_user_id ON accounts(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_inventory_movements_item_id ON inventory_movements(item_id);",
            "CREATE INDEX IF NOT EXISTS idx_inventory_movements_user_id ON inventory_movements(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_inventory_movements_movement_date ON inventory_movements(movement_date);",
            "CREATE INDEX IF NOT EXISTS idx_inventory_movements_movement_type ON inventory_movements(movement_type);",
            "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);",
            "CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);",
            "CREATE INDEX IF NOT EXISTS idx_exchange_rates_currency_code ON exchange_rates(currency_code);"
        ]
        for sql in indexes:
            try:
                self.execute(sql)
            except Exception as e:
                print(f"خطأ في إنشاء فهرس: {e}")
        self.commit()

    def check_default_admin_password(self) -> bool:
        try:
            from database.utils import verify_password
            cur = self.execute("SELECT password_hash FROM users WHERE username = 'admin'")
            row = cur.fetchone()
            if row and verify_password('admin123', row['password_hash']):
                return True
            return False
        except Exception:
            return False

    def change_admin_password(self, new_password: str) -> bool:
        from database.utils import hash_password
        new_hash = hash_password(new_password)
        self.execute("UPDATE users SET password_hash = ? WHERE username = 'admin'", (new_hash,))
        self.commit()
        return True

def get_db_connection():
    return DatabaseConnection().get_connection()

def init_db():
    DatabaseConnection().init_tables()
