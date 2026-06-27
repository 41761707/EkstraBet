"""Business logic for bet recommendation endpoints."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

import pandas as pd

from backend.repositories import bet_repository

BETTING_TAX_RATE = 0.12

SettlementStatus = Literal["pending", "won", "lost"]
SortBy = Literal["ev", "probability", "game_date"]
SortOrder = Literal["asc", "desc"]


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


def _optional_str(value: object) -> str | None:
    """Convert nullable values to strings."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return str(value)


def _compute_ev_after_tax(
    probability: float,
    odds: float,
    apply_tax: bool,
    tax_rate: float) -> float | None:
    """Return EV adjusted for Polish betting tax when requested."""
    if not apply_tax:
        return None
    return probability * odds * (1 - tax_rate) - 1


def _map_settlement_status(outcome: object) -> SettlementStatus:
    """Map database outcome to API settlement status."""
    if outcome is None or (isinstance(outcome, float) and pd.isna(outcome)):
        return "pending"
    return "won" if int(outcome) == 1 else "lost"


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


def _map_bet_row(row: pd.Series, apply_tax: bool) -> dict[str, Any]:
    """Map a raw bet recommendation dataframe row."""
    probability = float(row["probability"])
    odds = float(row["odds"])
    ev = float(row["ev"])
    ev_after_tax = _compute_ev_after_tax(
        probability,
        odds,
        apply_tax,
        BETTING_TAX_RATE)
    home_shortcut = _optional_str(row.get("home_team_shortcut"))
    away_shortcut = _optional_str(row.get("away_team_shortcut"))
    return {
        "bet_id": int(row["bet_id"]),
        "match_id": int(row["match_id"]),
        "league_id": int(row["league_id"]),
        "league_name": str(row["league_name"]),
        "season_id": int(row["season_id"]),
        "game_date": row["game_date"],
        "home_team": {
            "id": int(row["home_team_id"]),
            "name": str(row["home_team_name"]),
            "shortcut": home_shortcut
        },
        "away_team": {
            "id": int(row["away_team_id"]),
            "name": str(row["away_team_name"]),
            "shortcut": away_shortcut
        },
        "event_id": int(row["event_id"]),
        "event_name": str(row["event_name"]),
        "event_family": _map_event_family(row),
        "odds": odds,
        "probability": probability,
        "probability_pct": round(probability * 100, 2),
        "ev": ev,
        "ev_after_tax": ev_after_tax,
        "bookmaker_id": _optional_int(row.get("bookmaker_id")),
        "bookmaker_name": _optional_str(row.get("bookmaker_name")),
        "model_id": int(row["model_id"]),
        "model_name": str(row["model_name"]),
        "settlement_status": _map_settlement_status(row.get("bet_outcome")),
        "custom_bet": bool(int(row.get("custom_bet", 0) or 0))
    }


def get_bet_recommendations(
    league_ids: list[int] | None = None,
    season_id: int | None = None,
    event_ids: list[int] | None = None,
    model_ids: list[int] | None = None,
    bookmaker_ids: list[int] | None = None,
    match_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    from_now: bool = False,
    min_odds: float | None = None,
    positive_ev_only: bool = False,
    apply_tax: bool = False,
    settlement_status: str | None = None,
    sort_by: SortBy = "ev",
    sort_order: SortOrder = "desc",
    page: int = 1,
    page_size: int = 50) -> dict[str, Any]:
    """Return paginated bet recommendations with applied filters."""
    frame, total = bet_repository.search_bet_recommendations(
        league_ids=league_ids,
        season_id=season_id,
        event_ids=event_ids,
        model_ids=model_ids,
        bookmaker_ids=bookmaker_ids,
        match_date=match_date,
        date_from=date_from,
        date_to=date_to,
        from_now=from_now,
        min_odds=min_odds,
        positive_ev_only=positive_ev_only,
        apply_tax=apply_tax,
        tax_rate=BETTING_TAX_RATE,
        settlement_status=settlement_status,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size)
    recommendations = [
        _map_bet_row(row, apply_tax)
        for _, row in frame.iterrows()
    ]
    return {
        "recommendations": recommendations,
        "total_count": total,
        "filters_applied": {
            "league_ids": league_ids,
            "season_id": season_id,
            "event_ids": event_ids,
            "model_ids": model_ids,
            "bookmaker_ids": bookmaker_ids,
            "match_date": (
                match_date.isoformat() if match_date else None),
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
            "from_now": from_now,
            "min_odds": min_odds,
            "positive_ev_only": positive_ev_only,
            "apply_tax": apply_tax,
            "tax_rate": BETTING_TAX_RATE if apply_tax else None,
            "settlement_status": settlement_status,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "page": page,
            "page_size": page_size
        }
    }
