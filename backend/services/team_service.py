"""Business logic for team profile endpoints."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
import pandas as pd
from backend.repositories import league_repository, team_repository
from backend.repositories.sport_league_repository import HOCKEY_SPORT_ID
from backend.services.match_score import map_score_resolution
from backend.services.round_label import resolve_round_label
from backend.sports.hockey.first_period_goals import fetch_first_period_goals
from backend.sports.hockey.season_match_point import (
    map_hockey_season_match_point,
    resolve_hockey_form_result)

FormResult = Literal["W", "D", "L", "WPD", "PPD"]


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


def _stat_int(value: object) -> int:
    """Convert nullable numeric values to integers, defaulting to zero."""
    return _optional_int(value) or 0


def _team_match_stat(
    row: pd.Series,
    team_id: int,
    home_key: str,
    away_key: str) -> int:
    """Return a match stat from the profiled team's perspective."""
    is_home = int(row["home_id"]) == team_id
    if is_home:
        return _stat_int(row.get(home_key))
    return _stat_int(row.get(away_key))


def _opponent_match_stat(
    row: pd.Series,
    team_id: int,
    home_key: str,
    away_key: str) -> int:
    """Return a match stat from the opponent's perspective."""
    is_home = int(row["home_id"]) == team_id
    if is_home:
        return _stat_int(row.get(away_key))
    return _stat_int(row.get(home_key))


def _team_cards(row: pd.Series, team_id: int) -> int:
    """Return yellow and red cards for the profiled team."""
    return (
        _team_match_stat(row, team_id, "home_team_yc", "away_team_yc")
        + _team_match_stat(row, team_id, "home_team_rc", "away_team_rc"))


def _opponent_cards(row: pd.Series, team_id: int) -> int:
    """Return yellow and red cards for the opponent."""
    return (
        _opponent_match_stat(row, team_id, "home_team_yc", "away_team_yc")
        + _opponent_match_stat(row, team_id, "home_team_rc", "away_team_rc"))


def _map_team_summary(row: pd.Series) -> dict[str, Any]:
    """Map a team dataframe row to a TeamSummary dictionary."""
    shortcut = row.get("shortcut")
    return {
        "id": int(row["id"]),
        "name": str(row["name"]),
        "shortcut": str(shortcut) if pd.notna(shortcut) else None,
        "country_id": (
            int(row["country_id"])
            if pd.notna(row["country_id"]) else None),
        "country_name": (
            str(row["country_name"])
            if pd.notna(row["country_name"]) else None),
        "country_emoji": (
            str(row["country_emoji"])
            if pd.notna(row["country_emoji"]) else None),
        "sport_id": (
            int(row["sport_id"])
            if pd.notna(row["sport_id"]) else None),
        "sport_name": (
            str(row["sport_name"])
            if pd.notna(row["sport_name"]) else None)
    }


def _map_match_summary_row(
    row: pd.Series,
    special_rounds: dict[int, str]) -> dict[str, Any]:
    """Map a match dataframe row to a MatchSummary dictionary."""
    game_date = _to_datetime(row["game_date"])
    if game_date is None:
        raise ValueError("Match row is missing game_date")
    result = str(row["result"]) if pd.notna(row["result"]) else "0"
    home_shortcut = row.get("home_shortcut")
    away_shortcut = row.get("away_shortcut")
    round_number = _optional_int(row.get("round"))
    return {
        "id": int(row["id"]),
        "league_id": int(row["league_id"]),
        "season_id": int(row["season_id"]),
        "round": round_number,
        "round_label": resolve_round_label(round_number, special_rounds),
        "game_date": game_date,
        "home_team": {
            "id": int(row["home_id"]),
            "name": str(row["home_name"]),
            "shortcut": (
                str(home_shortcut)
                if pd.notna(home_shortcut) else None)
        },
        "away_team": {
            "id": int(row["away_id"]),
            "name": str(row["away_name"]),
            "shortcut": (
                str(away_shortcut)
                if pd.notna(away_shortcut) else None)
        },
        "home_goals": _optional_int(row.get("home_team_goals")),
        "away_goals": _optional_int(row.get("away_team_goals")),
        "result": result,
        "is_played": result != "0",
        "score_resolution": map_score_resolution(row)
    }


def _match_form_result(team_id: int, row: pd.Series) -> FormResult:
    """Return W/D/L from the perspective of the given team."""
    sport_id = row.get("sport_id")
    if sport_id is not None and not (
            isinstance(sport_id, float) and pd.isna(sport_id)):
        if int(sport_id) == HOCKEY_SPORT_ID:
            return resolve_hockey_form_result(team_id, row)

    result = str(row["result"])
    is_home = int(row["home_id"]) == team_id
    if result == "X":
        return "D"
    if is_home:
        return "W" if result == "1" else "L"
    return "W" if result == "2" else "L"


