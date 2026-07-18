"""Basketball league-level aggregate statistics."""

from __future__ import annotations
from typing import Any, Literal
import pandas as pd
from backend.database import get_db_connection
from backend.repositories.sport_league_repository import (
    BASKETBALL_SPORT_ID,
    REGULAR_SEASON_ROUND)

Category = Literal["shooting", "points", "over_under"]


def _round_filter(phase: int | None) -> tuple[str, list[object]]:
    """Build SQL filter for regular season or playoffs."""
    if phase is None:
        return "", []
    if phase == REGULAR_SEASON_ROUND:
        return " AND m.round = %s", [REGULAR_SEASON_ROUND]
    return " AND m.round != %s", [REGULAR_SEASON_ROUND]


def fetch_basketball_points_distribution(
    league_id: int,
    season_id: int,
    phase: int | None = None) -> dict[str, Any]:
    """Return league-wide points distribution summary."""
    round_sql, round_params = _round_filter(phase)
    query = f"""
        SELECT
            m.home_team_goals + m.away_team_goals AS total_points,
            m.home_team_goals AS home_points,
            m.away_team_goals AS away_points
        FROM matches m
        WHERE m.league = %s
            AND m.season = %s
            AND m.sport_id = %s
            AND m.result != '0'
            {round_sql}
        ORDER BY m.game_date
    """
    params: list[object] = [
        league_id,
        season_id,
        BASKETBALL_SPORT_ID,
        *round_params]
    with get_db_connection() as conn:
        frame = pd.read_sql(query, conn, params=tuple(params))
    if frame.empty:
        return {"matches": [], "summary": None}
    totals = frame["total_points"].astype(float)
    return {
        "matches": [
            {
                "total_points": int(row["total_points"]),
                "home_points": int(row["home_points"]),
                "away_points": int(row["away_points"])
            }
            for _, row in frame.iterrows()
        ],
        "summary": {
            "average_total": round(float(totals.mean()), 1),
            "median_total": round(float(totals.median()), 1),
            "min_total": int(totals.min()),
            "max_total": int(totals.max()),
            "average_home": round(float(frame["home_points"].mean()), 1),
            "average_away": round(float(frame["away_points"].mean()), 1)
        }
    }


def fetch_basketball_shooting_stats(
    league_id: int,
    season_id: int,
    phase: int | None = None) -> list[dict[str, Any]]:
    """Return per-team field goal percentages."""
    round_sql, round_params = _round_filter(phase)
    query = f"""
        SELECT
            t.name AS team_name,
            t.shortcut AS team_shortcut,
            ROUND(AVG(
                CASE
                    WHEN m.home_team = t.id THEN bma.home_team_field_goals_acc
                    WHEN m.away_team = t.id THEN bma.away_team_field_goals_acc
                END), 1) AS avg_fg_pct,
            ROUND(AVG(
                CASE
                    WHEN m.home_team = t.id THEN bma.home_team_3_p_acc
                    WHEN m.away_team = t.id THEN bma.away_team_3_p_acc
                END), 1) AS avg_3p_pct,
            COUNT(*) AS matches_played
        FROM teams t
        JOIN matches m ON (m.home_team = t.id OR m.away_team = t.id)
        JOIN basketball_matches_add bma ON m.id = bma.match_id
        WHERE m.league = %s
            AND m.season = %s
            AND m.sport_id = %s
            AND m.result != '0'
            {round_sql}
        GROUP BY t.id, t.name, t.shortcut
        ORDER BY avg_fg_pct DESC
    """
    params: list[object] = [
        league_id,
        season_id,
        BASKETBALL_SPORT_ID,
        *round_params]
    with get_db_connection() as conn:
        frame = pd.read_sql(query, conn, params=tuple(params))
    if frame.empty:
        return []
    return [
        {
            "team_name": str(row["team_name"]),
            "team_shortcut": str(row["team_shortcut"] or ""),
            "field_goal_pct": float(row["avg_fg_pct"]),
            "three_point_pct": float(row["avg_3p_pct"]),
            "matches_played": int(row["matches_played"])
        }
        for _, row in frame.iterrows()
    ]


def fetch_basketball_over_under_stats(
    league_id: int,
    season_id: int,
    phase: int | None = None) -> list[dict[str, Any]]:
    """Return per-team over/under hit rates for common NBA lines."""
    round_sql, round_params = _round_filter(phase)
    query = f"""
        SELECT
            t.name AS team_name,
            t.shortcut AS team_shortcut,
            COUNT(*) AS total_matches,
            SUM(CASE WHEN (m.home_team_goals + m.away_team_goals) > 210.5 THEN 1 ELSE 0 END) AS over_210_5,
            SUM(CASE WHEN (m.home_team_goals + m.away_team_goals) > 220.5 THEN 1 ELSE 0 END) AS over_220_5,
            SUM(CASE WHEN (m.home_team_goals + m.away_team_goals) > 230.5 THEN 1 ELSE 0 END) AS over_230_5
        FROM teams t
        JOIN matches m ON (m.home_team = t.id OR m.away_team = t.id)
        WHERE m.league = %s
            AND m.season = %s
            AND m.sport_id = %s
            AND m.result != '0'
            {round_sql}
        GROUP BY t.id, t.name, t.shortcut
        ORDER BY over_220_5 DESC
    """
    params: list[object] = [
        league_id,
        season_id,
        BASKETBALL_SPORT_ID,
        *round_params]
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
            "over_210_5_pct": round(int(row["over_210_5"]) * 100 / played, 1),
            "over_220_5_pct": round(int(row["over_220_5"]) * 100 / played, 1),
            "over_230_5_pct": round(int(row["over_230_5"]) * 100 / played, 1)
        })
    return rows
