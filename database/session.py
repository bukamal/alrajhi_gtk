# database/session.py
# -*- coding: utf-8 -*-
from typing import Optional

class UserSession:
    _current_user_id: Optional[str] = None
    _current_user_role: Optional[str] = None
    _force_password_change: bool = False

    @classmethod
    def set_current_user(cls, user_id: str, role: str = 'user'):
        cls._current_user_id = user_id
        cls._current_user_role = role
        cls._force_password_change = False

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
        cls._force_password_change = False

    @classmethod
    def set_force_password_change(cls, value: bool):
        cls._force_password_change = value

    @classmethod
    def get_force_password_change(cls) -> bool:
        return cls._force_password_change

def get_current_user_id() -> Optional[str]:
    return UserSession.get_current_user_id()

def get_current_user_role() -> Optional[str]:
    return UserSession.get_current_user_role()
