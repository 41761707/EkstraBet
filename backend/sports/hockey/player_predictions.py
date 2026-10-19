"""Map stored hockey player props into home and away lists."""

from __future__ import annotations

from typing import Any

import pandas as pd


HOCKEY_PLAYER_PROPS_MODEL_NAME = "HOCKEY_PLAYER_PROPS_V1"


def map_hockey_player_predictions(
    frame: pd.DataFrame,
    home_team_id: int,
    away_team_id: int) -> dict[str, Any] | None:
    """Group prop lines by club and player, or None when empty."""
    if frame.empty:
        return None
    return {
        "home": _team_players(frame, home_team_id),
        "away": _team_players(frame, away_team_id)
    }


def _team_players(
    frame: pd.DataFrame,
    team_id: int) -> list[dict[str, Any]]:
    """Collect one entry per skater, preserving query order."""
    players: list[dict[str, Any]] = []
    index: dict[int, dict[str, Any]] = {}
    for _, row in frame.iterrows():
        row_team_id = _optional_int(row.get("team_id"))
        if row_team_id != team_id:
            continue
        player_id = _optional_int(row.get("player_id"))
        if player_id is None:
            continue
        bucket = index.get(player_id)
        if bucket is None:
            bucket = {
                "player_id": player_id,
                "player_name": str(row["player_name"]),
                "team_id": team_id,
                "lines": []
            }
            index[player_id] = bucket
            players.append(bucket)
        line = _prediction_line(row)
        if line is not None:
            bucket["lines"].append(line)
    return players


def _prediction_line(row: pd.Series) -> dict[str, Any] | None:
    """Return one prop line, or None when the numbers are missing."""
    event_id = _optional_int(row.get("event_id"))
    line = _optional_float(row.get("line"))
    expected_value = _optional_float(row.get("expected_value"))
    probability = _optional_float(row.get("probability"))
    if (
            event_id is None
            or line is None
            or expected_value is None
            or probability is None):
        return None
    return {
        "event_id": event_id,
        "line": line,
        "expected_value": expected_value,
        "probability": probability
    }


def _optional_int(value: object) -> int | None:
    """Convert nullable numeric values to integers."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return int(value)


def _optional_float(value: object) -> float | None:
    """Convert nullable numeric values to floats."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return float(value)
