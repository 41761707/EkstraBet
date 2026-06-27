"""SQL queries for league standings data."""

from __future__ import annotations
import pandas as pd
from backend.database import get_db_connection


def fetch_league_results(
    league_id: int,
    season_id: int) -> pd.DataFrame:
    """Return played match results for standings calculation."""
    query = """
        SELECT
            m.home_team AS home_team_id,
            t1.name AS home_team_name,
            m.away_team AS away_team_id,
            t2.name AS away_team_name,
            m.home_team_goals,
            m.away_team_goals,
            m.result
        FROM matches m
        JOIN teams t1 ON m.home_team = t1.id
        JOIN teams t2 ON m.away_team = t2.id
        WHERE m.league = %s
            AND m.season = %s
            AND m.result != '0'
            AND m.round < 900
    """
    with get_db_connection() as conn:
        return pd.read_sql(
            query,
            conn,
            params=(league_id, season_id))


def fetch_teams_in_season(
    league_id: int,
    season_id: int) -> pd.DataFrame:
    """Return distinct teams participating in a league season."""
    query = """
        SELECT DISTINCT
            t.id AS team_id,
            t.name AS team_name
        FROM matches m
        JOIN teams t ON (m.home_team = t.id OR m.away_team = t.id)
        WHERE m.league = %s
            AND m.season = %s
        ORDER BY t.name
    """
    with get_db_connection() as conn:
        return pd.read_sql(
            query,
            conn,
            params=(league_id, season_id))
