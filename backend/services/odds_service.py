"""Business logic for bookmaker odds read endpoints."""

from __future__ import annotations

from typing import Any

import pandas as pd

from backend.repositories import match_repository, odds_repository


def _optional_int(value: object) -> int | None:
    """Convert nullable numeric values to integers."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return int(value)


def _map_event_family(row: pd.Series) -> dict[str, Any] | None:
    """Map event family columns when present on a dataframe row."""
    family_id = _optional_int(row.get("event_family_id"))
    family_name = row.get("event_family_name")
    if family_id is None or family_name is None or pd.isna(family_name):
        return None
    return {
        "id": family_id,
        "name": str(family_name)
    }


def _map_odds_row(row: pd.Series) -> dict[str, Any]:
    """Map an odds dataframe row to the unified API structure."""
    return {
        "id": int(row["id"]),
        "match_id": int(row["match_id"]),
        "bookmaker_id": int(row["bookmaker_id"]),
        "bookmaker_name": str(row["bookmaker_name"]),
        "event_id": int(row["event_id"]),
        "event_name": str(row["event_name"]),
        "event_family": _map_event_family(row),
        "odds": float(row["odds"])
    }


def get_match_odds(match_id: int) -> dict[str, Any] | None:
    """Return match odds or None when the match does not exist."""
    if not match_repository.match_exists(match_id):
        return None

    frame = odds_repository.fetch_match_odds(match_id)
    odds = [
        _map_odds_row(row)
        for _, row in frame.iterrows()
    ]
    return {
        "odds": odds,
        "total_count": len(odds),
        "match_id": match_id
    }


def get_match_odds_items(match_id: int) -> list[dict[str, Any]]:
    """Return odds rows for embedding in match details."""
    frame = odds_repository.fetch_match_odds(match_id)
    return [
        _map_odds_row(row)
        for _, row in frame.iterrows()
    ]
