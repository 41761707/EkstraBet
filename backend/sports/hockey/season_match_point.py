"""Hockey-specific team season match point mapping."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

import pandas as pd

HockeyFormResult = Literal["W", "D", "L", "WPD", "PPD"]


def _to_datetime(value: object) -> datetime | date | None:
    """Convert database datetime values to plain dates or datetimes."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return value
    if isinstance(value, pd.Timestamp):
        if value.hour == 0 and value.minute == 0 and value.second == 0:
            return value.date()
        return value.to_pydatetime()
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    if parsed.hour == 0 and parsed.minute == 0 and parsed.second == 0:
        return parsed.date()
    return parsed.to_pydatetime()


def _stat_int(value: object) -> int:
    """Convert nullable numeric values to integers, defaulting to zero."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0
    return int(value)


def _team_stat(
    row: pd.Series,
    team_id: int,
    home_key: str,
    away_key: str) -> int:
    """Return a match stat from the profiled team's perspective."""
    is_home = int(row["home_id"]) == team_id
    if is_home:
        return _stat_int(row.get(home_key))
    return _stat_int(row.get(away_key))


def _opponent_stat(
    row: pd.Series,
    team_id: int,
    home_key: str,
    away_key: str) -> int:
    """Return a match stat from the opponent's perspective."""
    is_home = int(row["home_id"]) == team_id
    if is_home:
        return _stat_int(row.get(away_key))
    return _stat_int(row.get(home_key))


def resolve_hockey_form_result(
    team_id: int,
    row: pd.Series) -> HockeyFormResult:
    """Return W/WPD/L/PPD from the perspective of the given team."""
    is_home = int(row["home_id"]) == team_id
    home_goals = int(row["home_team_goals"])
    away_goals = int(row["away_team_goals"])
    has_ot = int(row.get("hma_ot") or 0) != 0
    has_so = int(row.get("hma_so") or 0) != 0
    overtime = has_ot or has_so

    if home_goals > away_goals:
        if is_home:
            return "WPD" if overtime else "W"
        return "PPD" if overtime else "L"
    if home_goals < away_goals:
        if is_home:
            return "PPD" if overtime else "L"
        return "WPD" if overtime else "W"
    return "D"


def map_hockey_season_match_point(
    team_id: int,
    row: pd.Series,
    first_period_goals: int | None = None) -> dict[str, Any]:
    """Map a hockey match row to a chart-friendly season match point."""
    is_home = int(row["home_id"]) == team_id
    home_goals = int(row["home_team_goals"])
    away_goals = int(row["away_team_goals"])
    if is_home:
        opponent_shortcut = row.get("away_shortcut")
        opponent_name = str(row["away_name"])
    else:
        opponent_shortcut = row.get("home_shortcut")
        opponent_name = str(row["home_name"])
    game_date = _to_datetime(row["game_date"])
    if game_date is None:
        raise ValueError("Match row is missing game_date")
    shortcut = (
        str(opponent_shortcut)
        if pd.notna(opponent_shortcut) else opponent_name[:3].upper())
    team_shots = _team_stat(row, team_id, "home_team_sc", "away_team_sc")
    opponent_shots = _opponent_stat(row, team_id, "home_team_sc", "away_team_sc")
    team_sog = _team_stat(row, team_id, "home_team_sog", "away_team_sog")
    opponent_sog = _opponent_stat(row, team_id, "home_team_sog", "away_team_sog")
    team_penalty_minutes = _team_stat(row, team_id, "home_team_fk", "away_team_fk")
    opponent_penalty_minutes = _opponent_stat(
        row, team_id, "home_team_fk", "away_team_fk")
    team_penalties = _team_stat(row, team_id, "home_team_fouls", "away_team_fouls")
    opponent_penalties = _opponent_stat(
        row, team_id, "home_team_fouls", "away_team_fouls")

    return {
        "match_id": int(row["id"]),
        "match_date": game_date,
        "opponent_shortcut": shortcut,
        "opponent_name": opponent_name,
        "total_goals": home_goals + away_goals,
        "btts": home_goals > 0 and away_goals > 0,
        "result": resolve_hockey_form_result(team_id, row),
        "home_team_name": str(row["home_name"]),
        "away_team_name": str(row["away_name"]),
        "home_goals": home_goals,
        "away_goals": away_goals,
        "is_home": is_home,
        "team_cards": 0,
        "opponent_cards": 0,
        "total_cards": 0,
        "team_offsides": 0,
        "opponent_offsides": 0,
        "total_offsides": 0,
        "team_corners": 0,
        "opponent_corners": 0,
        "total_corners": 0,
        "team_shots": team_shots,
        "opponent_shots": opponent_shots,
        "total_shots": team_shots + opponent_shots,
        "team_shots_on_target": team_sog,
        "opponent_shots_on_target": opponent_sog,
        "total_shots_on_target": team_sog + opponent_sog,
        "team_fouls": 0,
        "opponent_fouls": 0,
        "total_fouls": 0,
        "team_penalty_minutes": team_penalty_minutes,
        "opponent_penalty_minutes": opponent_penalty_minutes,
        "total_penalty_minutes": team_penalty_minutes + opponent_penalty_minutes,
        "team_penalties": team_penalties,
        "opponent_penalties": opponent_penalties,
        "total_penalties": team_penalties + opponent_penalties,
        "first_period_goals": first_period_goals
    }
