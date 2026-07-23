"""Database access for historical and upcoming football matches."""

from __future__ import annotations

import logging
from datetime import date
from datetime import datetime

import pandas as pd

from backend.database import get_db_connection

logger = logging.getLogger(__name__)

MATCH_COLUMNS = [
    "id",
    "league",
    "season",
    "home_team",
    "away_team",
    "game_date",
    "round",
    "sport_id",
    "home_team_goals",
    "away_team_goals",
    "result",
    "home_team_xg",
    "away_team_xg",
    "home_team_bp",
    "away_team_bp",
    "home_team_sc",
    "away_team_sc",
    "home_team_sog",
    "away_team_sog"
]


def _match_select_clause() -> str:
    return ",\n            ".join(f"m.{column}" for column in MATCH_COLUMNS)


def fetch_finished_matches(
        sport_id: int,
        date_to: date | datetime) -> pd.DataFrame:
    """Fetch valid finished matches strictly before the supplied date."""
    query = f"""
        SELECT
            {_match_select_clause()}
        FROM matches m
        WHERE m.sport_id = %s
          AND m.game_date < %s
          AND m.result IN ('1', 'X', '2')
          AND m.home_team_goals IS NOT NULL
          AND m.away_team_goals IS NOT NULL
        ORDER BY m.game_date, m.id
    """
    with get_db_connection() as connection:
        frame = pd.read_sql(query, connection, params=(sport_id, date_to))
    logger.info("Fetched %s finished matches", len(frame))
    return frame


def fetch_upcoming_matches(
        sport_id: int,
        date_from: date | datetime,
        date_to: date | datetime | None = None,
        league_id: int | None = None) -> pd.DataFrame:
    """Fetch scheduled matches from a date, optionally by league and end date."""
    if date_from is None:
        date_from = datetime.now()
    filters = [
        "m.sport_id = %s",
        "m.game_date >= %s",
        "(m.result = '0' OR m.result IS NULL)"
    ]
    params: tuple[object, ...] = (sport_id, date_from)
    if date_to is not None:
        filters.append("m.game_date < %s")
        params = (*params, date_to)
    if league_id is not None:
        filters.append("m.league = %s")
        params = (*params, league_id)
    query = f"""
        SELECT
            {_match_select_clause()}
        FROM matches m
        WHERE {" AND ".join(filters)}
        ORDER BY m.game_date, m.id
    """
    with get_db_connection() as connection:
        frame = pd.read_sql(query, connection, params=params)
    logger.info("Fetched %s upcoming matches", len(frame))
    return frame


def fetch_teams(sport_id: int) -> pd.DataFrame:
    """Fetch teams for a sport."""
    query = """
        SELECT t.id, t.name, t.shortcut, t.country, t.sport_id
        FROM teams t
        WHERE t.sport_id = %s
        ORDER BY t.id
    """
    with get_db_connection() as connection:
        return pd.read_sql(query, connection, params=(sport_id,))


def fetch_league_context(
        sport_id: int,
        league_id: int | None = None) -> pd.DataFrame:
    """Fetch league identifiers, active season, and competition tier."""
    clauses = ["l.sport_id = %s"]
    params: tuple[object, ...] = (sport_id,)
    if league_id is not None:
        clauses.append("l.id = %s")
        params = (*params, league_id)
    query = f"""
        SELECT
            l.id AS league_id,
            l.name AS league_name,
            l.current_season_id,
            l.tier,
            l.active
        FROM leagues l
        WHERE {" AND ".join(clauses)}
        ORDER BY l.id
    """
    with get_db_connection() as connection:
        return pd.read_sql(query, connection, params=params)
