"""Business logic for bet recommendation endpoints."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

import pandas as pd

from backend.repositories import bet_repository
from backend.services.probability_service import to_unit_probability

BETTING_TAX_RATE = 0.12
_MAX_OPPORTUNITIES_LIMIT = 20
_DEFAULT_OPPORTUNITIES_LIMIT = 10

SettlementStatus = Literal["pending", "won", "lost"]
SortBy = Literal["ev", "probability", "game_date"]
SortOrder = Literal["asc", "desc"]
OpportunitySource = Literal["bet", "prediction"]
RankingBasis = Literal["ev_after_tax", "ev", "probability"]


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


def _compute_ev(probability: float, odds: float) -> float:
    """Return raw expected value from unit probability and decimal odds."""
    return probability * odds - 1


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
    # p.value w DB jest w skali 0-100 — normalizujemy do 0-1
    probability = to_unit_probability(float(row["probability"]))
    odds = float(row["odds"])
    ev = _compute_ev(probability, odds)
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
    match_id: int | None = None,
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
        match_id=match_id,
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
            "match_id": match_id,
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


def _map_opportunity_row(row: pd.Series) -> dict[str, Any]:
    """Map a market opportunity dataframe row to the API contract."""
    probability = _optional_float(row.get("probability"))
    if probability is None:
        raw_pct = _optional_float(row.get("probability_pct"))
        probability = (
            to_unit_probability(raw_pct) if raw_pct is not None else None)
    probability_pct = _optional_float(row.get("probability_pct"))
    if probability_pct is None and probability is not None:
        probability_pct = round(probability * 100, 2)

    odds = _optional_float(row.get("odds"))
    implied = (1.0 / odds) if odds is not None and odds > 0 else None
    ev = _optional_float(row.get("ev"))
    ev_after_tax = _optional_float(row.get("ev_after_tax"))
    if (
        probability is not None
        and odds is not None
        and ev is None
    ):
        ev = _compute_ev(probability, odds)
    if (
        probability is not None
        and odds is not None
        and ev_after_tax is None
        and str(row.get("ranking_basis")) == "ev_after_tax"
    ):
        ev_after_tax = _compute_ev_after_tax(
            probability, odds, True, BETTING_TAX_RATE)

    return {
        "match_id": int(row["match_id"]),
        "sport_id": int(row["sport_id"]),
        "league_id": int(row["league_id"]),
        "league_name": str(row["league_name"]),
        "game_date": row["game_date"],
        "home_team": str(row["home_team"]),
        "away_team": str(row["away_team"]),
        "event_id": int(row["event_id"]),
        "event_name": str(row["event_name"]),
        "model_id": _optional_int(row.get("model_id")),
        "model_name": _optional_str(row.get("model_name")),
        "probability": probability,
        "probability_pct": probability_pct,
        "odds": odds,
        "bookmaker_id": _optional_int(row.get("bookmaker_id")),
        "bookmaker_name": _optional_str(row.get("bookmaker_name")),
        "implied_probability": implied,
        "ev": ev,
        "ev_after_tax": ev_after_tax,
        "source": str(row["source"]),
        "ranking_basis": str(row["ranking_basis"])
    }


def get_market_opportunities(
    sport_id: int,
    match_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    from_now: bool = True,
    apply_tax: bool = True,
    positive_ev_only: bool = True,
    include_prediction_fallback: bool = True,
    one_per_match: bool = True,
    limit: int = _DEFAULT_OPPORTUNITIES_LIMIT) -> dict[str, Any]:
    """Return a fixed-size global ranking for one sport and date window."""
    resolved_limit = max(1, min(limit, _MAX_OPPORTUNITIES_LIMIT))
    frame, total, source_counts = bet_repository.search_market_opportunities(
        sport_id=sport_id,
        match_date=match_date,
        date_from=date_from,
        date_to=date_to,
        from_now=from_now,
        apply_tax=apply_tax,
        tax_rate=BETTING_TAX_RATE,
        positive_ev_only=positive_ev_only,
        include_prediction_fallback=include_prediction_fallback,
        one_per_match=one_per_match,
        limit=resolved_limit)

    opportunities = [
        _map_opportunity_row(row)
        for _, row in frame.iterrows()
    ] if not frame.empty else []

    warnings: list[str] = []
    prediction_count = int(source_counts.get("prediction", 0))
    if prediction_count > 0:
        no_odds = any(
            item["odds"] is None and item["source"] == "prediction"
            for item in opportunities)
        if no_odds:
            warnings.append(
                "Ranking was topped up with predictions that have no odds; "
                "those rows use probability ranking and are not value bets.")
        else:
            warnings.append(
                "Ranking was topped up with prediction-only candidates.")

    return {
        "opportunities": opportunities,
        "total_count": total,
        "filters_applied": {
            "sport_id": sport_id,
            "match_date": (
                match_date.isoformat() if match_date else None),
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
            "from_now": from_now,
            "apply_tax": apply_tax,
            "tax_rate": BETTING_TAX_RATE if apply_tax else None,
            "positive_ev_only": positive_ev_only,
            "include_prediction_fallback": include_prediction_fallback,
            "one_per_match": one_per_match,
            "limit": resolved_limit
        },
        "source_counts": source_counts,
        "warnings": warnings
    }
