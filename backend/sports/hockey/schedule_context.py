"""Prematch rest and workload for one NHL match."""

from __future__ import annotations

from typing import Any

import pandas as pd

from models.pipeline.features.hockey.schedule import build_schedule_features


_ARENA_COLUMNS = ["team_id", "latitude", "longitude", "timezone"]
_FEATURE_SIDES = ("home", "away")


def build_hockey_schedule_context(
    home_history: pd.DataFrame,
    away_history: pd.DataFrame,
    arenas: pd.DataFrame,
    *,
    match_id: int,
    home_team_id: int,
    away_team_id: int,
    game_date: object) -> dict[str, Any] | None:
    """Return rest, back-to-back and games in seven days for both clubs.

    Naive ``game_date`` values are Warsaw time, the same clock the
    schedule features use. Rest and the seven-day window then follow
    each match's home-arena local date, including this match.
    """
    if pd.isna(pd.to_datetime(game_date, errors="coerce")):
        return None
    features = build_schedule_features(
        _schedule_matches(
            home_history,
            away_history,
            match_id,
            home_team_id,
            away_team_id,
            game_date),
        _arenas_frame(arenas))
    matched = features.loc[features["match_id"] == int(match_id)]
    if matched.empty:
        return None
    record = matched.iloc[0]
    return {
        side: _side_context(record, side)
        for side in _FEATURE_SIDES
    }


def _schedule_matches(
    home_history: pd.DataFrame,
    away_history: pd.DataFrame,
    match_id: int,
    home_team_id: int,
    away_team_id: int,
    game_date: object) -> pd.DataFrame:
    """One row per earlier game, then this match as not yet played."""
    rows: dict[int, dict[str, object]] = {}
    for frame in (home_history, away_history):
        rows.update(_history_rows(frame))
    # Bieżący mecz nie może wejść do historii, nawet gdy powtórzy id.
    rows[int(match_id)] = {
        "match_id": int(match_id),
        "home_team": int(home_team_id),
        "away_team": int(away_team_id),
        "game_date": game_date,
        "result": "0"
    }
    return pd.DataFrame(list(rows.values()))


def _history_rows(frame: pd.DataFrame) -> dict[int, dict[str, object]]:
    """Map played matches onto the schedule-feature columns."""
    if frame.empty:
        return {}
    rows: dict[int, dict[str, object]] = {}
    for _, row in frame.iterrows():
        mapped = _history_row(row)
        if mapped is None:
            continue
        rows[int(mapped["match_id"])] = mapped
    return rows


def _history_row(row: pd.Series) -> dict[str, object] | None:
    """Return one completed game, or None when the keys are missing."""
    match_id = _optional_int(row.get("id"))
    home_team = _optional_int(row.get("home_id"))
    away_team = _optional_int(row.get("away_id"))
    if match_id is None or home_team is None or away_team is None:
        return None
    if pd.isna(pd.to_datetime(row.get("game_date"), errors="coerce")):
        return None
    result = row.get("result")
    if result is None or (isinstance(result, float) and pd.isna(result)):
        result = "1"
    return {
        "match_id": match_id,
        "home_team": home_team,
        "away_team": away_team,
        "game_date": row.get("game_date"),
        "result": str(result)
    }


def _side_context(record: pd.Series, side: str) -> dict[str, Any]:
    """Read one club's rest features from a schedule row."""
    rest_days = int(record[f"{side}_rest_days"])
    return {
        "rest_days": rest_days,
        "is_b2b": float(record[f"{side}_is_b2b"]) == 1.0,
        "games_last_7_days": int(record[f"{side}_games_last_7_days"])
    }


def _arenas_frame(arenas: pd.DataFrame) -> pd.DataFrame:
    """Keep the columns the schedule features require."""
    if arenas.empty:
        return pd.DataFrame(columns=_ARENA_COLUMNS)
    return arenas


def _optional_int(value: object) -> int | None:
    """Convert nullable numeric values to integers."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return int(value)
