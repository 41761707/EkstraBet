"""Business logic for match schedule and detail endpoints."""

from __future__ import annotations
from datetime import date, datetime
from typing import Any
import pandas as pd
from backend.repositories import league_repository, match_repository


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


def _map_team(row: pd.Series, prefix: str) -> dict[str, Any]:
    """Map home or away team columns from a match row."""
    shortcut = row.get(f"{prefix}_shortcut")
    return {
        "id": int(row[f"{prefix}_id"]),
        "name": str(row[f"{prefix}_name"]),
        "shortcut": str(shortcut) if pd.notna(shortcut) else None
    }


def _is_played(result: object) -> bool:
    """Return True when the match has a recorded result."""
    if result is None or (isinstance(result, float) and pd.isna(result)):
        return False
    return str(result) != "0"


def _map_match_summary_row(row: pd.Series) -> dict[str, Any]:
    """Map a match dataframe row to a MatchSummary dictionary."""
    game_date = _to_datetime(row["game_date"])
    if game_date is None:
        raise ValueError("Match row is missing game_date")
    result = str(row["result"]) if pd.notna(row["result"]) else "0"
    return {
        "id": int(row["id"]),
        "league_id": int(row["league_id"]),
        "season_id": int(row["season_id"]),
        "round": _optional_int(row.get("round")),
        "game_date": game_date,
        "home_team": _map_team(row, "home"),
        "away_team": _map_team(row, "away"),
        "home_goals": _optional_int(row.get("home_team_goals")),
        "away_goals": _optional_int(row.get("away_team_goals")),
        "result": result,
        "is_played": _is_played(result)
    }


def _has_basic_stats(row: pd.Series) -> bool:
    """Return True when at least one stat column is populated."""
    stat_columns = [
        "home_team_xg",
        "away_team_xg",
        "home_team_bp",
        "away_team_bp",
        "home_team_sc",
        "away_team_sc"]
    return any(pd.notna(row.get(column)) for column in stat_columns)


def _map_basic_stats(row: pd.Series) -> dict[str, Any] | None:
    """Map in-match statistics from a match row."""
    if not _has_basic_stats(row):
        return None
    return {
        "home_xg": _optional_float(row.get("home_team_xg")),
        "away_xg": _optional_float(row.get("away_team_xg")),
        "home_possession": _optional_int(row.get("home_team_bp")),
        "away_possession": _optional_int(row.get("away_team_bp")),
        "home_shots": _optional_int(row.get("home_team_sc")),
        "away_shots": _optional_int(row.get("away_team_sc")),
        "home_shots_on_goal": _optional_int(row.get("home_team_sog")),
        "away_shots_on_goal": _optional_int(row.get("away_team_sog")),
        "home_corners": _optional_int(row.get("home_team_ck")),
        "away_corners": _optional_int(row.get("away_team_ck")),
        "home_fouls": _optional_int(row.get("home_team_fouls")),
        "away_fouls": _optional_int(row.get("away_team_fouls")),
        "home_yellow_cards": _optional_int(row.get("home_team_yc")),
        "away_yellow_cards": _optional_int(row.get("away_team_yc")),
        "home_red_cards": _optional_int(row.get("home_team_rc")),
        "away_red_cards": _optional_int(row.get("away_team_rc"))
    }


def get_league_matches(
    league_id: int,
    season_id: int,
    round_num: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None) -> list[dict[str, Any]] | None:
    """Return league matches or None when the league does not exist."""
    if not league_repository.league_exists(league_id):
        return None
    frame = match_repository.fetch_league_matches(
        league_id=league_id,
        season_id=season_id,
        round_num=round_num,
        date_from=date_from,
        date_to=date_to)
    if frame.empty:
        return []
    return [
        _map_match_summary_row(row)
        for _, row in frame.iterrows()
    ]


def get_match_details(
    match_id: int,
    model_ids: list[int] | None = None) -> dict[str, Any] | None:
    """Return match details or None when the match does not exist."""
    frame = match_repository.fetch_match_by_id(match_id)
    if frame.empty:
        return None

    row = frame.iloc[0]
    summary = _map_match_summary_row(row)
    predictions_frame = match_repository.fetch_match_final_predictions(
        match_id,
        model_ids=model_ids)
    odds_frame = match_repository.fetch_match_odds(match_id)

    final_predictions: list[dict[str, Any]] = []
    for _, prediction_row in predictions_frame.iterrows():
        outcome = prediction_row.get("outcome")
        final_predictions.append({
            "event_id": int(prediction_row["event_id"]),
            "event_name": str(prediction_row["event_name"]),
            "model_id": int(prediction_row["model_id"]),
            "outcome": (
                int(outcome)
                if outcome is not None and pd.notna(outcome) else None)
        })

    odds: list[dict[str, Any]] = []
    for _, odds_row in odds_frame.iterrows():
        odds.append({
            "bookmaker": str(odds_row["bookmaker"]),
            "event": str(odds_row["event"]),
            "odds": float(odds_row["odds"])
        })

    return {
        **summary,
        "final_predictions": final_predictions,
        "odds": odds,
        "stats": _map_basic_stats(row)
    }
