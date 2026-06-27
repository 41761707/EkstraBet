"""Business logic for league standings calculation."""

from __future__ import annotations
from typing import Any, Literal
import pandas as pd
from backend.repositories import league_repository, standings_repository

StandingScope = Literal["overall", "home", "away", "ou_btts"]


def _empty_stats_row(team_id: int, team_name: str) -> dict[str, Any]:
    """Initialize a traditional standings row for a team."""
    return {
        "team_id": team_id,
        "team_name": team_name,
        "played": 0,
        "wins": 0,
        "draws": 0,
        "losses": 0,
        "goals_for": 0,
        "goals_against": 0,
        "goal_difference": 0,
        "points": 0
    }


def _empty_ou_btts_row(team_id: int, team_name: str) -> dict[str, Any]:
    """Initialize an OU/BTTS standings row for a team."""
    return {
        "team_id": team_id,
        "team_name": team_name,
        "played": 0,
        "btts_count": 0,
        "btts_percentage": 0.0,
        "over_1_5_count": 0,
        "over_1_5_percentage": 0.0,
        "over_2_5_count": 0,
        "over_2_5_percentage": 0.0,
        "over_3_5_count": 0,
        "over_3_5_percentage": 0.0
    }


def _apply_match_result(
    stats: dict[int, dict[str, Any]],
    team_id: int,
    outcome: int,
    goals_for: int,
    goals_against: int) -> None:
    """Update traditional stats for one team after a match."""
    row = stats[team_id]
    row["played"] += 1
    row["goals_for"] += goals_for
    row["goals_against"] += goals_against
    if outcome == 0:
        row["wins"] += 1
        row["points"] += 3
    elif outcome == 1:
        row["draws"] += 1
        row["points"] += 1
    else:
        row["losses"] += 1
    row["goal_difference"] = row["goals_for"] - row["goals_against"]


def _process_traditional_match(
    stats: dict[int, dict[str, Any]],
    row: pd.Series,
    scope: Literal["overall", "home", "away"]) -> None:
    """Apply one match row to traditional standings for the given scope."""
    home_id = int(row["home_team_id"])
    away_id = int(row["away_team_id"])
    home_goals = int(row["home_team_goals"])
    away_goals = int(row["away_team_goals"])
    result = str(row["result"])

    if result == "1":
        if scope in ("overall", "home"):
            _apply_match_result(stats, home_id, 0, home_goals, away_goals)
        if scope in ("overall", "away"):
            _apply_match_result(stats, away_id, 2, away_goals, home_goals)
    elif result == "X":
        if scope in ("overall", "home"):
            _apply_match_result(stats, home_id, 1, home_goals, away_goals)
        if scope in ("overall", "away"):
            _apply_match_result(stats, away_id, 1, away_goals, home_goals)
    elif result == "2":
        if scope in ("overall", "home"):
            _apply_match_result(stats, home_id, 2, home_goals, away_goals)
        if scope in ("overall", "away"):
            _apply_match_result(stats, away_id, 0, away_goals, home_goals)


def _build_traditional_standings(
    teams_frame: pd.DataFrame,
    results_frame: pd.DataFrame,
    scope: Literal["overall", "home", "away"]) -> list[dict[str, Any]]:
    """Build sorted traditional standings for the requested scope."""
    stats: dict[int, dict[str, Any]] = {}
    for _, team_row in teams_frame.iterrows():
        team_id = int(team_row["team_id"])
        stats[team_id] = _empty_stats_row(team_id, str(team_row["team_name"]))

    for _, match_row in results_frame.iterrows():
        _process_traditional_match(stats, match_row, scope)

    sorted_rows = sorted(
        stats.values(),
        key=lambda item: (item["points"], item["goal_difference"]),
        reverse=True)
    standings: list[dict[str, Any]] = []
    for position, row in enumerate(sorted_rows, start=1):
        standings.append({"position": position, **row})
    return standings


def _percentage(count: int, played: int) -> float:
    """Return a percentage rounded to two decimal places."""
    if played <= 0:
        return 0.0
    return round(count * 100 / played, 2)


def _build_ou_btts_standings(
    teams_frame: pd.DataFrame,
    results_frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Build OU/BTTS standings sorted alphabetically by team name."""
    stats: dict[int, dict[str, Any]] = {}
    for _, team_row in teams_frame.iterrows():
        team_id = int(team_row["team_id"])
        stats[team_id] = _empty_ou_btts_row(team_id, str(team_row["team_name"]))

    for _, row in results_frame.iterrows():
        home_id = int(row["home_team_id"])
        away_id = int(row["away_team_id"])
        home_goals = int(row["home_team_goals"])
        away_goals = int(row["away_team_goals"])
        total_goals = home_goals + away_goals
        btts = home_goals > 0 and away_goals > 0

        for team_id in (home_id, away_id):
            team_stats = stats[team_id]
            team_stats["played"] += 1
            if btts:
                team_stats["btts_count"] += 1
            if total_goals > 1:
                team_stats["over_1_5_count"] += 1
            if total_goals > 2:
                team_stats["over_2_5_count"] += 1
            if total_goals > 3:
                team_stats["over_3_5_count"] += 1

    sorted_rows = sorted(
        stats.values(),
        key=lambda item: item["team_name"])
    standings: list[dict[str, Any]] = []
    for position, row in enumerate(sorted_rows, start=1):
        played = row["played"]
        standings.append({
            "position": position,
            "team_id": row["team_id"],
            "team_name": row["team_name"],
            "played": played,
            "btts_count": row["btts_count"],
            "btts_percentage": _percentage(row["btts_count"], played),
            "over_1_5_count": row["over_1_5_count"],
            "over_1_5_percentage": _percentage(
                row["over_1_5_count"],
                played),
            "over_2_5_count": row["over_2_5_count"],
            "over_2_5_percentage": _percentage(
                row["over_2_5_count"],
                played),
            "over_3_5_count": row["over_3_5_count"],
            "over_3_5_percentage": _percentage(
                row["over_3_5_count"],
                played)
        })
    return standings


def get_league_standings(
    league_id: int,
    season_id: int,
    scope: StandingScope = "overall") -> dict[str, Any] | None:
    """Return league standings or None when the league does not exist."""
    if not league_repository.league_exists(league_id):
        return None

    teams_frame = standings_repository.fetch_teams_in_season(
        league_id,
        season_id)
    results_frame = standings_repository.fetch_league_results(
        league_id,
        season_id)

    if scope == "ou_btts":
        standings = _build_ou_btts_standings(teams_frame, results_frame)
    else:
        standings = _build_traditional_standings(
            teams_frame,
            results_frame,
            scope)

    return {
        "league_id": league_id,
        "season_id": season_id,
        "scope": scope,
        "standings": standings,
        "total_count": len(standings)
    }
