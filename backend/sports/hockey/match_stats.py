"""Map hockey match statistics from matches and hockey_matches_add rows."""

from __future__ import annotations

from typing import Any

import pandas as pd


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


def map_hockey_match_stats(row: pd.Series) -> dict[str, Any] | None:
    """Map hockey in-match statistics from a joined match row."""
    home_goals = _optional_int(row.get("home_team_goals"))
    away_goals = _optional_int(row.get("away_team_goals"))
    home_sog = _optional_int(row.get("home_team_sog"))
    away_sog = _optional_int(row.get("away_team_sog"))
    if home_goals is None and away_goals is None and home_sog is None:
        return None

    return {
        "home_goals": home_goals,
        "away_goals": away_goals,
        "home_shots_on_goal": home_sog,
        "away_shots_on_goal": away_sog,
        "home_penalty_minutes": _optional_int(row.get("home_team_fk")),
        "away_penalty_minutes": _optional_int(row.get("away_team_fk")),
        "home_penalties": _optional_int(row.get("home_team_fouls")),
        "away_penalties": _optional_int(row.get("away_team_fouls")),
        "home_pp_goals": _optional_int(row.get("home_team_pp_goals")),
        "away_pp_goals": _optional_int(row.get("away_team_pp_goals")),
        "home_sh_goals": _optional_int(row.get("home_team_sh_goals")),
        "away_sh_goals": _optional_int(row.get("away_team_sh_goals")),
        "home_shots_accuracy": _optional_float(row.get("home_team_shots_acc")),
        "away_shots_accuracy": _optional_float(row.get("away_team_shots_acc")),
        "home_saves": _optional_int(row.get("home_team_saves")),
        "away_saves": _optional_int(row.get("away_team_saves")),
        "home_saves_accuracy": _optional_float(row.get("home_team_saves_acc")),
        "away_saves_accuracy": _optional_float(row.get("away_team_saves_acc")),
        "home_pp_accuracy": _optional_float(row.get("home_team_pp_acc")),
        "away_pp_accuracy": _optional_float(row.get("away_team_pp_acc")),
        "home_pk_accuracy": _optional_float(row.get("home_team_pk_acc")),
        "away_pk_accuracy": _optional_float(row.get("away_team_pk_acc")),
        "home_faceoffs_won": _optional_int(row.get("home_team_faceoffs")),
        "away_faceoffs_won": _optional_int(row.get("away_team_faceoffs")),
        "home_faceoffs_accuracy": _optional_float(
            row.get("home_team_faceoffs_acc")),
        "away_faceoffs_accuracy": _optional_float(
            row.get("away_team_faceoffs_acc")),
        "home_hits": _optional_int(row.get("home_team_hits")),
        "away_hits": _optional_int(row.get("away_team_hits")),
        "home_turnovers": _optional_int(row.get("home_team_to")),
        "away_turnovers": _optional_int(row.get("away_team_to")),
        "home_empty_net_goals": _optional_int(row.get("home_team_en")),
        "away_empty_net_goals": _optional_int(row.get("away_team_en"))
    }
