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


def _resolve_hockey_result(
    is_home: bool,
    home_goals: int,
    away_goals: int,
    ot_winner: int,
    so_winner: int,
    has_ot: bool,
    has_so: bool) -> HockeyResult:
    """Map one team perspective to W/WPD/L/PPD result codes."""
    if home_goals > away_goals:
        if is_home:
            return "WPD" if (has_ot or has_so) else "W"
        return "PPD" if (has_ot or has_so) else "L"
    if home_goals < away_goals:
        if is_home:
            return "PPD" if (has_ot or has_so) else "L"
        return "WPD" if (has_ot or has_so) else "W"
    return "D"


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
        team_key = "home" if is_home else "away"
        opponent_key = "away" if is_home else "home"
        home_goals = int(row["home_team_goals"])
        away_goals = int(row["away_team_goals"])
        has_ot = int(row.get("hma_ot") or 0) != 0
        has_so = int(row.get("hma_so") or 0) != 0
        team_goals = home_goals if is_home else away_goals
        opponent_goals = away_goals if is_home else home_goals
        team_sog = row.get("home_team_sog") if is_home else row.get("away_team_sog")
        opponent_sog = row.get("away_team_sog") if is_home else row.get("home_team_sog")

        history.append({
            "match_id": int(row["id"]),
            "match_date": _to_date_label(row["game_date"]),
            "opponent_shortcut": str(row[f"{opponent_key}_shortcut"] or ""),
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
                int(row.get("hma_ot_winner") or 0),
                int(row.get("hma_so_winner") or 0),
                has_ot,
                has_so),
            "home_team_name": str(row["home_name"]),
            "away_team_name": str(row["away_name"]),
            "home_goals": home_goals,
            "away_goals": away_goals
        })
    return history
