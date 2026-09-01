"""SQL queries for application users (site accounts)."""

from __future__ import annotations

from typing import Any

from backend.database import get_db_connection

_USER_COLUMNS = (
    "id, uuid, username, password_hash, display_name, is_active, "
    "is_admin, first_login, created_at, updated_at")

# lista admina nigdy nie czyta hash — serwis i API nie mogą go wyciec
_ADMIN_USER_COLUMNS = (
    "id, uuid, username, display_name, is_active, "
    "is_admin, first_login, created_at, updated_at")

_USER_FLAG_COLUMNS = frozenset({"is_active", "is_admin"})


def fetch_user_by_username(username: str) -> dict[str, Any] | None:
    """Return a user row by username, or None when missing."""
    query = f"""
        SELECT {_USER_COLUMNS}
        FROM users
        WHERE username = %s
        LIMIT 1
    """
    return _fetch_one(query, (username,))


def fetch_user_by_uuid(user_uuid: str) -> dict[str, Any] | None:
    """Return a user row by public UUID, or None when missing."""
    query = f"""
        SELECT {_USER_COLUMNS}
        FROM users
        WHERE uuid = %s
        LIMIT 1
    """
    return _fetch_one(query, (user_uuid,))


def fetch_user_by_id(user_id: int) -> dict[str, Any] | None:
    """Return a user row by internal ID (admin/reporting only)."""
    query = f"""
        SELECT {_USER_COLUMNS}
        FROM users
        WHERE id = %s
        LIMIT 1
    """
    return _fetch_one(query, (user_id,))


def fetch_all_users() -> list[dict[str, Any]]:
    """Return all users ordered by username, without password hashes."""
    query = f"""
        SELECT {_ADMIN_USER_COLUMNS}
        FROM users
        ORDER BY username, id
    """
    return _fetch_all(query, ())


def create_user(
        user_uuid: str,
        username: str,
        password_hash: str,
        display_name: str | None,
        is_admin: bool = False,
        is_active: bool = True,
        first_login: bool = True) -> dict[str, Any]:
    """Insert a user row and return it without the password hash."""
    query = """
        INSERT INTO users (
            uuid, username, password_hash, display_name,
            is_admin, is_active, first_login)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    params = (
        user_uuid,
        username,
        password_hash,
        display_name,
        _as_int_flag(is_admin),
        _as_int_flag(is_active),
        _as_int_flag(first_login))
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            # mysql-connector bez autocommit — close bez commit cofa INSERT
            conn.commit()
        finally:
            cursor.close()
    created = _fetch_admin_user_by_uuid(user_uuid)
    if created is None:
        raise RuntimeError("Inserted user could not be read back")
    return created


def set_user_active(
        user_uuid: str, is_active: bool) -> dict[str, Any] | None:
    """Set is_active and return the user without hash, or None if missing."""
    return _update_user_flag(user_uuid, "is_active", is_active)


def set_user_admin(
        user_uuid: str, is_admin: bool) -> dict[str, Any] | None:
    """Set is_admin and return the user without hash, or None if missing."""
    return _update_user_flag(user_uuid, "is_admin", is_admin)


def is_username_taken(username: str, exclude_user_id: int) -> bool:
    """Return True when another user already uses the username."""
    query = """
        SELECT 1
        FROM users
        WHERE username = %s AND id <> %s
        LIMIT 1
    """
    return _fetch_one(query, (username, exclude_user_id)) is not None


def update_user_credentials_after_first_login(
        user_id: int,
        username: str,
        password_hash: str,
        display_name: str) -> None:
    """Set username, display name and password hash, then clear first_login."""
    query = """
        UPDATE users
        SET username = %s,
            password_hash = %s,
            display_name = %s,
            first_login = 0,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s AND first_login = 1
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                query, (username, password_hash, display_name, user_id))
            if cursor.rowcount == 0:
                conn.rollback()
                raise ValueError(
                    "First login already completed or user not found")
            # mysql-connector bez autocommit — close bez commit cofa UPDATE
            conn.commit()
        finally:
            cursor.close()


def _as_int_flag(value: bool) -> int:
    return 1 if value else 0


def _fetch_admin_user_by_uuid(user_uuid: str) -> dict[str, Any] | None:
    query = f"""
        SELECT {_ADMIN_USER_COLUMNS}
        FROM users
        WHERE uuid = %s
        LIMIT 1
    """
    return _fetch_one(query, (user_uuid,))


def _update_user_flag(
        user_uuid: str,
        column: str,
        value: bool) -> dict[str, Any] | None:
    if column not in _USER_FLAG_COLUMNS:
        raise ValueError(f"Unsupported user flag column: {column}")
    query = f"""
        UPDATE users
        SET {column} = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE uuid = %s
    """
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, (_as_int_flag(value), user_uuid))
            # rowcount bez CLIENT_FOUND_ROWS nie odróżnia braku wiersza
            # od no-op UPDATE tej samej flagi — istnienie sprawdza SELECT
            conn.commit()
        finally:
            cursor.close()
    return _fetch_admin_user_by_uuid(user_uuid)


def _fetch_one(query: str, params: tuple[object, ...]) -> dict[str, Any] | None:
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            row = cursor.fetchone()
        finally:
            cursor.close()
    return dict(row) if row else None


def _fetch_all(
        query: str,
        params: tuple[object, ...]) -> list[dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
        finally:
            cursor.close()
    return [dict(row) for row in rows]
