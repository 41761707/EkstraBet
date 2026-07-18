"""Hockey league table calculations."""

from __future__ import annotations
from typing import Any, Literal
import pandas as pd

Scope = Literal["overall", "home", "away"]
WINNER_GAIN = 2
DRAW_GAIN = 1
OT_WINNER_GAIN = 1
OT_LOSER_GAIN = 1


def _empty_row(team_id: int, team_name: str) -> dict[str, Any]:
    """Initialize hockey standings counters for one team."""
    return {
        "team_id": team_id,
        "team_name": team_name,
        "played": 0,
        "wins": 0,
        "losses": 0,
        "goals_for": 0,
        "goals_against": 0,
        "goal_difference": 0,
        "points": 0,
        "overtime_wins": 0,
        "overtime_losses": 0
    }


def _update_team(
    row: dict[str, Any],
    goals_for: int,
    goals_against: int,
    won: bool,
    lost: bool,
    ot_win: bool = False,
    ot_loss: bool = False) -> None:
    """Apply one side of a match to team standings."""
    row["played"] += 1
    row["goals_for"] += goals_for
    row["goals_against"] += goals_against
    if won:
        row["wins"] += 1
        row["points"] += WINNER_GAIN
    if lost:
        row["losses"] += 1
    if ot_win:
        row["overtime_wins"] += 1
        row["points"] += OT_WINNER_GAIN
        row["goals_for"] += 1
    if ot_loss:
        row["overtime_losses"] += 1
        row["points"] += OT_LOSER_GAIN
        row["goals_against"] += 1
    row["goal_difference"] = row["goals_for"] - row["goals_against"]


def _process_match(
    stats: dict[int, dict[str, Any]],
    match_row: pd.Series,
    scope: Scope) -> None:
    """Update standings from a single hockey match row."""
    home_id = int(match_row["home_id"])
    away_id = int(match_row["away_id"])
    home_goals = int(match_row["home_team_goals"])
    away_goals = int(match_row["away_team_goals"])
    ot_winner = int(match_row.get("hma_ot_winner") or 0)
    so_winner = int(match_row.get("hma_so_winner") or 0)
    process_home = scope in ("overall", "home")
    process_away = scope in ("overall", "away")

    if home_goals > away_goals:
        if process_home:
            _update_team(
                stats[home_id], home_goals, away_goals, True, False)
        if process_away:
            _update_team(
                stats[away_id], away_goals, home_goals, False, True)
    elif home_goals < away_goals:
        if process_home:
            _update_team(
                stats[home_id], home_goals, away_goals, False, True)
        if process_away:
            _update_team(
                stats[away_id], away_goals, home_goals, True, False)
    else:
        if process_home:
            row = stats[home_id]
            row["played"] += 1
            row["goals_for"] += home_goals
            row["goals_against"] += away_goals
            row["points"] += DRAW_GAIN
        if process_away:
            row = stats[away_id]
            row["played"] += 1
            row["goals_for"] += away_goals
            row["goals_against"] += home_goals
            row["points"] += DRAW_GAIN
        if ot_winner == 1 or so_winner == 1:
            if process_home:
                _update_team(
                    stats[home_id], 0, 0, False, False, True, False)
            if process_away:
                _update_team(
                    stats[away_id], 0, 0, False, False, False, True)
        elif ot_winner == 2 or so_winner == 2:
            if process_home:
                _update_team(
                    stats[home_id], 0, 0, False, False, False, True)
            if process_away:
                _update_team(
                    stats[away_id], 0, 0, False, False, True, False)


def build_hockey_standings(
    teams_frame: pd.DataFrame,
    matches_frame: pd.DataFrame,
    scope: Scope = "overall") -> list[dict[str, Any]]:
    """Build sorted hockey standings for the requested scope."""
    stats: dict[int, dict[str, Any]] = {}
    for _, team_row in teams_frame.iterrows():
        team_id = int(team_row["team_id"])
        stats[team_id] = _empty_row(team_id, str(team_row["team_name"]))

    for _, match_row in matches_frame.iterrows():
        _process_match(stats, match_row, scope)

    sorted_rows = sorted(
        stats.values(),
        key=lambda item: (item["points"], item["goal_difference"]),
        reverse=True)
    standings: list[dict[str, Any]] = []
    for position, row in enumerate(sorted_rows, start=1):
        standings.append({"position": position, **row})
    return standings
