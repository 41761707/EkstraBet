"""Hockey league-level aggregate statistics."""

from __future__ import annotations
from typing import Any, Literal
import pandas as pd
from backend.database import get_db_connection
from backend.repositories.sport_league_repository import REGULAR_SEASON_ROUND

Category = Literal["shots", "goals", "over_under"]


def _round_filter(phase: int | None) -> tuple[str, list[object]]:
    """Build SQL filter for regular season or playoffs."""
    if phase is None:
        return "", []
    if phase == REGULAR_SEASON_ROUND:
        return " AND m.round = %s", [REGULAR_SEASON_ROUND]
    return " AND m.round != %s", [REGULAR_SEASON_ROUND]


def fetch_hockey_shots_stats(
    league_id: int,
    season_id: int,
    phase: int | None = None) -> list[dict[str, Any]]:
    """Return per-team shots on goal averages."""
    round_sql, round_params = _round_filter(phase)
    query = f"""
        SELECT
            t.name AS team_name,
            t.shortcut AS team_shortcut,
            ROUND(AVG(
                CASE
                    WHEN m.home_team = t.id THEN m.home_team_sog
                    WHEN m.away_team = t.id THEN m.away_team_sog
                END), 2) AS avg_shots_for,
            ROUND(AVG(
                CASE
                    WHEN m.home_team = t.id THEN m.away_team_sog
                    WHEN m.away_team = t.id THEN m.home_team_sog
                END), 2) AS avg_shots_against,
            COUNT(*) AS matches_played
        FROM teams t
        JOIN matches m ON (m.home_team = t.id OR m.away_team = t.id)
        WHERE m.league = %s
            AND m.season = %s
            AND m.result != '0'
            AND m.home_team_sog IS NOT NULL
            AND m.away_team_sog IS NOT NULL
            {round_sql}
        GROUP BY t.id, t.name, t.shortcut
        ORDER BY avg_shots_for DESC
    """
    params: list[object] = [league_id, season_id, *round_params]
    with get_db_connection() as conn:
        frame = pd.read_sql(query, conn, params=tuple(params))
    if frame.empty:
        return []
    return [
        {
            "team_name": str(row["team_name"]),
            "team_shortcut": str(row["team_shortcut"] or ""),
            "avg_for": float(row["avg_shots_for"]),
            "avg_against": float(row["avg_shots_against"]),
            "matches_played": int(row["matches_played"])
        }
        for _, row in frame.iterrows()
    ]


def fetch_hockey_goals_stats(
    league_id: int,
    season_id: int,
    phase: int | None = None) -> list[dict[str, Any]]:
    """Return per-team goals averages."""
    round_sql, round_params = _round_filter(phase)
    query = f"""
        SELECT
            t.name AS team_name,
            t.shortcut AS team_shortcut,
            ROUND(AVG(
                CASE
                    WHEN m.home_team = t.id THEN m.home_team_goals
                    WHEN m.away_team = t.id THEN m.away_team_goals
                END), 2) AS avg_goals_for,
            ROUND(AVG(
                CASE
                    WHEN m.home_team = t.id THEN m.away_team_goals
                    WHEN m.away_team = t.id THEN m.home_team_goals
                END), 2) AS avg_goals_against,
            COUNT(*) AS matches_played
        FROM teams t
        JOIN matches m ON (m.home_team = t.id OR m.away_team = t.id)
        WHERE m.league = %s
            AND m.season = %s
            AND m.result != '0'
            {round_sql}
        GROUP BY t.id, t.name, t.shortcut
        ORDER BY avg_goals_for DESC
    """
    params: list[object] = [league_id, season_id, *round_params]
    with get_db_connection() as conn:
        frame = pd.read_sql(query, conn, params=tuple(params))
    if frame.empty:
        return []
    return [
        {
            "team_name": str(row["team_name"]),
            "team_shortcut": str(row["team_shortcut"] or ""),
            "avg_for": float(row["avg_goals_for"]),
            "avg_against": float(row["avg_goals_against"]),
            "matches_played": int(row["matches_played"])
        }
        for _, row in frame.iterrows()
    ]


