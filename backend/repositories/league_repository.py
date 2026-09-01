"""SQL queries for league navigation data."""

from __future__ import annotations

from typing import Any

import pandas as pd

from backend.database import get_db_connection

_ADMIN_LEAGUE_SELECT = """
    SELECT
        l.id,
        l.name,
        l.country AS country_id,
        c.name AS country_name,
        c.emoji AS country_emoji,
        l.sport_id,
        s.name AS sport_name,
        l.active,
        l.last_update,
        l.current_season_id,
        l.tier,
        l.has_player_stats
    FROM leagues l
    LEFT JOIN countries c ON l.country = c.id
    LEFT JOIN sports s ON l.sport_id = s.id
"""


def fetch_leagues(
    active: bool | None = True,
    sport_id: int | None = None) -> pd.DataFrame:
    """Return leagues joined with country and sport metadata."""
    conditions = ["1 = 1"]
    params: list[object] = []

    if active is not None:
        conditions.append("l.active = %s")
        params.append(1 if active else 0)

    if sport_id is not None:
        conditions.append("l.sport_id = %s")
        params.append(sport_id)

    where_clause = " AND ".join(conditions)
    query = f"""
        SELECT
            l.id,
            l.name,
            l.country AS country_id,
            c.name AS country_name,
            c.emoji AS country_emoji,
            l.sport_id,
            s.name AS sport_name,
            l.active,
            l.last_update,
            l.current_season_id,
            l.tier,
            l.has_player_stats
        FROM leagues l
        LEFT JOIN countries c ON l.country = c.id
        LEFT JOIN sports s ON l.sport_id = s.id
        WHERE {where_clause}
        ORDER BY l.country, l.name
    """
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=tuple(params) or None)


def fetch_league_by_id(league_id: int) -> pd.DataFrame:
    """Return a single league row or an empty DataFrame."""
    query = """
        SELECT
            l.id,
            l.name,
            l.country AS country_id,
            c.name AS country_name,
            c.emoji AS country_emoji,
            l.sport_id,
            s.name AS sport_name,
            l.active,
            l.last_update,
            l.current_season_id,
            l.tier,
            l.has_player_stats
        FROM leagues l
        LEFT JOIN countries c ON l.country = c.id
        LEFT JOIN sports s ON l.sport_id = s.id
        WHERE l.id = %s
    """
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=(league_id,))


def league_exists(league_id: int) -> bool:
    """Return True when the league id exists in the database."""
    query = "SELECT 1 FROM leagues WHERE id = %s LIMIT 1"
    with get_db_connection() as conn:
        frame = pd.read_sql(query, conn, params=(league_id,))
    return not frame.empty


def fetch_league_match_count(league_id: int) -> int:
    """Return total number of matches stored for the league."""
    query = "SELECT COUNT(*) AS total FROM matches WHERE league = %s"
    with get_db_connection() as conn:
        frame = pd.read_sql(query, conn, params=(league_id,))
    if frame.empty:
        return 0
    return int(frame.iloc[0]["total"] or 0)


def fetch_seasons_for_league(league_id: int) -> pd.DataFrame:
    """Return distinct seasons that contain matches for the league."""
    query = """
        SELECT DISTINCT
            m.season AS season_id,
            s.years,
            COUNT(m.id) AS match_count
        FROM matches m
        JOIN seasons s ON m.season = s.id
        WHERE m.league = %s
        GROUP BY m.season, s.years
        ORDER BY s.years DESC
    """
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=(league_id,))


def fetch_rounds_for_league_season(
    league_id: int,
    season_id: int) -> pd.DataFrame:
    """Return rounds with the latest game date per round."""
    query = """
        SELECT
            round AS round_number,
            CAST(MAX(game_date) AS DATE) AS game_date
        FROM matches
        WHERE league = %s AND season = %s
        GROUP BY round
        ORDER BY game_date DESC
    """
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=(league_id, season_id))


def fetch_special_round_names() -> dict[int, str]:
    """Return special round id to display name mapping."""
    query = "SELECT id, name FROM special_rounds"
    with get_db_connection() as conn:
        frame = pd.read_sql(query, conn)
    if frame.empty:
        return {}
    return {
        int(row["id"]): str(row["name"])
        for _, row in frame.iterrows()
    }


def fetch_all_leagues() -> list[dict[str, Any]]:
    """Return all leagues including inactive ones, by country then name."""
    query = f"""
        {_ADMIN_LEAGUE_SELECT}
        ORDER BY l.country, l.name
    """
    return _fetch_all(query, ())


def create_league(
        name: str,
        country_id: int,
        sport_id: int,
        current_season_id: int | None = None,
        tier: int | None = None,
        has_player_stats: bool = False,
        active: bool = True) -> dict[str, Any]:
    """Insert a league and return the joined admin row."""
    query = """
        INSERT INTO leagues (
            name, country, sport_id, current_season_id,
            tier, has_player_stats, active)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    params = (
        name,
        country_id,
        sport_id,
        current_season_id,
        tier,
        _as_int_flag(has_player_stats),
        _as_int_flag(active))
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            league_id = int(cursor.lastrowid)
            # mysql-connector bez autocommit — close bez commit cofa INSERT
            conn.commit()
        finally:
            cursor.close()
    created = _fetch_admin_league_by_id(league_id)
    if created is None:
        raise RuntimeError("Inserted league could not be read back")
    return created


def set_league_active(
        league_id: int, active: bool) -> dict[str, Any] | None:
    """Set active and return the league, or None when the id is missing."""
    query = """
        UPDATE leagues
        SET active = %s
        WHERE id = %s
    """
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, (_as_int_flag(active), league_id))
            # rowcount bez CLIENT_FOUND_ROWS nie odróżnia braku wiersza
            # od no-op UPDATE tej samej flagi — istnienie sprawdza SELECT
            conn.commit()
        finally:
            cursor.close()
    return _fetch_admin_league_by_id(league_id)


def _as_int_flag(value: bool) -> int:
    return 1 if value else 0


def _fetch_admin_league_by_id(league_id: int) -> dict[str, Any] | None:
    query = f"""
        {_ADMIN_LEAGUE_SELECT}
        WHERE l.id = %s
        LIMIT 1
    """
    rows = _fetch_all(query, (league_id,))
    if not rows:
        return None
    return rows[0]


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
