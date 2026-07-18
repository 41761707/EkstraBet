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
            m.away_team AS away_team_id,
            m.home_team_goals,
            m.away_team_goals,
            m.result
        FROM matches m
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
        SELECT team_id, team_name
        FROM (
            SELECT DISTINCT
                m.home_team AS team_id,
                t.name AS team_name
            FROM matches m
            JOIN teams t ON m.home_team = t.id
            WHERE m.league = %s AND m.season = %s
            UNION
            SELECT DISTINCT
                m.away_team AS team_id,
                t.name AS team_name
            FROM matches m
            JOIN teams t ON m.away_team = t.id
            WHERE m.league = %s AND m.season = %s
        ) AS season_teams
        ORDER BY team_name
    """
    with get_db_connection() as conn:
        return pd.read_sql(
            query,
            conn,
            params=(league_id, season_id, league_id, season_id))
