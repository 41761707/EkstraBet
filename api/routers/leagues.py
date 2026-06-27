"""League navigation endpoints for the EkstraBet API."""

from __future__ import annotations
import logging
from datetime import date

from fastapi import APIRouter, HTTPException, Path, Query
from api.schemas.league import (
    LeagueDetails,
    LeagueRoundsListResponse,
    LeagueRoundResponse,
    LeagueSeasonResponse,
    LeagueSeasonsListResponse,
    LeaguesListResponse,
    LeagueSummary)
from api.schemas.match import (
    LeagueMatchesListResponse,
    MatchSummary)
from api.schemas.standing import (
    LeagueStandingsResponse,
    OuBttsStandingRow,
    StandingScope,
    TraditionalStandingRow)
from backend.services import league_service, match_service, standings_service

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
            "GET /leagues/{league_id}/matches - League schedule and results",
            "GET /leagues/{league_id}/standings - League standings",
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


@router.get(
    "/{league_id}/matches",
    response_model=LeagueMatchesListResponse)
async def get_league_matches(
    league_id: int = Path(..., ge=1, description="League ID"),
    season_id: int = Query(..., ge=1, description="Season ID"),
    round: int | None = Query(
        None,
        ge=0,
        description="Filter by round number"),
    date_from: date | None = Query(
        None,
        description="Include matches from this date"),
    date_to: date | None = Query(
        None,
        description="Include matches up to this date")
) -> LeagueMatchesListResponse:
    """Return league schedule and results with optional filters."""
    if (
        date_from is not None
        and date_to is not None
        and date_from > date_to
    ):
        raise HTTPException(
            status_code=422,
            detail="date_from must be less than or equal to date_to")
    try:
        matches = match_service.get_league_matches(
            league_id=league_id,
            season_id=season_id,
            round_num=round,
            date_from=date_from,
            date_to=date_to)
        if matches is None:
            raise HTTPException(
                status_code=404,
                detail=f"League {league_id} not found")
        mapped = [MatchSummary(**match) for match in matches]
        return LeagueMatchesListResponse(
            matches=mapped,
            total_count=len(mapped),
            league_id=league_id,
            season_id=season_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to fetch matches for league %s season %s: %s",
            league_id,
            season_id,
            exc)
        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to fetch matches for league {league_id}, "
                f"season {season_id}")) from exc


@router.get(
    "/{league_id}/standings",
    response_model=LeagueStandingsResponse)
async def get_league_standings(
    league_id: int = Path(..., ge=1, description="League ID"),
    season_id: int = Query(..., ge=1, description="Season ID"),
    scope: StandingScope = Query(
        "overall",
        description="Standings scope: overall, home, away, ou_btts")
) -> LeagueStandingsResponse:
    """Return league standings for the requested season and scope."""
    try:
        payload = standings_service.get_league_standings(
            league_id=league_id,
            season_id=season_id,
            scope=scope)
        if payload is None:
            raise HTTPException(
                status_code=404,
                detail=f"League {league_id} not found")
        if scope == "ou_btts":
            mapped = [
                OuBttsStandingRow(**row)
                for row in payload["standings"]
            ]
        else:
            mapped = [
                TraditionalStandingRow(**row)
                for row in payload["standings"]
            ]
        return LeagueStandingsResponse(
            league_id=payload["league_id"],
            season_id=payload["season_id"],
            scope=payload["scope"],
            standings=mapped,
            total_count=payload["total_count"])
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to fetch standings for league %s season %s: %s",
            league_id,
            season_id,
            exc)
        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to fetch standings for league {league_id}, "
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
