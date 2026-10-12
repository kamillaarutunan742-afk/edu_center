"""Сервис аутентификации: вход в систему и управление пользователями.

Пароли хранятся в виде SHA-256 хэша с солью — в открытом виде пароли
не хранят никогда.
"""

import hashlib
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import User


def hash_password(password: str, salt: str | None = None) -> str:
    """Хэширует пароль с солью.

    Args:
        password: пароль в открытом виде.
        salt: соль; если не задана, генерируется случайно.

    Returns:
        Строка вида "salt:hash".
    """
    salt = salt or secrets.token_hex(8)
    digest = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{digest}"


def verify_password(password: str, stored: str) -> bool:
    """Проверяет пароль против сохранённого хэша.

    Args:
        password: введённый пользователем пароль.
        stored: сохранённая строка "salt:hash".

    Returns:
        True, если пароль верный.
    """
    salt, _ = stored.split(":", 1)
    return hash_password(password, salt) == stored


def authenticate(session: Session, login: str, password: str) -> User | None:
    """Выполняет вход пользователя.

    Args:
        session: сессия БД.
        login: логин пользователя.
        password: введённый пароль.

    Returns:
        Объект User при успешном входе, иначе None.
    """
    user = session.scalar(select(User).where(User.login == login))
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user
