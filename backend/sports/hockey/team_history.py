"""Hockey team match history for league page charts."""

from __future__ import annotations
from datetime import date, datetime
from typing import Any
import pandas as pd

HockeyResult = str


def _to_date_label(value: object) -> str:
    """Format match date for chart labels."""
    if isinstance(value, datetime):
        return value.strftime("%d.%m")
    if isinstance(value, date):
        return value.strftime("%d.%m")
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return ""
    return parsed.strftime("%d.%m")


def _flag_int(value: object) -> int:
    """Convert nullable flags to integers, treating missing values as zero."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0
    if pd.isna(value):
        return 0
    return int(value)


def _extra_time_winner(ot_winner: int, so_winner: int) -> int:
    """Return 1 or 2 when OT or a shootout decided a tied game."""
    if so_winner in (1, 2):
        return so_winner
    if ot_winner in (1, 2):
        return ot_winner
    return 0


def _resolve_hockey_result(
    is_home: bool,
    home_goals: int,
    away_goals: int,
    ot_winner: int,
    so_winner: int) -> HockeyResult:
    """Map one team perspective to W/WPD/D/L/PPD result codes.

    Unequal regulation goals stay W or L. A tie uses the OT or SO winner.
    """
    if home_goals != away_goals:
        home_won = home_goals > away_goals
        team_won = home_won if is_home else not home_won
        return "W" if team_won else "L"
    decider = _extra_time_winner(ot_winner, so_winner)
    if decider == 0:
        return "D"
    home_won = decider == 1
    team_won = home_won if is_home else not home_won
    return "WPD" if team_won else "PPD"


def build_hockey_team_history(
    team_id: int,
    matches_frame: pd.DataFrame,
    lookback: int,
    first_period_goals: dict[int, int] | None = None) -> list[dict[str, Any]]:
    """Return recent played matches for one hockey team."""
    if matches_frame.empty:
        return []

    goals_map = first_period_goals or {}

    team_matches = matches_frame[
        (
            (matches_frame["home_id"] == team_id)
            | (matches_frame["away_id"] == team_id)
        )
        & (matches_frame["result"] != "0")
    ].sort_values("game_date", ascending=False).head(lookback)

    history: list[dict[str, Any]] = []
    for _, row in team_matches.iterrows():
        is_home = int(row["home_id"]) == team_id
        opponent_key = "away" if is_home else "home"
        home_goals = int(row["home_team_goals"])
        away_goals = int(row["away_team_goals"])
        team_goals = home_goals if is_home else away_goals
        opponent_goals = away_goals if is_home else home_goals
        team_sog = row.get("home_team_sog") if is_home else row.get("away_team_sog")
        opponent_sog = row.get("away_team_sog") if is_home else row.get("home_team_sog")

        history.append({
            "match_id": int(row["id"]),
            "match_date": _to_date_label(row["game_date"]),
            "opponent_shortcut": str(row[f"{opponent_key}_shortcut"] or ""),
            "opponent_name": str(row[f"{opponent_key}_name"] or ""),
            "team_goals": team_goals,
            "opponent_goals": opponent_goals,
            "total_goals": team_goals + opponent_goals,
            "first_period_goals": goals_map.get(int(row["id"])),
            "team_shots_on_goal": (
                int(team_sog) if pd.notna(team_sog) else None),
            "opponent_shots_on_goal": (
                int(opponent_sog) if pd.notna(opponent_sog) else None),
            "result": _resolve_hockey_result(
                is_home,
                home_goals,
                away_goals,
                _flag_int(row.get("hma_ot_winner")),
                _flag_int(row.get("hma_so_winner"))),
            "home_team_name": str(row["home_name"]),
            "away_team_name": str(row["away_name"]),
            "home_goals": home_goals,
            "away_goals": away_goals
        })
    return history
