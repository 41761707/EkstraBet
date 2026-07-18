"""SQL queries for application users (site accounts)."""

from __future__ import annotations

from typing import Any

from backend.database import get_db_connection

_USER_COLUMNS = (
    "id, uuid, username, password_hash, display_name, is_active, "
    "created_at, updated_at"
)


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


def _fetch_one(query: str, params: tuple[object, ...]) -> dict[str, Any] | None:
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params)
        row = cursor.fetchone()
        cursor.close()
    return dict(row) if row else None
