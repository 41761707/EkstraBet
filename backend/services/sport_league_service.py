"""Business logic for NHL/NBA league pages."""

from __future__ import annotations
from datetime import date, datetime
from typing import Any, Literal
import pandas as pd
from backend.repositories import league_repository, sport_league_repository
from backend.repositories.sport_league_repository import (
    BASKETBALL_SPORT_ID,
    HOCKEY_SPORT_ID,
    REGULAR_SEASON_ROUND)
from backend.sports.basketball import league_stats as basketball_league_stats
from backend.sports.basketball.standings import build_basketball_standings
from backend.sports.basketball.team_history import build_basketball_team_history
from backend.sports.hockey import league_stats as hockey_league_stats
from backend.sports.hockey.first_period_goals import fetch_first_period_goals
from backend.sports.hockey.standings import build_hockey_standings
from backend.sports.hockey.team_history import build_hockey_team_history
from backend.services.match_score import map_score_resolution
from backend.services.round_label import resolve_round_label

SportPhase = int
StandingScope = Literal["overall", "home", "away"]


def _resolve_sport_id(league_id: int) -> int | None:
    """Return sport id for a league or None when unsupported."""
    frame = league_repository.fetch_league_by_id(league_id)
    if frame.empty:
        return None
    sport_id = frame.iloc[0].get("sport_id")
    if sport_id is None or (isinstance(sport_id, float) and pd.isna(sport_id)):
        return None
    sport = int(sport_id)
    if sport not in (HOCKEY_SPORT_ID, BASKETBALL_SPORT_ID):
        return None
    return sport


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


def _map_sport_match_row(
    row: pd.Series,
    sport_id: int,
    special_rounds: dict[int, str]) -> dict[str, Any]:
    """Map a sport match dataframe row to MatchSummary-compatible dict."""
    game_date = _to_datetime(row["game_date"])
    if game_date is None:
        raise ValueError("Match row is missing game_date")
    result = str(row["result"]) if pd.notna(row["result"]) else "0"
    resolution_row = row.copy()
    resolution_row["sport_id"] = sport_id
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
                str(row["home_shortcut"])
                if pd.notna(row["home_shortcut"]) else None)
        },
        "away_team": {
            "id": int(row["away_id"]),
            "name": str(row["away_name"]),
            "shortcut": (
                str(row["away_shortcut"])
                if pd.notna(row["away_shortcut"]) else None)
        },
        "home_goals": _optional_int(row.get("home_team_goals")),
        "away_goals": _optional_int(row.get("away_team_goals")),
        "result": result,
        "is_played": result != "0",
        "score_resolution": map_score_resolution(resolution_row)
    }


def get_sport_matches(
    league_id: int,
    season_id: int,
    phase: SportPhase | None = None,
    date_from: date | None = None,
    date_to: date | None = None) -> list[dict[str, Any]] | None:
    """Return sport league matches or None when league is unsupported."""
    sport_id = _resolve_sport_id(league_id)
    if sport_id is None:
        return None
    frame = sport_league_repository.fetch_sport_matches(
        league_id=league_id,
        season_id=season_id,
        sport_id=sport_id,
        phase=phase,
        date_from=date_from,
        date_to=date_to)
    if frame.empty:
        return []
    special_rounds = league_repository.fetch_special_round_names()
    return [
        _map_sport_match_row(row, sport_id, special_rounds)
        for _, row in frame.iterrows()]


def get_sport_teams(
    league_id: int,
    season_id: int) -> list[dict[str, Any]] | None:
    """Return teams for a sport league season."""
    sport_id = _resolve_sport_id(league_id)
    if sport_id is None:
        return None
    frame = sport_league_repository.fetch_teams_in_sport_season(
        league_id,
        season_id,
        sport_id)
    if frame.empty:
        return []
    return [
        {
            "team_id": int(row["team_id"]),
            "team_name": str(row["team_name"]),
            "team_shortcut": (
                str(row["team_shortcut"])
                if pd.notna(row["team_shortcut"]) else None)
        }
        for _, row in frame.iterrows()
    ]


def get_sport_standings(
    league_id: int,
    season_id: int,
    scope: StandingScope = "overall",
    phase: SportPhase | None = REGULAR_SEASON_ROUND) -> dict[str, Any] | None:
    """Return sport-specific standings for a league season."""
    sport_id = _resolve_sport_id(league_id)
    if sport_id is None:
        return None

    teams_frame = sport_league_repository.fetch_teams_in_sport_season(
        league_id,
        season_id,
        sport_id)
    matches_frame = sport_league_repository.fetch_played_sport_matches(
        league_id,
        season_id,
        sport_id,
        phase=phase)
    if sport_id == HOCKEY_SPORT_ID:
        regular = matches_frame[
            matches_frame["round"] == REGULAR_SEASON_ROUND]
        standings = build_hockey_standings(teams_frame, regular, scope)
    else:
        regular = matches_frame[
            matches_frame["round"] == REGULAR_SEASON_ROUND]
        standings = build_basketball_standings(teams_frame, regular, scope)

    return {
        "league_id": league_id,
        "season_id": season_id,
        "scope": scope,
        "standings": standings,
        "total_count": len(standings)
    }


def get_sport_team_history(
    league_id: int,
    season_id: int,
    team_id: int,
    phase: SportPhase | None = None,
    lookback: int = 10) -> list[dict[str, Any]] | None:
    """Return recent match history for charts on sport league pages."""
    sport_id = _resolve_sport_id(league_id)
    if sport_id is None:
        return None
    frame = sport_league_repository.fetch_sport_matches(
        league_id=league_id,
        season_id=season_id,
        sport_id=sport_id,
        phase=phase)
    if sport_id == HOCKEY_SPORT_ID:
        match_ids = [
            int(row["id"])
            for _, row in frame.iterrows()
            if int(row["home_id"]) == team_id or int(row["away_id"]) == team_id]
        first_period_map = fetch_first_period_goals(match_ids)
        return build_hockey_team_history(
            team_id, frame, lookback, first_period_map)
    return build_basketball_team_history(team_id, frame, lookback)


def get_sport_league_stats(
    league_id: int,
    season_id: int,
    category: str,
    phase: SportPhase | None = None) -> dict[str, Any] | None:
    """Return league stats payload for one category tab."""
    sport_id = _resolve_sport_id(league_id)
    if sport_id is None:
        return None

    if sport_id == HOCKEY_SPORT_ID:
        if category == "shots":
            rows = hockey_league_stats.fetch_hockey_shots_stats(
                league_id, season_id, phase)
        elif category == "goals":
            rows = hockey_league_stats.fetch_hockey_goals_stats(
                league_id, season_id, phase)
        elif category == "over_under":
            rows = hockey_league_stats.fetch_hockey_over_under_stats(
                league_id, season_id, phase)
        else:
            return None
        return {"category": category, "rows": rows, "distribution": None}

    if category == "shooting":
        rows = basketball_league_stats.fetch_basketball_shooting_stats(
            league_id, season_id, phase)
        return {"category": category, "rows": rows, "distribution": None}
    if category == "points":
        distribution = basketball_league_stats.fetch_basketball_points_distribution(
            league_id, season_id, phase)
        return {
            "category": category,
            "rows": [],
            "distribution": distribution}
    if category == "over_under":
        rows = basketball_league_stats.fetch_basketball_over_under_stats(
            league_id, season_id, phase)
        return {"category": category, "rows": rows, "distribution": None}
    return None
