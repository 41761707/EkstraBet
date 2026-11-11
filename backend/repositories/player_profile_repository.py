"""SQL reads for the shared player profile slice."""

from __future__ import annotations

from typing import Any

import pandas as pd

from backend.database import get_db_connection
from backend.sports.player_profile import ALLOWED_PROFILE_STATS_TABLES


_PLAYER_NAME_LIKE_SQL = """
LOWER(
    CONVERT(
        CONCAT_WS(
            ' ',
            p.first_name,
            p.last_name,
            p.common_name
        )
        USING utf8mb4
    )
) COLLATE utf8mb4_unicode_ci LIKE %s
""".strip()

# Koperta nazywa bramki home_goals / away_goals.
# W matches kolumny to home_team_goals / away_team_goals.
_SLICE_HEADER_SQL = """\
    m.id AS match_id,
    DATE_FORMAT(CAST(m.game_date AS DATE), '%Y-%m-%d') AS game_date,
    s.id AS season_id,
    s.years AS season_years,
    own.id AS own_team_id,
    own.name AS own_team_name,
    CASE
        WHEN m.home_team = stat.team_id THEN away.id
        ELSE home.id
    END AS opponent_team_id,
    CASE
        WHEN m.home_team = stat.team_id THEN away.name
        ELSE home.name
    END AS opponent_name,
    CASE
        WHEN m.home_team = stat.team_id THEN away.shortcut
        ELSE home.shortcut
    END AS opponent_shortcut,
    CASE
        WHEN m.home_team = stat.team_id THEN 'home'
        ELSE 'away'
    END AS venue,
    m.home_team_goals AS home_goals,
    m.away_team_goals AS away_goals,
    m.result AS result"""

_OPPONENT_SQL = (
    "((m.home_team = stat.team_id AND m.away_team = %s)"
    " OR (m.away_team = stat.team_id AND m.home_team = %s))")


def fetch_player(player_id: int) -> dict[str, Any] | None:
    """Return one player without a sport filter, or None when missing."""
    query = """
        SELECT
            p.id AS player_id,
            CONCAT_WS(' ', p.first_name, p.last_name) AS player_name,
            p.position AS position,
            p.sports_id AS sport_id
        FROM players p
        WHERE p.id = %s
        LIMIT 1
    """
    row = _fetch_one(query, (player_id,))
    if row is None:
        return None
    return _player_record(row)


def fetch_player_search(
        sport_id: int,
        term: str,
        limit: int) -> list[dict[str, Any]]:
    """Return players of one sport whose name matches the term."""
    query = f"""
        SELECT
            p.id AS player_id,
            CONCAT_WS(' ', p.first_name, p.last_name) AS player_name,
            p.position AS position,
            t.name AS current_team_name
        FROM players p
        LEFT JOIN teams t ON t.id = p.current_club
        WHERE p.sports_id = %s
            AND {_PLAYER_NAME_LIKE_SQL}
        ORDER BY p.last_name, p.first_name
        LIMIT %s
    """
    pattern = f"%{term.strip().lower()}%"
    rows = _fetch_all(query, (sport_id, pattern, limit))
    return [_search_hit(row) for row in rows]


def team_exists(team_id: int, sport_id: int) -> bool:
    """Return True when the team belongs to the given sport."""
    query = """
        SELECT 1 AS found
        FROM teams
        WHERE id = %s
            AND sport_id = %s
        LIMIT 1
    """
    return _fetch_one(query, (team_id, sport_id)) is not None


def season_exists(season_id: int, sport_id: int) -> bool:
    """Return True when the season has a match of this sport."""
    query = """
        SELECT 1 AS found
        FROM matches
        WHERE season = %s
            AND sport_id = %s
        LIMIT 1
    """
    return _fetch_one(query, (season_id, sport_id)) is not None


def fetch_profile_slice(
        stats_table: str,
        stat_select_sql: str,
        player_id: int,
        sport_id: int,
        season_id: int | None,
        opponent_team_id: int | None,
        own_team_id: int | None,
        teammate_id: int | None,
        limit: int) -> pd.DataFrame:
    """Return one stats row per match from a whitelisted table.

    ``stat_select_sql`` is a column fragment from the sport source.
    It is not taken from the request.
    """
    table = _require_stats_table(stats_table)
    conditions, params = _slice_conditions(
        table,
        player_id,
        sport_id,
        season_id,
        opponent_team_id,
        own_team_id,
        teammate_id)
    params.append(limit)
    query = _slice_query(table, stat_select_sql, conditions)
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=tuple(params))


def _require_stats_table(stats_table: str) -> str:
    """Reject a stats table that is not on the profile whitelist."""
    if stats_table not in ALLOWED_PROFILE_STATS_TABLES:
        raise ValueError("Unsupported player profile stats table")
    return stats_table


def _slice_conditions(
        stats_table: str,
        player_id: int,
        sport_id: int,
        season_id: int | None,
        opponent_team_id: int | None,
        own_team_id: int | None,
        teammate_id: int | None) -> tuple[list[str], list[object]]:
    """Build the slice WHERE clause. The table name is already allowed."""
    conditions = [
        "stat.player_id = %s",
        "m.sport_id = %s"]
    params: list[object] = [player_id, sport_id]
    if season_id is not None:
        conditions.append("m.season = %s")
        params.append(season_id)
    if opponent_team_id is not None:
        conditions.append(_OPPONENT_SQL)
        params.extend([opponent_team_id, opponent_team_id])
    if own_team_id is not None:
        conditions.append("stat.team_id = %s")
        params.append(own_team_id)
    if teammate_id is not None:
        conditions.append(_teammate_exists_sql(stats_table))
        params.append(teammate_id)
    return conditions, params


def _teammate_exists_sql(stats_table: str) -> str:
    """Correlate a teammate row in the same whitelisted stats table."""
    return (
        "EXISTS ("
        f"SELECT 1 FROM {stats_table} mate "
        "WHERE mate.match_id = stat.match_id "
        "AND mate.team_id = stat.team_id "
        "AND mate.player_id = %s)")


def _slice_query(
        stats_table: str,
        stat_select_sql: str,
        conditions: list[str]) -> str:
    """Assemble the slice SELECT. The table name is already whitelisted."""
    # Fragment kolumn pochodzi ze stałej źródła, nie z requestu.
    where_sql = "\n    AND ".join(conditions)
    return (
        "SELECT\n"
        f"{_SLICE_HEADER_SQL},\n"
        f"    {stat_select_sql.strip()}\n"
        f"FROM {stats_table} stat\n"
        "JOIN matches m ON stat.match_id = m.id\n"
        "JOIN seasons s ON s.id = m.season\n"
        "JOIN teams own ON own.id = stat.team_id\n"
        "JOIN teams home ON home.id = m.home_team\n"
        "JOIN teams away ON away.id = m.away_team\n"
        f"WHERE {where_sql}\n"
        "ORDER BY m.game_date DESC, m.id DESC\n"
        "LIMIT %s")


def _player_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "player_id": int(row["player_id"]),
        "player_name": _required_text(row["player_name"]),
        "position": _optional_text(row["position"]),
        "sport_id": _optional_int(row["sport_id"])}


def _search_hit(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "player_id": int(row["player_id"]),
        "player_name": _required_text(row["player_name"]),
        "position": _optional_text(row["position"]),
        "current_team_name": _optional_text(row["current_team_name"])}


def _required_text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def _fetch_one(
        query: str,
        params: tuple[object, ...]) -> dict[str, Any] | None:
    rows = _fetch_all(query, params)
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
