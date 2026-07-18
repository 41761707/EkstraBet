"""Business logic for match schedule and detail endpoints."""

from __future__ import annotations
from datetime import date, datetime
from typing import Any
import pandas as pd
from backend.repositories import league_repository, match_repository
from backend.repositories.sport_league_repository import HOCKEY_SPORT_ID
from backend.services import odds_service, prediction_service
from backend.services.match_score import map_score_resolution
from backend.services.round_label import resolve_round_label
from backend.sports.hockey.boxscore import map_hockey_boxscore
from backend.sports.hockey.first_period_goals import fetch_first_period_goals
from backend.sports.hockey.match_stats import map_hockey_match_stats
from backend.sports.hockey.season_match_point import map_hockey_season_match_point
from backend.services.team_service import (
    _build_head_to_head_summary,
    _map_season_match_point)


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


def _map_match_summary_row(
    row: pd.Series,
    special_rounds: dict[int, str]) -> dict[str, Any]:
    """Map a match dataframe row to a MatchSummary dictionary."""
    game_date = _to_datetime(row["game_date"])
    if game_date is None:
        raise ValueError("Match row is missing game_date")
    result = str(row["result"]) if pd.notna(row["result"]) else "0"
    round_number = _optional_int(row.get("round"))
    return {
        "id": int(row["id"]),
        "league_id": int(row["league_id"]),
        "season_id": int(row["season_id"]),
        "round": round_number,
        "round_label": resolve_round_label(round_number, special_rounds),
        "game_date": game_date,
        "home_team": _map_team(row, "home"),
        "away_team": _map_team(row, "away"),
        "home_goals": _optional_int(row.get("home_team_goals")),
        "away_goals": _optional_int(row.get("away_team_goals")),
        "result": result,
        "is_played": _is_played(result),
        "score_resolution": map_score_resolution(row)
    }


def _has_basic_stats(row: pd.Series) -> bool:
    """Return True when at least one stat column is populated."""
    stat_columns = [
        "home_team_goals",
        "away_team_goals",
        "home_team_xg",
        "away_team_xg",
        "home_team_bp",
        "away_team_bp",
        "home_team_sc",
        "away_team_sc"]
    return any(pd.notna(row.get(column)) for column in stat_columns)


