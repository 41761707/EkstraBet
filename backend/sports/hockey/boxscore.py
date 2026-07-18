"""Map hockey match player stats for boxscore display."""

from __future__ import annotations

from typing import Any

import pandas as pd


def _optional_int(value: object) -> int | None:
    """Convert nullable non-negative stat values to integers."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    numeric = int(value)
    if numeric < 0:
        return None
    return numeric


def _signed_int(value: object) -> int | None:
    """Convert nullable numeric values to integers, keeping negatives."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return int(value)


def _optional_float(value: object) -> float | None:
    """Convert nullable numeric values to floats."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return float(value)


def _optional_str(value: object) -> str | None:
    """Convert nullable values to strings."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text or None


def _map_goalie_row(row: pd.Series) -> dict[str, Any]:
    """Map one goalie boxscore row."""
    saves_accuracy = _optional_float(row.get("saves_acc"))
    return {
        "player_id": int(row["player_id"]),
        "player_name": str(row["player_name"]),
        "team_id": int(row["team_id"]),
        "team_name": str(row["team_name"]),
        "points": _optional_int(row.get("points")),
        "penalty_minutes": _optional_int(row.get("penalty_minutes")),
        "time_on_ice": _optional_str(row.get("toi")),
        "shots_against": _optional_int(row.get("shots_against")),
        "shots_saved": _optional_int(row.get("shots_saved")),
        "saves_accuracy": (
            round(saves_accuracy, 2)
            if saves_accuracy is not None else None)
    }


def _map_skater_row(row: pd.Series) -> dict[str, Any]:
    """Map one skater boxscore row."""
    return {
        "player_id": int(row["player_id"]),
        "player_name": str(row["player_name"]),
        "team_id": int(row["team_id"]),
        "team_name": str(row["team_name"]),
        "goals": _optional_int(row.get("goals")),
        "assists": _optional_int(row.get("assists")),
        "points": _optional_int(row.get("points")),
        "plus_minus": _signed_int(row.get("plus_minus")),
        "penalty_minutes": _optional_int(row.get("penalty_minutes")),
        "shots_on_goal": _optional_int(row.get("sog")),
        "time_on_ice": _optional_str(row.get("toi"))
    }


def map_hockey_boxscore(
    goalies_frame: pd.DataFrame,
    skaters_frame: pd.DataFrame) -> dict[str, Any]:
    """Return goalie and skater boxscore rows for one match."""
    return {
        "goalies": [
            _map_goalie_row(row)
            for _, row in goalies_frame.iterrows()
        ],
        "skaters": [
            _map_skater_row(row)
            for _, row in skaters_frame.iterrows()
        ]
    }
