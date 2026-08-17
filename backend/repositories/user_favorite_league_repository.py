"""SQL queries for user favorite league relations."""

from __future__ import annotations

from backend.database import get_db_connection


def fetch_favorite_league_ids(user_id: int) -> list[int]:
    """Return favorite league IDs for a user, sorted ascending."""
    query = """
        SELECT league_id
        FROM user_favorite_leagues
        WHERE user_id = %s
        ORDER BY league_id
    """
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, (user_id,))
            rows = cursor.fetchall()
        finally:
            cursor.close()
    return [int(row["league_id"]) for row in rows]


def add_favorite_league(user_id: int, league_id: int) -> None:
    """Insert a favorite relation; an existing composite key is a no-op."""
    query = """
        INSERT INTO user_favorite_leagues (user_id, league_id)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE user_id = user_id
    """
    _execute_write(query, (user_id, league_id))


def remove_favorite_league(user_id: int, league_id: int) -> None:
    """Delete a favorite relation; missing row is still a success."""
    query = """
        DELETE FROM user_favorite_leagues
        WHERE user_id = %s AND league_id = %s
    """
    _execute_write(query, (user_id, league_id))


def _execute_write(query: str, params: tuple[object, ...]) -> None:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            # mysql-connector bez autocommit — close bez commit cofa zapis
            conn.commit()
        finally:
            cursor.close()
