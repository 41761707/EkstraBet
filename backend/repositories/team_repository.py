"""SQL queries for team profile and match history."""

from __future__ import annotations
import pandas as pd
from backend.database import get_db_connection

_TEAM_SELECT_COLUMNS = """
    t.id,
    t.name,
    t.shortcut,
    t.country AS country_id,
    c.name AS country_name,
    c.emoji AS country_emoji,
    t.sport_id AS sport_id,
    s.name AS sport_name
"""


def team_exists(team_id: int) -> bool:
    """Return True when the team id exists in the database."""
    query = "SELECT 1 FROM teams WHERE id = %s LIMIT 1"
    with get_db_connection() as conn:
        frame = pd.read_sql(query, conn, params=(team_id,))
    return not frame.empty


def fetch_team_by_id(team_id: int) -> pd.DataFrame:
    """Return a single team row with country and sport metadata."""
    query = f"""
        SELECT
            {_TEAM_SELECT_COLUMNS}
        FROM teams t
        LEFT JOIN countries c ON t.country = c.id
        LEFT JOIN sports s ON t.sport_id = s.id
        WHERE t.id = %s
    """
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=(team_id,))


def fetch_team_played_matches(
    team_id: int,
    season_id: int | None = None,
    league_id: int | None = None,
    limit: int | None = None) -> pd.DataFrame:
    """Return played matches for a team"""
    conditions = [
        "(m.home_team = %s OR m.away_team = %s)",
        "m.result != '0'"]
    params: list[object] = [team_id, team_id]

    if season_id is not None:
        conditions.append("m.season = %s")
        params.append(season_id)

    if league_id is not None:
        conditions.append("m.league = %s")
        params.append(league_id)

    where_clause = " AND ".join(conditions)
    limit_clause = ""
    if limit is not None:
        limit_clause = "LIMIT %s"
        params.append(limit)

    query = f"""
        SELECT
            m.id,
            m.league AS league_id,
            m.season AS season_id,
            m.sport_id,
            m.round,
            m.game_date,
            m.result,
            m.home_team_goals,
            m.away_team_goals,
            m.home_team AS home_id,
            t1.name AS home_name,
            t1.shortcut AS home_shortcut,
            m.away_team AS away_id,
            t2.name AS away_name,
            t2.shortcut AS away_shortcut,
            m.home_team_sc,
            m.away_team_sc,
            m.home_team_sog,
            m.away_team_sog,
            m.home_team_fk,
            m.away_team_fk,
            m.home_team_fouls,
            m.away_team_fouls,
            m.home_team_ck,
            m.away_team_ck,
            m.home_team_off,
            m.away_team_off,
            m.home_team_yc,
            m.away_team_yc,
            m.home_team_rc,
            m.away_team_rc,
            hma.OT AS hma_ot,
            hma.SO AS hma_so,
            hma.OTwinner AS hma_ot_winner,
            hma.SOwinner AS hma_so_winner
        FROM matches m
        JOIN teams t1 ON m.home_team = t1.id
        JOIN teams t2 ON m.away_team = t2.id
        LEFT JOIN hockey_matches_add hma ON m.id = hma.match_id
        WHERE {where_clause}
        ORDER BY m.game_date DESC
        {limit_clause}
    """
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=tuple(params))


def fetch_head_to_head_matches(
    team_1_id: int,
    team_2_id: int,
    limit: int = 5) -> pd.DataFrame:
    """Return recent head-to-head matches between two teams."""
    from backend.repositories.match_repository import (
        _HOCKEY_MATCHES_ADD_JOIN,
        _HOCKEY_SCORE_RESOLUTION_COLUMNS,
        _MATCH_BASE_COLUMNS,
        _MATCH_SCORE_RESOLUTION_COLUMNS,
        _MATCH_SCORE_RESOLUTION_JOIN)

    query = f"""
        SELECT
            {_MATCH_BASE_COLUMNS},
            {_MATCH_SCORE_RESOLUTION_COLUMNS},
            {_HOCKEY_SCORE_RESOLUTION_COLUMNS}
        FROM matches m
        JOIN teams t1 ON m.home_team = t1.id
        JOIN teams t2 ON m.away_team = t2.id
        {_MATCH_SCORE_RESOLUTION_JOIN}
        {_HOCKEY_MATCHES_ADD_JOIN}
        WHERE (
            (m.home_team = %s AND m.away_team = %s)
            OR (m.home_team = %s AND m.away_team = %s)
        )
            AND m.result != '0'
        ORDER BY m.game_date DESC
        LIMIT %s
    """
    with get_db_connection() as conn:
        return pd.read_sql(
            query,
            conn,
            params=(team_1_id, team_2_id, team_2_id, team_1_id, limit))
