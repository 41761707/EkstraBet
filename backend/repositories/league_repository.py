"""SQL queries for league navigation data."""

from __future__ import annotations
import pandas as pd
from backend.database import get_db_connection

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