def fetch_hockey_over_under_stats(
    league_id: int,
    season_id: int,
    phase: int | None = None) -> list[dict[str, Any]]:
    """Return per-team over/under hit rates for common lines."""
    round_sql, round_params = _round_filter(phase)
    query = f"""
        SELECT
            t.name AS team_name,
            t.shortcut AS team_shortcut,
            COUNT(*) AS total_matches,
            SUM(CASE WHEN (m.home_team_goals + m.away_team_goals) > 4 THEN 1 ELSE 0 END) AS over_4_5,
            SUM(CASE WHEN (m.home_team_goals + m.away_team_goals) > 5 THEN 1 ELSE 0 END) AS over_5_5,
            SUM(CASE WHEN (m.home_team_goals + m.away_team_goals) > 6 THEN 1 ELSE 0 END) AS over_6_5,
            SUM(CASE WHEN (m.home_team_goals + m.away_team_goals) > 7 THEN 1 ELSE 0 END) AS over_7_5
        FROM teams t
        JOIN matches m ON (m.home_team = t.id OR m.away_team = t.id)
        WHERE m.league = %s
            AND m.season = %s
            AND m.result != '0'
            {round_sql}
        GROUP BY t.id, t.name, t.shortcut
        ORDER BY over_5_5 DESC
    """
    params: list[object] = [league_id, season_id, *round_params]
    with get_db_connection() as conn:
        frame = pd.read_sql(query, conn, params=tuple(params))
    if frame.empty:
        return []
    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        played = int(row["total_matches"])
        rows.append({
            "team_name": str(row["team_name"]),
            "team_shortcut": str(row["team_shortcut"] or ""),
            "matches_played": played,
            "over_4_5_pct": round(int(row["over_4_5"]) * 100 / played, 1),
            "over_5_5_pct": round(int(row["over_5_5"]) * 100 / played, 1),
            "over_6_5_pct": round(int(row["over_6_5"]) * 100 / played, 1),
            "over_7_5_pct": round(int(row["over_7_5"]) * 100 / played, 1)
        })
    return rows


def bucket_goal_totals(totals: list[int]) -> dict[str, int]:
    """Count matches in the league goal pie buckets.

    Buckets match the old Streamlit chart: under 5, exactly 5, 6, 7
    and 8 or more. Totals are regulation goals.
    """
    under_5 = 0
    exactly_5 = 0
    exactly_6 = 0
    exactly_7 = 0
    over_7 = 0
    for total in totals:
        if total < 5:
            under_5 += 1
        elif total == 5:
            exactly_5 += 1
        elif total == 6:
            exactly_6 += 1
        elif total == 7:
            exactly_7 += 1
        else:
            over_7 += 1
    return {
        "total_matches": len(totals),
        "under_5": under_5,
        "exactly_5": exactly_5,
        "exactly_6": exactly_6,
        "exactly_7": exactly_7,
        "over_7": over_7
    }


def fetch_hockey_goals_distribution(
    league_id: int,
    season_id: int,
    phase: int | None = None) -> dict[str, int]:
    """Return league-wide regulation goal totals split into pie buckets."""
    round_sql, round_params = _round_filter(phase)
    query = f"""
        SELECT m.home_team_goals + m.away_team_goals AS total_goals
        FROM matches m
        WHERE m.league = %s
            AND m.season = %s
            AND m.result != '0'
            AND m.home_team_goals IS NOT NULL
            AND m.away_team_goals IS NOT NULL
            {round_sql}
    """
    params: list[object] = [league_id, season_id, *round_params]
    with get_db_connection() as conn:
        frame = pd.read_sql(query, conn, params=tuple(params))
    if frame.empty:
        return bucket_goal_totals([])
    totals = [int(value) for value in frame["total_goals"].tolist()]
    return bucket_goal_totals(totals)
