"""Business logic for player statistics endpoints."""

from __future__ import annotations

from typing import Any

import pandas as pd

from backend.repositories import player_repository

FOOTBALL_SPORT_ID = 1
HOCKEY_SPORT_ID = 2
BASKETBALL_SPORT_ID = 3

# TODO: Pobierać dane z bazy!
PLAYER_SPORTS: dict[int, dict[str, Any]] = {
    FOOTBALL_SPORT_ID: {
        "label": "Piłka nożna",
        "emoji": "⚽",
        "available": True,
    },
    HOCKEY_SPORT_ID: {
        "label": "NHL",
        "emoji": "🏒",
        "available": True,
    },
    BASKETBALL_SPORT_ID: {
        "label": "NBA",
        "emoji": "🏀",
        "available": False,
    },
}


def get_player_sports() -> list[dict[str, Any]]:
    """Return sports exposed on the players page."""
    return [
        {"sport_id": sport_id, **config}
        for sport_id, config in PLAYER_SPORTS.items()
    ]


def resolve_player_sport(sport_id: int) -> dict[str, Any] | None:
    """Return sport config for an ID or None when unknown."""
    config = PLAYER_SPORTS.get(sport_id)
    if config is None:
        return None
    return {"sport_id": sport_id, **config}


def get_football_filter_countries() -> list[dict[str, Any]]:
    """Return countries available in the football players filter."""
    frame = player_repository.fetch_football_player_countries()
    if frame.empty:
        return []
    return [
        {
            "id": int(row["country_id"]),
            "name": str(row["country_name"]),
            "emoji": (
                str(row["country_emoji"])
                if pd.notna(row["country_emoji"]) else None),
        }
        for _, row in frame.iterrows()
    ]


def get_football_filter_teams(country_id: int) -> list[dict[str, Any]]:
    """Return teams available for a football players country filter."""
    frame = player_repository.fetch_football_player_teams(country_id)
    if frame.empty:
        return []
    return [
        {
            "id": int(row["team_id"]),
            "name": str(row["team_name"]),
            "country_id": int(row["country_id"]),
        }
        for _, row in frame.iterrows()
    ]


def get_hockey_filter_teams() -> list[dict[str, Any]]:
    """Return NHL teams available in the players filter."""
    frame = player_repository.fetch_hockey_player_teams()
    if frame.empty:
        return []
    return [
        {
            "id": int(row["team_id"]),
            "name": str(row["team_name"]),
            "country_id": (
                int(row["country_id"])
                if pd.notna(row["country_id"]) else None),
        }
        for _, row in frame.iterrows()
    ]


def get_football_filter_seasons() -> list[dict[str, Any]]:
    """Return seasons available for football player stats."""
    frame = player_repository.fetch_football_player_seasons()
    if frame.empty:
        return []
    return [
        {
            "season_id": int(row["season_id"]),
            "years": str(row["years"]),
        }
        for _, row in frame.iterrows()
    ]


def get_hockey_filter_seasons() -> list[dict[str, Any]]:
    """Return seasons available for NHL player stats."""
    frame = player_repository.fetch_hockey_player_seasons()
    if frame.empty:
        return []
    return [
        {
            "season_id": int(row["season_id"]),
            "years": str(row["years"]),
        }
        for _, row in frame.iterrows()
    ]


def get_football_players(
    season_id: int,
    team_id: int | None = None,
    search: str | None = None) -> list[dict[str, Any]]:
    """Return football players for the selected filters."""
    frame = player_repository.fetch_football_players(
        season_id=season_id,
        team_id=team_id,
        search=search)
    if frame.empty:
        return []
    return [
        {
            "id": int(row["player_id"]),
            "common_name": str(row["common_name"]),
            "current_team_id": int(row["current_team_id"]),
            "position": None,
        }
        for _, row in frame.iterrows()
    ]


def get_hockey_players(
    season_id: int,
    team_id: int | None = None,
    search: str | None = None) -> list[dict[str, Any]]:
    """Return NHL players for the selected filters."""
    frame = player_repository.fetch_hockey_players(
        season_id=season_id,
        team_id=team_id,
        search=search)
    if frame.empty:
        return []
    return [
        {
            "id": int(row["player_id"]),
            "common_name": str(row["common_name"]),
            "current_team_id": (
                int(row["current_team_id"])
                if pd.notna(row["current_team_id"]) else 0),
            "position": (
                str(row["position"])
                if pd.notna(row["position"]) else None),
        }
        for _, row in frame.iterrows()
    ]


def _build_match_stat_row(row: pd.Series) -> dict[str, Any]:
    """Map a player match stats row to API format."""
    return {
        "match_id": int(row["match_id"]),
        "home_team": str(row["home_team"]),
        "away_team": str(row["away_team"]),
        "match_date": str(row["match_date"]),
        "opponent_shortcut": (
            str(row["opponent_shortcut"])
            if pd.notna(row["opponent_shortcut"]) else ""),
        "goals": int(row["goals"]),
        "assists": int(row["assists"]),
        "shots": int(row["shots"]),
        "shots_on_target": int(row["shots_on_target"]),
        "fouls_conceded": int(row["fouls_conceded"]),
        "yellow_cards": int(row["yellow_cards"]),
    }


