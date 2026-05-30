# database/dao/reporting_dao.py
# -*- coding: utf-8 -*-

from decimal import Decimal
import json
from database.dao.base_dao import BaseDAO
from database.session import UserSession
from database.utils import storage_to_decimal, decimal_to_storage

class ReportingDAO(BaseDAO):
    def _safe_sum(self, sql, params):
        cur = self._execute(sql, params)
        val = cur.fetchone()[0]
        return storage_to_decimal(val or '0')

    def get_summary(self):
        uid = UserSession.get_current_user_id()
        if not uid:
            return {}
        sales = self._safe_sum("SELECT CAST(SUM(CAST(total AS TEXT)) AS TEXT) FROM invoices WHERE type='sale' AND user_id=? AND deleted_at IS NULL", (uid,))
        purchases = self._safe_sum("SELECT CAST(SUM(CAST(total AS TEXT)) AS TEXT) FROM invoices WHERE type='purchase' AND user_id=? AND deleted_at IS NULL", (uid,))
        expenses = self._safe_sum("SELECT CAST(SUM(CAST(amount AS TEXT)) AS TEXT) FROM expenses WHERE user_id=?", (uid,))
        receivables = self._safe_sum("SELECT CAST(SUM(CAST(balance AS TEXT)) AS TEXT) FROM customers WHERE user_id=?", (uid,))
        payables = self._safe_sum("SELECT CAST(SUM(CAST(balance AS TEXT)) AS TEXT) FROM suppliers WHERE user_id=?", (uid,))
        cash = self._safe_sum("SELECT CAST(cash_balance AS TEXT) FROM users WHERE id=?", (uid,))
        return {
            'net_profit': sales - purchases - expenses,
            'cash_balance': cash,
            'receivables': receivables,
            'payables': payables,
            'total_sales': sales,
            'total_purchases': purchases,
            'total_expenses': expenses
        }

    def get_trial_balance(self):
        uid = UserSession.get_current_user_id()
        sales = self._safe_sum("SELECT CAST(SUM(CAST(total AS TEXT)) AS TEXT) FROM invoices WHERE type='sale' AND user_id=? AND deleted_at IS NULL", (uid,))
        purchases = self._safe_sum("SELECT CAST(SUM(CAST(total AS TEXT)) AS TEXT) FROM invoices WHERE type='purchase' AND user_id=? AND deleted_at IS NULL", (uid,))
        expenses = self._safe_sum("SELECT CAST(SUM(CAST(amount AS TEXT)) AS TEXT) FROM expenses WHERE user_id=?", (uid,))
        cash = self._safe_sum("SELECT CAST(cash_balance AS TEXT) FROM users WHERE id=?", (uid,))
        receivables = self._safe_sum("SELECT CAST(SUM(CAST(balance AS TEXT)) AS TEXT) FROM customers WHERE user_id=?", (uid,))
        payables = self._safe_sum("SELECT CAST(SUM(CAST(balance AS TEXT)) AS TEXT) FROM suppliers WHERE user_id=?", (uid,))
        return [
            {'name':'الصندوق','debit':cash if cash>0 else 0,'credit':-cash if cash<0 else 0},
            {'name':'الذمم المدينة','debit':receivables,'credit':0},
            {'name':'الذمم الدائنة','debit':0,'credit':payables},
            {'name':'المبيعات','debit':0,'credit':sales},
            {'name':'المشتريات','debit':purchases,'credit':0},
            {'name':'المصاريف','debit':expenses,'credit':0}
        ]

    def get_trial_balance_filtered(self, start_date=None, end_date=None):
        uid = UserSession.get_current_user_id()
        if start_date and end_date:
            sales = self._safe_sum("SELECT CAST(SUM(CAST(total AS TEXT)) AS TEXT) FROM invoices WHERE type='sale' AND user_id=? AND deleted_at IS NULL AND (date BETWEEN ? AND ?)", (uid, start_date, end_date))
            purchases = self._safe_sum("SELECT CAST(SUM(CAST(total AS TEXT)) AS TEXT) FROM invoices WHERE type='purchase' AND user_id=? AND deleted_at IS NULL AND (date BETWEEN ? AND ?)", (uid, start_date, end_date))
            expenses = self._safe_sum("SELECT CAST(SUM(CAST(amount AS TEXT)) AS TEXT) FROM expenses WHERE user_id=? AND (expense_date BETWEEN ? AND ?)", (uid, start_date, end_date))
        else:
            sales = purchases = expenses = Decimal('0')
        cash = self._safe_sum("SELECT CAST(cash_balance AS TEXT) FROM users WHERE id=?", (uid,))
        receivables = self._safe_sum("SELECT CAST(SUM(CAST(balance AS TEXT)) AS TEXT) FROM customers WHERE user_id=?", (uid,))
        payables = self._safe_sum("SELECT CAST(SUM(CAST(balance AS TEXT)) AS TEXT) FROM suppliers WHERE user_id=?", (uid,))
        return [
            {'name':'الصندوق','debit':cash if cash>0 else 0,'credit':-cash if cash<0 else 0},
            {'name':'الذمم المدينة','debit':receivables,'credit':0},
            {'name':'الذمم الدائنة','debit':0,'credit':payables},
            {'name':'المبيعات','debit':0,'credit':sales},
            {'name':'المشتريات','debit':purchases,'credit':0},
            {'name':'المصاريف','debit':expenses,'credit':0}
        ]

    def get_income_statement(self):
        trial = self.get_trial_balance()
        inc = [t for t in trial if t['name']=='المبيعات']
        exp = [t for t in trial if t['name'] in ('المشتريات','المصاريف')]
        total_income = sum(i['credit'] for i in inc)
        total_expenses = sum(e['debit'] for e in exp)
        net = total_income - total_expenses
        return {'income':[{'name':i['name'],'balance':i['credit']} for i in inc],
                'expenses':[{'name':e['name'],'balance':e['debit']} for e in exp],
                'total_income':total_income,'total_expenses':total_expenses,'net_profit':net}

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

    def get_balance_sheet(self):
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

    def get_customer_statement(self, cust_id: int):
        uid = UserSession.get_current_user_id()
        rows = self._fetch_all("""
            SELECT date, reference, 
                   CAST(total AS TEXT) as amount, 
                   'فاتورة' as description, 
                   CAST(total AS TEXT) as debit, 
                   '0' as credit
            FROM invoices WHERE customer_id=? AND type='sale' AND user_id=? AND deleted_at IS NULL
            UNION ALL
            SELECT date, reference, 
                   CAST(amount AS TEXT), 
                   'سند قبض', 
                   '0', 
                   CAST(amount AS TEXT)
            FROM vouchers WHERE customer_id=? AND type='receipt' AND user_id=?
            ORDER BY date
        """, (cust_id, uid, cust_id, uid))
        result = []
        balance = Decimal('0')
        for row in rows:
            d = dict(row)
            d['debit'] = storage_to_decimal(d.get('debit', '0'))
            d['credit'] = storage_to_decimal(d.get('credit', '0'))
            balance += d['debit'] - d['credit']
            d['balance'] = balance
            result.append(d)
        return result

    def get_supplier_statement(self, supp_id: int):
        uid = UserSession.get_current_user_id()
        rows = self._fetch_all("""
            SELECT date, reference, 
                   CAST(total AS TEXT) as amount, 
                   'فاتورة' as description, 
                   '0' as debit, 
                   CAST(total AS TEXT) as credit
            FROM invoices WHERE supplier_id=? AND type='purchase' AND user_id=? AND deleted_at IS NULL
            UNION ALL
            SELECT date, reference, 
                   CAST(amount AS TEXT), 
                   'سند دفع', 
                   CAST(amount AS TEXT), 
                   '0'
            FROM vouchers WHERE supplier_id=? AND type='payment' AND user_id=?
            ORDER BY date
        """, (supp_id, uid, supp_id, uid))
        result = []
        balance = Decimal('0')
        for row in rows:
            d = dict(row)
            d['debit'] = storage_to_decimal(d.get('debit', '0'))
            d['credit'] = storage_to_decimal(d.get('credit', '0'))
            balance += d['credit'] - d['debit']
            d['balance'] = balance
            result.append(d)
        return result

    def get_monthly_sales(self):
        uid = UserSession.get_current_user_id()
        rows = self._fetch_all("""
            SELECT strftime('%Y-%m', date) as month, 
                   CAST(SUM(CAST(total AS TEXT)) AS TEXT) as total
            FROM invoices
            WHERE type='sale' AND user_id=? AND deleted_at IS NULL
            GROUP BY month
            ORDER BY month
        """, (uid,))
        return [{'month':row['month'], 'total':storage_to_decimal(row['total'] or '0')} for row in rows]

    def get_monthly_profit(self):
        uid = UserSession.get_current_user_id()
        rows = self._fetch_all("""
            SELECT strftime('%Y-%m', i.date) as month,
                   CAST(SUM(CASE WHEN i.type='sale' THEN CAST(i.total AS TEXT) ELSE '0' END) AS TEXT) -
                   CAST(SUM(CASE WHEN i.type='purchase' THEN CAST(i.total AS TEXT) ELSE '0' END) AS TEXT) -
                   COALESCE((
                       SELECT CAST(SUM(CAST(amount AS TEXT)) AS TEXT) 
                       FROM expenses 
                       WHERE user_id=? AND strftime('%Y-%m', expense_date)=strftime('%Y-%m', i.date)
                   ), '0') as profit
            FROM invoices i
            WHERE i.user_id=? AND i.deleted_at IS NULL
            GROUP BY month
            ORDER BY month
        """, (uid, uid))
        return [{'month':row['month'], 'profit':storage_to_decimal(row['profit'] or '0')} for row in rows]

    def export_full_database(self) -> bytes:
        tables = ['customers','suppliers','categories','items','item_units','invoices','invoice_lines','vouchers','expenses','users','inventory_movements','exchange_rates']
        data = {}
        uid = UserSession.get_current_user_id()
        for tbl in tables:
            if tbl == 'item_units':
                rows = self._fetch_all("""
                    SELECT iu.* FROM item_units iu
                    JOIN items i ON iu.item_id = i.id
                    WHERE i.user_id = ?
                """, (uid,))
            elif tbl in ('inventory_movements', 'exchange_rates'):
                rows = self._fetch_all(f"SELECT * FROM {tbl}")
            else:
                rows = self._fetch_all(f"SELECT * FROM {tbl} WHERE user_id=?", (uid,))
            data[tbl] = [dict(row) for row in rows]
        return json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')

    def import_full_database(self, json_bytes: bytes):
        data = json.loads(json_bytes.decode('utf-8'))
        self.begin_transaction()
        try:
            uid = UserSession.get_current_user_id()
            for tbl, rows in data.items():
                if tbl == 'item_units':
                    self._execute("DELETE FROM item_units WHERE item_id IN (SELECT id FROM items WHERE user_id=?)", (uid,))
                elif tbl in ('inventory_movements', 'exchange_rates'):
                    self._execute(f"DELETE FROM {tbl}")
                else:
                    self._execute(f"DELETE FROM {tbl} WHERE user_id=?", (uid,))
                for row in rows:
                    if 'user_id' in row and tbl not in ('item_units','inventory_movements','exchange_rates'):
                        row['user_id'] = uid
                    cols = ', '.join(row.keys())
                    ph = ', '.join(['?' for _ in row])
                    self._execute(f"INSERT INTO {tbl} ({cols}) VALUES ({ph})", list(row.values()))
            self._commit()
        except Exception as e:
            self._rollback()
            raise e
