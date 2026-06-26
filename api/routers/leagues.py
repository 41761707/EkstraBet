"""League navigation endpoints for the EkstraBet API."""

from __future__ import annotations
import logging
from fastapi import APIRouter, HTTPException, Path, Query
from api.schemas.league import (
    LeagueDetails,
    LeagueRoundsListResponse,
    LeagueRoundResponse,
    LeagueSeasonResponse,
    LeagueSeasonsListResponse,
    LeaguesListResponse,
    LeagueSummary)
from backend.services import league_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/leagues", tags=["Leagues"])


@router.get("/", tags=["System"])
async def leagues_info() -> dict[str, object]:
    """Return module metadata and available endpoints."""
    return {
        "module": "EkstraBet Leagues API",
        "version": "1.0.0",
        "description": "League navigation and metadata endpoints",
        "endpoints": [
            "GET /leagues - List leagues with filters",
            "GET /leagues/{league_id} - League details",
            "GET /leagues/{league_id}/seasons - Seasons for a league",
            "GET /leagues/{league_id}/rounds/{season_id} - Rounds for a season",
        ],
    }

@router.get("", response_model=LeaguesListResponse)
async def get_leagues(
    active: bool | None = Query(
        True,
        description="Filter by active leagues; omit filter with null"),
    sport_id: int | None = Query(
        None,
        ge=1,
        description="Filter by sport ID")) -> LeaguesListResponse:
    """Return leagues for home page navigation and league pickers."""
    try:
        leagues = league_service.get_leagues(
            active=active,
            sport_id=sport_id)
        summaries = [LeagueSummary(**league) for league in leagues]
        return LeaguesListResponse(
            leagues=summaries,
            total_count=len(summaries))
    except Exception as exc:
        logger.error("Failed to fetch leagues: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch leagues") from exc


@router.get(
    "/{league_id}/seasons",
    response_model=LeagueSeasonsListResponse)
async def get_league_seasons(
    league_id: int = Path(..., ge=1, description="League ID")
) -> LeagueSeasonsListResponse:
    """Return seasons available for the given league."""
    try:
        seasons = league_service.get_league_seasons(league_id)
        if seasons is None:
            raise HTTPException(
                status_code=404,
                detail=f"League {league_id} not found")
        mapped = [LeagueSeasonResponse(**season) for season in seasons]
        return LeagueSeasonsListResponse(
            seasons=mapped,
            total_count=len(mapped))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to fetch seasons for league %s: %s",
            league_id,
            exc)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch seasons for league {league_id}") from exc


@router.get(
    "/{league_id}/rounds/{season_id}",
    response_model=LeagueRoundsListResponse)
async def get_league_rounds(
    league_id: int = Path(..., ge=1, description="League ID"),
    season_id: int = Path(..., ge=1, description="Season ID")
) -> LeagueRoundsListResponse:
    """Return rounds available for the given league and season."""
    try:
        rounds = league_service.get_league_rounds(league_id, season_id)
        if rounds is None:
            raise HTTPException(
                status_code=404,
                detail=f"League {league_id} not found")
        mapped = [LeagueRoundResponse(**round_data) for round_data in rounds]
        return LeagueRoundsListResponse(
            rounds=mapped,
            total_count=len(mapped))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to fetch rounds for league %s season %s: %s",
            league_id,
            season_id,
            exc)
        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to fetch rounds for league {league_id}, "
                f"season {season_id}")) from exc


@router.get("/{league_id}", response_model=LeagueDetails)
async def get_league_details(
    league_id: int = Path(..., ge=1, description="League ID")
) -> LeagueDetails:
    """Return league metadata, seasons and match count."""
    try:
        details = league_service.get_league_details(league_id)
        if details is None:
            raise HTTPException(
                status_code=404,
                detail=f"League {league_id} not found")
        return LeagueDetails(**details)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to fetch league details for %s: %s",
            league_id,
            exc)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch league {league_id}") from exc