def _empty_split_stats() -> dict[str, Any]:
    """Initialize empty home/away/overall split statistics."""
    return {
        "played": 0,
        "wins": 0,
        "draws": 0,
        "losses": 0,
        "goals_for": 0,
        "goals_conceded": 0,
        "goal_difference": 0,
        "points": 0
    }


def _apply_split_match(
    stats: dict[str, Any],
    team_id: int,
    row: pd.Series) -> None:
    """Update split statistics for one played match."""
    is_home = int(row["home_id"]) == team_id
    goals_for = int(
        row["home_team_goals"] if is_home else row["away_team_goals"])
    goals_against = int(
        row["away_team_goals"] if is_home else row["home_team_goals"])
    form_result = _match_form_result(team_id, row)
    sport_id = row.get("sport_id")
    is_hockey = (
        sport_id is not None
        and not (isinstance(sport_id, float) and pd.isna(sport_id))
        and int(sport_id) == HOCKEY_SPORT_ID)

    stats["played"] += 1
    stats["goals_for"] += goals_for
    stats["goals_conceded"] += goals_against
    if is_hockey:
        if form_result in ("W", "WPD"):
            stats["wins"] += 1
            stats["points"] += 2
        elif form_result == "D":
            stats["draws"] += 1
            stats["points"] += 1
        elif form_result == "PPD":
            stats["losses"] += 1
            stats["points"] += 1
        else:
            stats["losses"] += 1
    elif form_result == "W":
        stats["wins"] += 1
        stats["points"] += 3
    elif form_result == "D":
        stats["draws"] += 1
        stats["points"] += 1
    else:
        stats["losses"] += 1
    stats["goal_difference"] = stats["goals_for"] - stats["goals_conceded"]


def _build_split_stats(
    team_id: int,
    matches_frame: pd.DataFrame) -> tuple[
        dict[str, Any],
        dict[str, Any],
        dict[str, Any]]:
    """Build overall, home and away statistics from match rows."""
    overall = _empty_split_stats()
    home_stats = _empty_split_stats()
    away_stats = _empty_split_stats()

    for _, row in matches_frame.iterrows():
        _apply_split_match(overall, team_id, row)
        if int(row["home_id"]) == team_id:
            _apply_split_match(home_stats, team_id, row)
        else:
            _apply_split_match(away_stats, team_id, row)

    return overall, home_stats, away_stats


def _map_season_match_point(
    team_id: int,
    row: pd.Series) -> dict[str, Any]:
    """Map a match row to a chart-friendly season match point."""
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
    return {
        "match_id": int(row["id"]),
        "match_date": game_date,
        "opponent_shortcut": shortcut,
        "opponent_name": opponent_name,
        "total_goals": home_goals + away_goals,
        "btts": home_goals > 0 and away_goals > 0,
        "result": _match_form_result(team_id, row),
        "home_team_name": str(row["home_name"]),
        "away_team_name": str(row["away_name"]),
        "home_goals": home_goals,
        "away_goals": away_goals,
        "is_home": is_home,
        "team_cards": _team_cards(row, team_id),
        "opponent_cards": _opponent_cards(row, team_id),
        "total_cards": _team_cards(row, team_id) + _opponent_cards(row, team_id),
        "team_offsides": _team_match_stat(
            row, team_id, "home_team_off", "away_team_off"),
        "opponent_offsides": _opponent_match_stat(
            row, team_id, "home_team_off", "away_team_off"),
        "total_offsides": (
            _stat_int(row.get("home_team_off"))
            + _stat_int(row.get("away_team_off"))),
        "team_corners": _team_match_stat(
            row, team_id, "home_team_ck", "away_team_ck"),
        "opponent_corners": _opponent_match_stat(
            row, team_id, "home_team_ck", "away_team_ck"),
        "total_corners": (
            _stat_int(row.get("home_team_ck"))
            + _stat_int(row.get("away_team_ck"))),
        "team_shots": _team_match_stat(
            row, team_id, "home_team_sc", "away_team_sc"),
        "opponent_shots": _opponent_match_stat(
            row, team_id, "home_team_sc", "away_team_sc"),
        "total_shots": (
            _stat_int(row.get("home_team_sc"))
            + _stat_int(row.get("away_team_sc"))),
        "team_shots_on_target": _team_match_stat(
            row, team_id, "home_team_sog", "away_team_sog"),
        "opponent_shots_on_target": _opponent_match_stat(
            row, team_id, "home_team_sog", "away_team_sog"),
        "total_shots_on_target": (
            _stat_int(row.get("home_team_sog"))
            + _stat_int(row.get("away_team_sog"))),
        "team_fouls": _team_match_stat(
            row, team_id, "home_team_fouls", "away_team_fouls"),
        "opponent_fouls": _opponent_match_stat(
            row, team_id, "home_team_fouls", "away_team_fouls"),
        "total_fouls": (
            _stat_int(row.get("home_team_fouls"))
            + _stat_int(row.get("away_team_fouls"))),
    }


