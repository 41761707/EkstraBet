"""Read per-match NHL special-teams inputs."""

from __future__ import annotations

from typing import Any

import pandas as pd

from backend.database import get_db_connection
from backend.repositories.sport_league_repository import (
    _phase_condition)


MINOR_PENALTY_EVENT_ID = 183
MAJOR_PENALTY_EVENT_ID = 185
GAME_MISCONDUCT_EVENT_ID = 186
MISCONDUCT_EVENT_ID = 189
PENALTY_EVENT_IDS = (
    MINOR_PENALTY_EVENT_ID,
    MAJOR_PENALTY_EVENT_ID,
    GAME_MISCONDUCT_EVENT_ID,
    MISCONDUCT_EVENT_ID)
_EXTRA_TIME_RESULT = "X"


def _optional_float(value: object) -> float | None:
    """Convert a nullable percent to float."""
    if value is None or pd.isna(value):
        return None
    return float(value)


def _int_value(value: object) -> int:
    """Convert a nullable count to int. Missing means zero."""
    if value is None or pd.isna(value):
        return 0
    return int(value)


def _text(value: object) -> str:
    """Convert a nullable label to text."""
    if value is None or pd.isna(value):
        return ""
    return str(value)


def _map_match(row: pd.Series) -> dict[str, Any]:
    """Map one SQL row onto the service contract."""
    return {
        "match_id": int(row["match_id"]),
        "went_to_extra_time": _text(row["result"]) == _EXTRA_TIME_RESULT,
        "home_team_id": int(row["home_team_id"]),
        "home_team_name": _text(row["home_team_name"]),
        "home_team_shortcut": _text(row["home_team_shortcut"]),
        "away_team_id": int(row["away_team_id"]),
        "away_team_name": _text(row["away_team_name"]),
        "away_team_shortcut": _text(row["away_team_shortcut"]),
        "home_pp_goals": _int_value(row["home_team_pp_goals"]),
        "away_pp_goals": _int_value(row["away_team_pp_goals"]),
        "home_pp_accuracy": _optional_float(row["home_team_pp_acc"]),
        "away_pp_accuracy": _optional_float(row["away_team_pp_acc"]),
        "home_fouls": _int_value(row["home_team_fouls"]),
        "away_fouls": _int_value(row["away_team_fouls"])
    }


def _map_penalty(row: pd.Series) -> dict[str, Any]:
    """Map one penalty row. The match id is only a join key."""
    return {
        "match_id": int(row["match_id"]),
        "team_id": int(row["team_id"]),
        "event_id": int(row["event_id"]),
        "description": _text(row["description"]),
        "period": _int_value(row["period"]),
        "event_time": _text(row["event_time"])
    }


def _read_frame(
        query: str,
        params: list[object]) -> pd.DataFrame:
    """Run one special-teams read."""
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=tuple(params))


def _fetch_matches(
        league_id: int,
        season_id: int,
        phase_sql: str,
        phase_params: list[object]) -> list[dict[str, Any]]:
    """Return played matches with power-play goals, rates and fouls."""
    query = f"""
        SELECT
            m.id AS match_id,
            m.result,
            ht.id AS home_team_id,
            ht.name AS home_team_name,
            ht.shortcut AS home_team_shortcut,
            away.id AS away_team_id,
            away.name AS away_team_name,
            away.shortcut AS away_team_shortcut,
            hma.home_team_pp_goals,
            hma.away_team_pp_goals,
            hma.home_team_pp_acc,
            hma.away_team_pp_acc,
            m.home_team_fouls,
            m.away_team_fouls
        FROM matches m
        JOIN hockey_matches_add hma ON hma.match_id = m.id
        JOIN teams ht ON ht.id = m.home_team
        JOIN teams away ON away.id = m.away_team
        WHERE m.league = %s
            AND m.season = %s
            AND m.result != '0'
            {phase_sql}
        ORDER BY m.id
    """
    params: list[object] = [league_id, season_id, *phase_params]
    frame = _read_frame(query, params)
    if frame.empty:
        return []
    return [_map_match(row) for _, row in frame.iterrows()]


def _fetch_penalties(
        league_id: int,
        season_id: int,
        phase_sql: str,
        phase_params: list[object]) -> list[dict[str, Any]]:
    """Return minor, major and misconduct rows for the same matches."""
    event_ids = ", ".join(str(event_id) for event_id in PENALTY_EVENT_IDS)
    query = f"""
        SELECT
            hme.match_id,
            hme.team_id,
            hme.event_id,
            hme.description,
            hme.period,
            hme.event_time
        FROM hockey_match_events hme
        JOIN matches m ON m.id = hme.match_id
        WHERE m.league = %s
            AND m.season = %s
            AND m.result != '0'
            AND hme.event_id IN ({event_ids})
            {phase_sql}
        ORDER BY hme.match_id, hme.period, hme.event_time
    """
    params: list[object] = [league_id, season_id, *phase_params]
    frame = _read_frame(query, params)
    if frame.empty:
        return []
    return [_map_penalty(row) for _, row in frame.iterrows()]


def _attach_penalties(
        matches: list[dict[str, Any]],
        penalties: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group penalties onto their match and drop the join key."""
    grouped: dict[int, list[dict[str, Any]]] = {}
    for penalty in penalties:
        match_id = int(penalty.pop("match_id"))
        grouped.setdefault(match_id, []).append(penalty)
    for match in matches:
        match_id = int(match.pop("match_id"))
        match["penalties"] = grouped.get(match_id, [])
    return matches


def fetch_special_teams_matches(
        league_id: int,
        season_id: int,
        phase: int | None = None) -> list[dict[str, Any]]:
    """Return played matches with power-play goals, fouls and penalties."""
    phase_sql, phase_params = _phase_condition(phase)
    matches = _fetch_matches(
        league_id, season_id, phase_sql, phase_params)
    if not matches:
        return []
    penalties = _fetch_penalties(
        league_id, season_id, phase_sql, phase_params)
    return _attach_penalties(matches, penalties)
