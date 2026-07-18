"""Basketball team match history for league page charts."""

from __future__ import annotations
from datetime import date, datetime
from typing import Any
import pandas as pd


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


def build_basketball_team_history(
    team_id: int,
    matches_frame: pd.DataFrame,
    lookback: int) -> list[dict[str, Any]]:
    """Return recent played matches for one basketball team."""
    if matches_frame.empty:
        return []

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
        team_points = int(row["home_team_goals"] if is_home else row["away_team_goals"])
        opponent_points = int(row["away_team_goals"] if is_home else row["home_team_goals"])
        if team_points > opponent_points:
            result = "W"
        else:
            result = "L"

        history.append({
            "match_id": int(row["id"]),
            "match_date": _to_date_label(row["game_date"]),
            "opponent_shortcut": str(row[f"{opponent_key}_shortcut"] or ""),
            "team_points": team_points,
            "opponent_points": opponent_points,
            "total_points": team_points + opponent_points,
            "result": result,
            "home_team_name": str(row["home_name"]),
            "away_team_name": str(row["away_name"]),
            "home_points": int(row["home_team_goals"]),
            "away_points": int(row["away_team_goals"])
        })
    return history