def _build_head_to_head_summary(
    team_id: int,
    opponent_id: int,
    matches_frame: pd.DataFrame,
    special_rounds: dict[int, str]) -> dict[str, Any]:
    """Build aggregated head-to-head statistics between two teams."""
    wins = 0
    draws = 0
    losses = 0
    goals_for = 0
    goals_conceded = 0
    btts_count = 0
    meetings: list[dict[str, Any]] = []

    for _, row in matches_frame.iterrows():
        is_home = int(row["home_id"]) == team_id
        team_goals = int(
            row["home_team_goals"] if is_home else row["away_team_goals"])
        opponent_goals = int(
            row["away_team_goals"] if is_home else row["home_team_goals"])
        form_result = _match_form_result(team_id, row)

        goals_for += team_goals
        goals_conceded += opponent_goals
        if form_result == "W":
            wins += 1
        elif form_result == "D":
            draws += 1
        else:
            losses += 1
        if team_goals > 0 and opponent_goals > 0:
            btts_count += 1

        meetings.append(_map_match_summary_row(row, special_rounds))

    played = len(meetings)
    return {
        "team_id": team_id,
        "opponent_id": opponent_id,
        "played": played,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": goals_for,
        "goals_conceded": goals_conceded,
        "btts_count": btts_count,
        "btts_percentage": (
            round(btts_count * 100 / played, 2) if played > 0 else 0.0),
        "avg_goals_per_match": (
            round((goals_for + goals_conceded) / played, 2)
            if played > 0 else 0.0),
        "meetings": meetings
    }


def get_team_profile(
    team_id: int,
    season_id: int | None = None,
    league_id: int | None = None,
    limit: int = 5,
    opponent_id: int | None = None) -> dict[str, Any] | None:
    """Return team profile data or None when the team does not exist."""
    team_frame = team_repository.fetch_team_by_id(team_id)
    if team_frame.empty:
        return None

    all_matches = team_repository.fetch_team_played_matches(
        team_id=team_id,
        season_id=season_id,
        league_id=league_id)

    overall, home_stats, away_stats = _build_split_stats(
        team_id,
        all_matches)

    # forma i lista meczów dla całego sezonu; frontend filtruje po suwaku lookback
    form: list[FormResult] = []
    if not all_matches.empty:
        for _, row in all_matches.iloc[::-1].iterrows():
            form.append(_match_form_result(team_id, row))

    special_rounds = league_repository.fetch_special_round_names()

    recent_matches = [
        _map_match_summary_row(row, special_rounds)
        for _, row in all_matches.iterrows()
    ]
    season_matches: list[dict[str, Any]] = []
    team_sport_id = team_frame.iloc[0].get("sport_id")
    is_hockey_team = (
        team_sport_id is not None
        and not (isinstance(team_sport_id, float) and pd.isna(team_sport_id))
        and int(team_sport_id) == HOCKEY_SPORT_ID)
    first_period_map: dict[int, int] = {}
    if is_hockey_team and not all_matches.empty:
        match_ids = [int(row["id"]) for _, row in all_matches.iterrows()]
        first_period_map = fetch_first_period_goals(match_ids)

    for _, row in all_matches.iterrows():
        if is_hockey_team:
            season_matches.append(map_hockey_season_match_point(
                team_id,
                row,
                first_period_goals=first_period_map.get(int(row["id"]))))
        else:
            season_matches.append(_map_season_match_point(team_id, row))

    head_to_head = None
    if opponent_id is not None and opponent_id != team_id:
        if team_repository.team_exists(opponent_id):
            h2h_frame = team_repository.fetch_head_to_head_matches(
                team_id,
                opponent_id,
                limit=limit)
            head_to_head = _build_head_to_head_summary(
                team_id,
                opponent_id,
                h2h_frame,
                special_rounds)

    return {
        "team": _map_team_summary(team_frame.iloc[0]),
        "season_id": season_id,
        "league_id": league_id,
        "form": form,
        "recent_matches": recent_matches,
        "overall_stats": overall,
        "home_stats": home_stats,
        "away_stats": away_stats,
        "season_matches": season_matches,
        "head_to_head": head_to_head
    }