def _map_player_stat_value(value: object) -> int | None:
    """Map nullable player stat values, treating -1 as missing."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    numeric = int(value)
    if numeric < 0:
        return None
    return numeric


def _map_player_stat_row(row: pd.Series) -> dict[str, Any]:
    """Map a football player stats row for match boxscore."""
    return {
        "player_id": int(row["player_id"]),
        "player_name": str(row["player_name"]),
        "team_id": int(row["team_id"]),
        "team_name": str(row["team_name"]),
        "goals": _map_player_stat_value(row.get("goals")),
        "assists": _map_player_stat_value(row.get("assists")),
        "red_cards": _map_player_stat_value(row.get("red_cards")),
        "yellow_cards": _map_player_stat_value(row.get("yellow_cards")),
        "corners_won": _map_player_stat_value(row.get("corners_won")),
        "shots": _map_player_stat_value(row.get("shots")),
        "shots_on_target": _map_player_stat_value(row.get("shots_on_target")),
        "blocked_shots": _map_player_stat_value(row.get("blocked_shots")),
        "passes": _map_player_stat_value(row.get("passes")),
        "crosses": _map_player_stat_value(row.get("crosses")),
        "tackles": _map_player_stat_value(row.get("tackles")),
        "offsides": _map_player_stat_value(row.get("offsides")),
        "fouls_conceded": _map_player_stat_value(row.get("fouls_conceded")),
        "fouls_won": _map_player_stat_value(row.get("fouls_won")),
        "saves": _map_player_stat_value(row.get("saves"))
    }


def _map_match_boxscore(match_id: int) -> list[dict[str, Any]] | None:
    """Return player stats for a match or None when unavailable."""
    frame = match_repository.fetch_match_player_stats(match_id)
    if frame.empty:
        return None
    return [
        _map_player_stat_row(row)
        for _, row in frame.iterrows()
    ]


def _map_basic_stats(row: pd.Series) -> dict[str, Any] | None:
    """Map in-match statistics from a match row."""
    if not _has_basic_stats(row):
        return None
    return {
        "home_goals": _optional_int(row.get("home_team_goals")),
        "away_goals": _optional_int(row.get("away_team_goals")),
        "home_xg": _optional_float(row.get("home_team_xg")),
        "away_xg": _optional_float(row.get("away_team_xg")),
        "home_possession": _optional_int(row.get("home_team_bp")),
        "away_possession": _optional_int(row.get("away_team_bp")),
        "home_shots": _optional_int(row.get("home_team_sc")),
        "away_shots": _optional_int(row.get("away_team_sc")),
        "home_shots_on_goal": _optional_int(row.get("home_team_sog")),
        "away_shots_on_goal": _optional_int(row.get("away_team_sog")),
        "home_free_kicks": _optional_int(row.get("home_team_fk")),
        "away_free_kicks": _optional_int(row.get("away_team_fk")),
        "home_corners": _optional_int(row.get("home_team_ck")),
        "away_corners": _optional_int(row.get("away_team_ck")),
        "home_offsides": _optional_int(row.get("home_team_off")),
        "away_offsides": _optional_int(row.get("away_team_off")),
        "home_fouls": _optional_int(row.get("home_team_fouls")),
        "away_fouls": _optional_int(row.get("away_team_fouls")),
        "home_yellow_cards": _optional_int(row.get("home_team_yc")),
        "away_yellow_cards": _optional_int(row.get("away_team_yc")),
        "home_red_cards": _optional_int(row.get("home_team_rc")),
        "away_red_cards": _optional_int(row.get("away_team_rc"))
    }


def _league_has_player_stats(league_id: int) -> bool:
    """Return True when the league exposes football player stats."""
    frame = league_repository.fetch_league_by_id(league_id)
    if frame.empty:
        return False
    value = frame.iloc[0].get("has_player_stats")
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return False
    return bool(int(value))


def _map_team_history(
    team_id: int,
    matches_frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Map played matches to chart-friendly history points."""
    if matches_frame.empty:
        return []

    sport_id = matches_frame.iloc[0].get("sport_id")
    is_hockey = (
        sport_id is not None
        and not (isinstance(sport_id, float) and pd.isna(sport_id))
        and int(sport_id) == HOCKEY_SPORT_ID)
    first_period_map: dict[int, int] = {}
    if is_hockey:
        match_ids = [int(row["id"]) for _, row in matches_frame.iterrows()]
        first_period_map = fetch_first_period_goals(match_ids)

    history: list[dict[str, Any]] = []
    for _, row in matches_frame.iterrows():
        if is_hockey:
            history.append(map_hockey_season_match_point(
                team_id,
                row,
                first_period_goals=first_period_map.get(int(row["id"]))))
        else:
            history.append(_map_season_match_point(team_id, row))
    return history


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
    special_rounds = league_repository.fetch_special_round_names()
    return [
        _map_match_summary_row(row, special_rounds)
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
    special_rounds = league_repository.fetch_special_round_names()
    summary = _map_match_summary_row(row, special_rounds)
    final_predictions = prediction_service.get_match_final_predictions(
        match_id,
        model_ids=model_ids)
    odds = odds_service.get_match_odds_items(match_id)

    home_team_id = int(row["home_id"])
    away_team_id = int(row["away_id"])
    game_date = row["game_date"]
    has_player_stats = _league_has_player_stats(int(row["league_id"]))

    h2h_frame = match_repository.fetch_head_to_head_for_match(
        home_team_id,
        away_team_id,
        exclude_match_id=match_id)
    head_to_head = _build_head_to_head_summary(
        home_team_id,
        away_team_id,
        h2h_frame,
        special_rounds)

    home_history_frame = match_repository.fetch_team_matches_before_date(
        home_team_id,
        game_date,
        exclude_match_id=match_id)
    away_history_frame = match_repository.fetch_team_matches_before_date(
        away_team_id,
        game_date,
        exclude_match_id=match_id)

    boxscore = None
    hockey_boxscore = None
    if has_player_stats and summary["is_played"]:
        boxscore = _map_match_boxscore(match_id)

    sport_id = _optional_int(row.get("sport_id"))
    hockey_stats = None
    football_stats = None
    if sport_id == HOCKEY_SPORT_ID:
        hockey_stats = map_hockey_match_stats(row)
        if summary["is_played"]:
            goalies_frame, skaters_frame = (
                match_repository.fetch_hockey_match_boxscore(match_id))
            if not goalies_frame.empty or not skaters_frame.empty:
                hockey_boxscore = map_hockey_boxscore(
                    goalies_frame,
                    skaters_frame)
    else:
        football_stats = _map_basic_stats(row)

    has_hockey_boxscore = hockey_boxscore is not None

    return {
        **summary,
        "sport_id": sport_id,
        "final_predictions": final_predictions,
        "odds": odds,
        "stats": football_stats,
        "hockey_stats": hockey_stats,
        "has_player_stats": has_player_stats or has_hockey_boxscore,
        "head_to_head": head_to_head,
        "home_team_history": _map_team_history(
            home_team_id,
            home_history_frame),
        "away_team_history": _map_team_history(
            away_team_id,
            away_history_frame),
        "boxscore": boxscore,
        "hockey_boxscore": hockey_boxscore
    }
