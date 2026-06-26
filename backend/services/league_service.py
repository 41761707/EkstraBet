"""Business logic for league navigation endpoints."""

from __future__ import annotations
import re
from datetime import date, datetime
from typing import Any
import pandas as pd
from backend.repositories import league_repository

def build_league_slug(name: str) -> str:
    """Build a URL slug from a league name."""
    slug = name.strip().lower().replace(" ", "_")
    return re.sub(r"[^\w._-]", "", slug, flags=re.UNICODE)


def _to_date(value: object) -> date | None:
    """Convert database date values to plain dates."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, pd.Timestamp):
        return value.date()
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def _map_league_row(row: pd.Series) -> dict[str, Any]:
    """Map a league dataframe row to an API-ready dictionary."""
    name = str(row["name"])
    return {
        "id": int(row["id"]),
        "name": name,
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
            if pd.notna(row["sport_name"]) else None),
        "active": bool(int(row["active"])) if pd.notna(row["active"]) else False,
        "last_update": _to_date(row["last_update"]),
        "slug": build_league_slug(name)
    }


def get_leagues(
    active: bool | None = True,
    sport_id: int | None = None) -> list[dict[str, Any]]:
    """Return leagues for navigation and home page listings."""
    frame = league_repository.fetch_leagues(
        active=active,
        sport_id=sport_id)
    if frame.empty:
        return []
    return [_map_league_row(row) for _, row in frame.iterrows()]


def get_league_details(league_id: int) -> dict[str, Any] | None:
    """Return league metadata with seasons and match count."""
    frame = league_repository.fetch_league_by_id(league_id)
    if frame.empty:
        return None

    summary = _map_league_row(frame.iloc[0])
    seasons_frame = league_repository.fetch_seasons_for_league(league_id)
    seasons = _map_season_rows(seasons_frame)

    return {
        **summary,
        "current_season_id": (
            int(frame.iloc[0]["current_season_id"])
            if pd.notna(frame.iloc[0]["current_season_id"]) else None),
        "tier": (
            int(frame.iloc[0]["tier"])
            if pd.notna(frame.iloc[0]["tier"]) else None),
        "has_player_stats": (
            bool(int(frame.iloc[0]["has_player_stats"]))
            if pd.notna(frame.iloc[0]["has_player_stats"]) else False),
        "match_count": league_repository.fetch_league_match_count(league_id),
        "seasons": seasons
    }


def get_league_seasons(league_id: int) -> list[dict[str, Any]] | None:
    """Return seasons for a league or None when the league is missing."""
    if not league_repository.league_exists(league_id):
        return None
    frame = league_repository.fetch_seasons_for_league(league_id)
    return _map_season_rows(frame)


def get_league_rounds(
    league_id: int,
    season_id: int) -> list[dict[str, Any]] | None:
    """Return rounds for a league season or None when the league is missing."""
    if not league_repository.league_exists(league_id):
        return None
    frame = league_repository.fetch_rounds_for_league_season(
        league_id,
        season_id)
    return _map_round_rows(frame)


def _map_season_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Map season query results to response dictionaries."""
    if frame.empty:
        return []
    seasons: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        seasons.append({
            "season_id": int(row["season_id"]),
            "years": str(row["years"]),
            "match_count": int(row.get("match_count", 0) or 0)
        })
    return seasons


def _map_round_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Map round query results to response dictionaries."""
    if frame.empty:
        return []
    rounds: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        game_date = _to_date(row["game_date"])
        rounds.append({
            "round_number": int(row["round_number"]),
            "game_date": game_date.isoformat() if game_date else ""
        })
    return rounds
