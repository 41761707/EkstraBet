"""SQL queries for match schedule and detail data."""

from __future__ import annotations
from datetime import date
import pandas as pd
from backend.database import get_db_connection

_MATCH_SELECT_COLUMNS = """
    m.id,
    m.league AS league_id,
    m.season AS season_id,
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
    t2.shortcut AS away_shortcut
"""

_MATCH_STATS_COLUMNS = """
    m.home_team_xg,
    m.away_team_xg,
    m.home_team_bp,
    m.away_team_bp,
    m.home_team_sc,
    m.away_team_sc,
    m.home_team_sog,
    m.away_team_sog,
    m.home_team_ck,
    m.away_team_ck,
    m.home_team_fouls,
    m.away_team_fouls,
    m.home_team_yc,
    m.away_team_yc,
    m.home_team_rc,
    m.away_team_rc
"""


def fetch_league_matches(
    league_id: int,
    season_id: int,
    round_num: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None) -> pd.DataFrame:
    """Return matches for a league season with optional filters."""
    conditions = ["m.league = %s", "m.season = %s"]
    params: list[object] = [league_id, season_id]

    if round_num is not None:
        conditions.append("m.round = %s")
        params.append(round_num)

    if date_from is not None:
        conditions.append("CAST(m.game_date AS DATE) >= %s")
        params.append(date_from)

    if date_to is not None:
        conditions.append("CAST(m.game_date AS DATE) <= %s")
        params.append(date_to)

    where_clause = " AND ".join(conditions)
    query = f"""
        SELECT
            {_MATCH_SELECT_COLUMNS}
        FROM matches m
        JOIN teams t1 ON m.home_team = t1.id
        JOIN teams t2 ON m.away_team = t2.id
        WHERE {where_clause}
        ORDER BY m.game_date ASC
    """
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=tuple(params))


def match_exists(match_id: int) -> bool:
    """Return True when the match id exists in the database."""
    query = "SELECT 1 FROM matches WHERE id = %s LIMIT 1"
    with get_db_connection() as conn:
        frame = pd.read_sql(query, conn, params=(match_id,))
    return not frame.empty


def fetch_match_by_id(match_id: int) -> pd.DataFrame:
    """Return a single match row with teams and basic stats."""
    query = f"""
        SELECT
            {_MATCH_SELECT_COLUMNS},
            {_MATCH_STATS_COLUMNS}
        FROM matches m
        JOIN teams t1 ON m.home_team = t1.id
        JOIN teams t2 ON m.away_team = t2.id
        WHERE m.id = %s
    """
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=(match_id,))


def fetch_match_final_predictions(
    match_id: int,
    model_ids: list[int] | None = None) -> pd.DataFrame:
    """Return final predictions joined with event names for a match."""
    conditions = ["p.match_id = %s"]
    params: list[object] = [match_id]

    if model_ids:
        placeholders = ",".join(["%s"] * len(model_ids))
        conditions.append(f"p.model_id IN ({placeholders})")
        params.extend(model_ids)

    where_clause = " AND ".join(conditions)
    query = f"""
        SELECT
            p.event_id,
            e.name AS event_name,
            p.model_id,
            fp.outcome
        FROM predictions p
        JOIN final_predictions fp ON p.id = fp.predictions_id
        JOIN events e ON p.event_id = e.id
        WHERE {where_clause}
        ORDER BY p.event_id, p.model_id
    """
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=tuple(params))


def fetch_match_odds(match_id: int) -> pd.DataFrame:
    """Return bookmaker odds for a match."""
    query = """
        SELECT
            b.name AS bookmaker,
            e.name AS event,
            o.odds
        FROM odds o
        JOIN bookmakers b ON o.bookmaker = b.id
        JOIN events e ON o.event = e.id
        WHERE o.match_id = %s
        ORDER BY b.name, e.name
    """
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=(match_id,))
