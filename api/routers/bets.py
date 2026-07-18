"""Bet recommendation endpoints for the EkstraBet API."""

from __future__ import annotations

import logging
from datetime import date
from typing import Literal
from fastapi import APIRouter, HTTPException, Query
from api.routers.utils import parse_id_list
from api.schemas.bet import BetRecommendationsResponse
from backend.config import get_settings
from backend.services import bet_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bets", tags=["Bets"])

SettlementFilter = Literal[
    "pending",
    "settled",
    "won",
    "lost"]


@router.get("/", tags=["System"])
async def bets_info() -> dict[str, object]:
    """Return module metadata and available endpoints."""
    return {
        "module": "EkstraBet Bets API",
        "version": "1.0.0",
        "description": "Read-only endpoints for bet recommendations and EV",
        "endpoints": [
            "GET /bets/recommendations - Filtered bet recommendations",
        ],
    }


@router.get("/recommendations", response_model=BetRecommendationsResponse)
async def get_bet_recommendations(
    league_ids: str | None = Query(
        None,
        description="Comma-separated league IDs"),
    season_id: int | None = Query(
        None,
        ge=1,
        description="Season ID filter"),
    event_ids: str | None = Query(
        None,
        description="Comma-separated event IDs"),
    model_ids: str | None = Query(
        None,
        description="Comma-separated model IDs"),
    bookmaker_ids: str | None = Query(
        None,
        description="Comma-separated bookmaker IDs"),
    match_date: date | None = Query(
        None,
        description="Exact match date (YYYY-MM-DD)"),
    date_from: date | None = Query(
        None,
        description="Inclusive start date"),
    date_to: date | None = Query(
        None,
        description="Inclusive end date"),
    from_now: bool = Query(
        False,
        description="Only matches starting from the current moment"),
    min_odds: float | None = Query(
        None,
        ge=1.0,
        description="Minimum decimal odds"),
    positive_ev_only: bool = Query(
        False,
        description="Only bets with positive EV (after tax when enabled)"),
    apply_tax: bool = Query(
        False,
        description="Compute ev_after_tax using 12% betting tax"),
    settlement_status: SettlementFilter | None = Query(
        None,
        description="Filter by bet settlement status"),
    sort_by: Literal["ev", "probability", "game_date"] = Query(
        "ev",
        description="Sort field"),
    sort_order: Literal["asc", "desc"] = Query(
        "desc",
        description="Sort direction"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int | None = Query(
        None,
        ge=1,
        description="Page size")) -> BetRecommendationsResponse:
    """Return bet recommendations for the bookmaking view."""
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(
            status_code=422,
            detail="date_from cannot be later than date_to")

    settings = get_settings()
    resolved_page_size = page_size or settings.default_page_size
    if resolved_page_size > settings.max_page_size:
        raise HTTPException(
            status_code=422,
            detail=f"page_size cannot exceed {settings.max_page_size}")

    try:
        payload = bet_service.get_bet_recommendations(
            league_ids=parse_id_list(league_ids),
            season_id=season_id,
            event_ids=parse_id_list(event_ids),
            model_ids=parse_id_list(model_ids),
            bookmaker_ids=parse_id_list(bookmaker_ids),
            match_date=match_date,
            date_from=date_from,
            date_to=date_to,
            from_now=from_now,
            min_odds=min_odds,
            positive_ev_only=positive_ev_only,
            apply_tax=apply_tax,
            settlement_status=settlement_status,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=resolved_page_size)
        return BetRecommendationsResponse(**payload)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch bet recommendations: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch bet recommendations") from exc
