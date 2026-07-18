"""SQL queries for NHL/NBA league pages."""

from __future__ import annotations
from datetime import date
import pandas as pd
from backend.database import get_db_connection

HOCKEY_SPORT_ID = 2
BASKETBALL_SPORT_ID = 3
REGULAR_SEASON_ROUND = 100


def _phase_condition(phase: int | None) -> tuple[str, list[object]]:
    """Build SQL round filter for regular season or playoffs."""
    if phase is None:
        return "", []
    if phase == REGULAR_SEASON_ROUND:
        return " AND m.round = %s", [REGULAR_SEASON_ROUND]
    return " AND m.round != %s", [REGULAR_SEASON_ROUND]


def fetch_sport_matches(
    league_id: int,
    season_id: int,
    sport_id: int,
    phase: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None) -> pd.DataFrame:
    """Return sport league matches with optional phase and date filters."""
    conditions = [
        "m.league = %s",
        "m.season = %s",
        "m.sport_id = %s"]
    params: list[object] = [league_id, season_id, sport_id]

    phase_sql, phase_params = _phase_condition(phase)
    if phase_sql:
        conditions.append(phase_sql.lstrip(" AND "))
        params.extend(phase_params)

    if date_from is not None:
        conditions.append("CAST(m.game_date AS DATE) >= %s")
        params.append(date_from)
    if date_to is not None:
        conditions.append("CAST(m.game_date AS DATE) <= %s")
        params.append(date_to)

    hockey_join = ""
    hockey_cols = ""
    basketball_join = ""
    basketball_cols = ""
    if sport_id == HOCKEY_SPORT_ID:
        hockey_join = "LEFT JOIN hockey_matches_add hma ON m.id = hma.match_id"
        hockey_cols = """
            , hma.OT AS hma_ot
            , hma.SO AS hma_so
            , hma.OTwinner AS hma_ot_winner
            , hma.SOwinner AS hma_so_winner"""
    elif sport_id == BASKETBALL_SPORT_ID:
        basketball_join = (
            "LEFT JOIN basketball_matches_add bma ON m.id = bma.match_id")
        basketball_cols = ", bma.ot AS bma_ot"

    where_clause = " AND ".join(conditions)
    query = f"""
        SELECT
            m.id,
            m.league AS league_id,
            m.season AS season_id,
            m.round,
            m.game_date,
            m.result,
            m.home_team_goals,
            m.away_team_goals,
            m.home_team_sog,
            m.away_team_sog,
            m.home_team AS home_id,
            t1.name AS home_name,
            t1.shortcut AS home_shortcut,
            m.away_team AS away_id,
            t2.name AS away_name,
            t2.shortcut AS away_shortcut
            {hockey_cols}
            {basketball_cols}
        FROM matches m
        JOIN teams t1 ON m.home_team = t1.id
        JOIN teams t2 ON m.away_team = t2.id
        {hockey_join}
        {basketball_join}
        WHERE {where_clause}
        ORDER BY m.game_date DESC
    """
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=tuple(params))


def fetch_teams_in_sport_season(
    league_id: int,
    season_id: int,
    sport_id: int) -> pd.DataFrame:
    """Return distinct teams that played in a league season."""
    query = """
        SELECT DISTINCT
            t.id AS team_id,
            t.name AS team_name,
            t.shortcut AS team_shortcut
        FROM teams t
        JOIN matches m ON (m.home_team = t.id OR m.away_team = t.id)
        WHERE m.league = %s
            AND m.season = %s
            AND m.sport_id = %s
        ORDER BY t.name
    """
    with get_db_connection() as conn:
        return pd.read_sql(
            query,
            conn,
            params=(league_id, season_id, sport_id))


def fetch_played_sport_matches(
    league_id: int,
    season_id: int,
    sport_id: int,
    phase: int | None = None) -> pd.DataFrame:
    """Return played matches for standings and league stats."""
    return fetch_sport_matches(
        league_id=league_id,
        season_id=season_id,
        sport_id=sport_id,
        phase=phase).query("result != '0'")
