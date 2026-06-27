"""Bookmaker odds read endpoints for the EkstraBet API."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Path

from api.schemas.odds import MatchOddsListResponse
from backend.services import odds_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/odds", tags=["Odds"])


@router.get("/", tags=["System"])
async def odds_info() -> dict[str, object]:
    """Return module metadata and available endpoints."""
    return {
        "module": "EkstraBet Odds API",
        "version": "1.0.0",
        "description": "Read-only endpoints for bookmaker odds",
        "endpoints": [
            "GET /odds/match/{match_id} - All odds for a match",
        ],
    }


@router.get("/match/{match_id}", response_model=MatchOddsListResponse)
async def get_odds_for_match(
    match_id: int = Path(..., ge=1, description="Match ID")
) -> MatchOddsListResponse:
    """Return unified odds rows for a match."""
    try:
        payload = odds_service.get_match_odds(match_id)
        if payload is None:
            raise HTTPException(
                status_code=404,
                detail=f"Match {match_id} not found")
        return MatchOddsListResponse(**payload)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to fetch odds for match %s: %s",
            match_id,
            exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch match odds") from exc
