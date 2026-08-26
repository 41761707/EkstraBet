"""SQL queries for the 1:1 user_preferences row."""

from __future__ import annotations

from backend.database import get_db_connection

_DEFAULT_THEME = "system"
_DEFAULT_TEAM_NAME_DISPLAY = "full"

_SELECT_PREFERENCES = """
    SELECT theme, team_name_display
    FROM user_preferences
    WHERE user_id = %s
"""

_UPSERT_PREFERENCES = """
    INSERT INTO user_preferences (user_id, theme, team_name_display)
    VALUES (%s, COALESCE(%s, 'system'), COALESCE(%s, 'full'))
    ON DUPLICATE KEY UPDATE
        theme = COALESCE(%s, theme),
        team_name_display = COALESCE(%s, team_name_display)
"""


def _preferences_document(row: dict[str, object]) -> dict[str, str]:
    return {
        "theme": str(row["theme"]),
        "team_name_display": str(row["team_name_display"])
    }


def fetch_preferences(user_id: int) -> dict[str, str] | None:
    """Return the preferences row for a user, or None when missing."""
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(_SELECT_PREFERENCES, (user_id,))
            row = cursor.fetchone()
        finally:
            cursor.close()
    if row is None:
        return None
    return _preferences_document(row)


def upsert_preferences(
        user_id: int,
        theme: str | None = None,
        team_name_display: str | None = None) -> dict[str, str]:
    """Insert or patch columns; omitted ones keep defaults or prior values."""
    params = (user_id, theme, team_name_display, theme, team_name_display)
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(_UPSERT_PREFERENCES, params)
            # mysql-connector bez autocommit — close bez commit cofa zapis
            conn.commit()
            cursor.execute(_SELECT_PREFERENCES, (user_id,))
            row = cursor.fetchone()
        finally:
            cursor.close()
    if row is None:
        return _preferences_document({
            "theme": theme or _DEFAULT_THEME,
            "team_name_display": (
                team_name_display or _DEFAULT_TEAM_NAME_DISPLAY)
        })
    return _preferences_document(row)
