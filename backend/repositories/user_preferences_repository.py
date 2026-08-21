"""SQL queries for the 1:1 user_preferences row."""

from __future__ import annotations

from backend.database import get_db_connection

_SELECT_THEME = """
    SELECT theme
    FROM user_preferences
    WHERE user_id = %s
"""

_UPSERT_THEME = """
    INSERT INTO user_preferences (user_id, theme)
    VALUES (%s, %s)
    ON DUPLICATE KEY UPDATE theme = VALUES(theme)
"""


def _theme_document(row: dict[str, object]) -> dict[str, str]:
    return {"theme": str(row["theme"])}


def fetch_preferences(user_id: int) -> dict[str, str] | None:
    """Return the preferences row for a user, or None when missing."""
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(_SELECT_THEME, (user_id,))
            row = cursor.fetchone()
        finally:
            cursor.close()
    if row is None:
        return None
    return _theme_document(row)


def upsert_theme(user_id: int, theme: str) -> dict[str, str]:
    """Insert or update only the theme column; other columns stay intact."""
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(_UPSERT_THEME, (user_id, theme))
            # mysql-connector bez autocommit — close bez commit cofa zapis
            conn.commit()
            cursor.execute(_SELECT_THEME, (user_id,))
            row = cursor.fetchone()
        finally:
            cursor.close()
    if row is None:
        return {"theme": theme}
    return _theme_document(row)
