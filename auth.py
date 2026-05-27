# -*- coding: utf-8 -*-
from database import db, get_current_user_id, get_current_user_role, set_current_user, clear_current_user
from typing import Optional, Dict

def login(username: str, password: str) -> bool:
    return db.login(username, password)

def logout():
    clear_current_user()

def get_current_user() -> Optional[Dict]:
    uid = get_current_user_id()
    if not uid:
        return None
    conn = db.connect()
    cur = conn.cursor()
    cur.execute("SELECT id, username, role, full_name FROM users WHERE id = ?", (uid,))
    row = cur.fetchone()
    return dict(row) if row else None

def is_authenticated() -> bool:
    return get_current_user_id() is not None

def is_admin() -> bool:
    return get_current_user_role() == 'admin'

def register_user(username: str, password: str, full_name: str = '', role: str = 'user') -> bool:
    return db.register_user(username, password, full_name, role)

def delete_user(user_id: str) -> bool:
    return db.delete_user(user_id)

def get_all_users() -> list:
    return db.get_users()

def change_password(user_id: str, old_password: str, new_password: str) -> bool:
    return db.change_password(user_id, old_password, new_password)

def hash_password(password: str) -> str:
    from database import hash_password as db_hash
    return db_hash(password)

def verify_password(password: str, hashed: str) -> bool:
    from database import verify_password as db_verify
    return db_verify(password, hashed)
