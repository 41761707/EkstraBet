"""SQL queries for sport dictionary rows used by admin forms."""

from __future__ import annotations

from typing import Any

from backend.database import get_db_connection


def fetch_all_sports() -> list[dict[str, Any]]:
    """Return sports ordered by name for dropdowns."""
    query = """
        SELECT id, name
        FROM sports
        ORDER BY name, id
    """
    return _fetch_all(query)


def _fetch_all(query: str) -> list[dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query)
            rows = cursor.fetchall()
        finally:
            cursor.close()
    return [dict(row) for row in rows]
