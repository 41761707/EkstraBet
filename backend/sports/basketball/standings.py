"""Basketball league table calculations."""

from __future__ import annotations
from typing import Any, Literal
import pandas as pd

Scope = Literal["overall", "home", "away"]


def _empty_row(team_id: int, team_name: str) -> dict[str, Any]:
    """Initialize basketball standings counters for one team."""
    return {
        "team_id": team_id,
        "team_name": team_name,
        "played": 0,
        "wins": 0,
        "losses": 0,
        "points_for": 0,
        "points_against": 0,
        "point_difference": 0,
        "win_percentage": 0.0
    }


def _process_team_match(
    row: dict[str, Any],
    team_points: int,
    opponent_points: int,
    is_overtime: bool) -> None:
    """Update one team's stats after a single game."""
    row["played"] += 1
    row["points_for"] += team_points
    row["points_against"] += opponent_points
    row["point_difference"] = row["points_for"] - row["points_against"]
    if team_points > opponent_points:
        row["wins"] += 1
    else:
        row["losses"] += 1
        if is_overtime:
            pass


def build_basketball_standings(
    teams_frame: pd.DataFrame,
    matches_frame: pd.DataFrame,
    scope: Scope = "overall") -> list[dict[str, Any]]:
    """Build sorted basketball standings for the requested scope."""
    stats: dict[int, dict[str, Any]] = {}
    for _, team_row in teams_frame.iterrows():
        team_id = int(team_row["team_id"])
        stats[team_id] = _empty_row(team_id, str(team_row["team_name"]))

    for _, match_row in matches_frame.iterrows():
        home_id = int(match_row["home_id"])
        away_id = int(match_row["away_id"])
        home_points = int(match_row["home_team_goals"])
        away_points = int(match_row["away_team_goals"])
        is_overtime = int(match_row.get("bma_ot") or 0) == 1

        if scope in ("overall", "home") and home_id in stats:
            _process_team_match(
                stats[home_id],
                home_points,
                away_points,
                is_overtime)
        if scope in ("overall", "away") and away_id in stats:
            _process_team_match(
                stats[away_id],
                away_points,
                home_points,
                is_overtime)

    sorted_rows = sorted(
        stats.values(),
        key=lambda item: (item["wins"], item["point_difference"]),
        reverse=True)
    standings: list[dict[str, Any]] = []
    for position, row in enumerate(sorted_rows, start=1):
        played = row["played"]
        win_pct = round(row["wins"] * 100 / played, 1) if played > 0 else 0.0
        standings.append({
            "position": position,
            **row,
            "win_percentage": win_pct
        })
    return standings
