"""Helpers for mapping cup knockout score resolution metadata."""

from __future__ import annotations

from typing import Any

import pandas as pd


def _optional_int(value: object) -> int | None:
    """Convert nullable numeric values to integers."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return int(value)


def _flag_int(value: object) -> int:
    """Convert nullable numeric values to integer flags."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0
    return int(value)


def _winner_side(
    has_shootout: bool,
    ot_winner: int,
    so_winner: int) -> int:
    """Return 1 or 2 for the team that won overtime or the shootout."""
    if has_shootout:
        if so_winner in (1, 2):
            return so_winner
        return 0
    if ot_winner in (1, 2):
        return ot_winner
    return 0


def _score_with_deciding_goal(
    home_goals: int | None,
    away_goals: int | None,
    winner_side: int) -> tuple[int | None, int | None]:
    """Add one goal for the winner when regulation ended in a tie."""
    if home_goals is None or away_goals is None:
        return home_goals, away_goals
    if home_goals != away_goals or winner_side not in (1, 2):
        return home_goals, away_goals
    if winner_side == 1:
        return home_goals + 1, away_goals
    return home_goals, away_goals + 1


def map_hockey_score_resolution(row: pd.Series) -> dict[str, Any] | None:
    """Map hockey OT/SO metadata from hockey_matches_add."""
    has_ot = _flag_int(row.get("hma_ot")) == 1
    has_so = _flag_int(row.get("hma_so")) == 1
    ot_winner = _flag_int(row.get("hma_ot_winner"))
    so_winner = _flag_int(row.get("hma_so_winner"))

    has_shootout = has_so or so_winner in (1, 2) or ot_winner == 3
    has_overtime_only = (
        (has_ot or ot_winner in (1, 2))
        and not has_shootout)

    if not has_shootout and not has_overtime_only:
        return None

    home_goals = _optional_int(row.get("home_team_goals"))
    away_goals = _optional_int(row.get("away_team_goals"))
    winner_side = _winner_side(has_shootout, ot_winner, so_winner)
    post_home, post_away = _score_with_deciding_goal(
        home_goals,
        away_goals,
        winner_side)

    return {
        "has_extra_time": has_overtime_only,
        "has_penalties": has_shootout,
        "post_ot_home_goals": post_home,
        "post_ot_away_goals": post_away,
        "penalties_home_goals": None,
        "penalties_away_goals": None,
        "overtime_winner": ot_winner or None,
        "shootout_winner": so_winner or None
    }


def map_score_resolution(row: pd.Series) -> dict[str, Any] | None:
    """Map extra-time and penalty metadata from a joined match row."""
    sport_id = row.get("sport_id")
    if sport_id is not None and not (
            isinstance(sport_id, float) and pd.isna(sport_id)):
        sport = int(sport_id)
        if sport == 2:
            return map_hockey_score_resolution(row)
        if sport == 3:
            # koszykówka: wynik z matches to już FT łącznie z dogrywką
            return None

    overtime_flag = row.get("fsr_ot")
    if overtime_flag is None or (
            isinstance(overtime_flag, float) and pd.isna(overtime_flag)):
        return None

    penalties_flag = row.get("fsr_pen")
    has_penalties = (
        penalties_flag is not None
        and not (isinstance(penalties_flag, float) and pd.isna(penalties_flag))
        and int(penalties_flag) == 1)
    has_extra_time = int(overtime_flag) == 1
    if not has_extra_time and not has_penalties:
        return None

    return {
        "has_extra_time": has_extra_time,
        "has_penalties": has_penalties,
        "post_ot_home_goals": _optional_int(
            row.get("fsr_post_ot_home_goals")),
        "post_ot_away_goals": _optional_int(
            row.get("fsr_post_ot_away_goals")),
        "penalties_home_goals": (
            _optional_int(row.get("fsr_penalties_home_goals"))
            if has_penalties else None),
        "penalties_away_goals": (
            _optional_int(row.get("fsr_penalties_away_goals"))
            if has_penalties else None)
    }
