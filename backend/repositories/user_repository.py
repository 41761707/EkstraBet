"""SQL queries for application users (site accounts)."""

from __future__ import annotations

from typing import Any

from backend.database import get_db_connection

_USER_COLUMNS = (
    "id, uuid, username, password_hash, display_name, is_active, "
    "first_login, created_at, updated_at")


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


def _fetch_one(query: str, params: tuple[object, ...]) -> dict[str, Any] | None:
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params)
        row = cursor.fetchone()
        cursor.close()
    return dict(row) if row else None