def get_football_player_match_stats(
    player_id: int,
    season_id: int,
    limit: int = 50) -> dict[str, Any] | None:
    """Return match log and summary totals for a football player."""
    frame = player_repository.fetch_football_player_match_stats(
        player_id,
        season_id,
        limit)
    if frame.empty:
        return None

    matches = [_build_match_stat_row(row) for _, row in frame.iterrows()]
    summary = {
        "goals": int(frame["goals"].sum()),
        "assists": int(frame["assists"].sum()),
        "shots": int(frame["shots"].sum()),
        "shots_on_target": int(frame["shots_on_target"].sum()),
        "fouls_conceded": int(frame["fouls_conceded"].sum()),
        "yellow_cards": int(frame["yellow_cards"].sum()),
    }
    return {
        "player_id": player_id,
        "season_id": season_id,
        "match_count": len(matches),
        "summary": summary,
        "matches": matches,
    }


def _toi_to_minutes(value: object) -> float:
    """Return time-on-ice text as decimal minutes."""
    if pd.isna(value):
        return 0.0
    parts = str(value).split(":")
    if len(parts) != 2:
        return 0.0
    try:
        return int(parts[0]) + int(parts[1]) / 60
    except ValueError:
        return 0.0


def _format_toi(minutes: float) -> str:
    """Return decimal minutes as mm:ss."""
    full_minutes = int(minutes)
    seconds = int(round((minutes - full_minutes) * 60))
    if seconds == 60:
        full_minutes += 1
        seconds = 0
    return f"{full_minutes}:{seconds:02d}"


def _build_hockey_match_stat_row(
    row: pd.Series,
    is_goalie: bool) -> dict[str, Any]:
    """Map a hockey player match stats row to API format."""
    base = {
        "match_id": int(row["match_id"]),
        "home_team": str(row["home_team"]),
        "away_team": str(row["away_team"]),
        "match_date": str(row["match_date"]),
        "opponent_shortcut": (
            str(row["opponent_shortcut"])
            if pd.notna(row["opponent_shortcut"]) else ""),
        "toi": str(row["toi"]),
        "toi_minutes": round(_toi_to_minutes(row["toi"]), 2),
    }
    if is_goalie:
        return {
            **base,
            "shots_against": int(row["shots_against"]),
            "shots_saved": int(row["shots_saved"]),
            "saves_acc": round(float(row["saves_acc"]), 1),
        }
    return {
        **base,
        "points": int(row["points"]),
        "goals": int(row["goals"]),
        "assists": int(row["assists"]),
        "plus_minus": int(row["plus_minus"]),
        "penalty_minutes": int(row["penalty_minutes"]),
        "sog": int(row["sog"]),
    }


def _build_hockey_summary(
    frame: pd.DataFrame,
    is_goalie: bool) -> dict[str, Any]:
    """Return role-specific hockey summary values."""
    average_toi = _format_toi(float(frame["toi_minutes"].mean()))
    if is_goalie:
        return {
            "is_goalie": True,
            "average_toi": average_toi,
            "shots_against": round(float(frame["shots_against"].mean()), 2),
            "shots_saved": round(float(frame["shots_saved"].mean()), 2),
            "saves_acc": round(float(frame["saves_acc"].mean()), 1),
        }
    return {
        "is_goalie": False,
        "points": int(frame["points"].sum()),
        "goals": int(frame["goals"].sum()),
        "assists": int(frame["assists"].sum()),
        "plus_minus": int(frame["plus_minus"].sum()),
        "penalty_minutes": int(frame["penalty_minutes"].sum()),
        "average_penalty_minutes": round(
            float(frame["penalty_minutes"].mean()),
            2),
        "average_toi": average_toi,
        "average_sog": round(float(frame["sog"].mean()), 2),
    }


def get_hockey_player_match_stats(
    player_id: int,
    season_id: int,
    limit: int = 200) -> dict[str, Any] | None:
    """Return match log and summary stats for an NHL player."""
    position = player_repository.fetch_player_position(player_id)
    is_goalie = position == "G"
    frame = player_repository.fetch_hockey_player_match_stats(
        player_id,
        season_id,
        limit,
        is_goalie)
    if frame.empty:
        return None

    rows = [_build_hockey_match_stat_row(row, is_goalie)
            for _, row in frame.iterrows()]
    stats_frame = pd.DataFrame(rows)
    return {
        "player_id": player_id,
        "season_id": season_id,
        "match_count": len(rows),
        "player_role": "goalie" if is_goalie else "skater",
        "summary": _build_hockey_summary(stats_frame, is_goalie),
        "matches": rows,
    }
