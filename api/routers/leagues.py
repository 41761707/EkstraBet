"""League navigation endpoints for the EkstraBet API."""

from __future__ import annotations
import logging
from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException, Path, Query
from api.schemas.analytics import LeagueCharacteristics
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
from api.schemas.sport_league import (
    BasketballStandingRow,
    BasketballTeamHistoryPoint,
    HockeyStandingRow,
    HockeyTeamHistoryPoint,
    SportLeagueStatsResponse,
    SportLeagueStatRow,
    SportMatchesListResponse,
    SportPointsDistributionSummary,
    SportStandingsResponse,
    SportTeamHistoryResponse,
    SportTeamsListResponse,
    SportTeamSummary)
from backend.repositories.sport_league_repository import (
    BASKETBALL_SPORT_ID,
    HOCKEY_SPORT_ID)
from backend.services import league_service, match_service, sport_league_service, standings_service

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
            "GET /leagues/{league_id}/characteristics - League OU/BTTS stats",
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
    "/{league_id}/characteristics",
    response_model=LeagueCharacteristics)
async def get_league_characteristics(
    league_id: int = Path(..., ge=1, description="League ID"),
    season_id: int = Query(..., ge=1, description="Season ID")
) -> LeagueCharacteristics:
    """Return league-level OU, BTTS and 1X2 distribution."""
    try:
        if league_service.get_league_details(league_id) is None:
            raise HTTPException(
                status_code=404,
                detail=f"League {league_id} not found")
        payload = league_service.get_league_characteristics(
            league_id,
            season_id)
        if payload is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"No played matches for league {league_id}, "
                    f"season {season_id}"))
        return LeagueCharacteristics(**payload)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to fetch characteristics for league %s season %s: %s",
            league_id,
            season_id,
            exc)
        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to fetch characteristics for league {league_id}, "
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


def _league_sport_id(league_id: int) -> int:
    """Return sport id for a league or raise 404/400."""
    details = league_service.get_league_details(league_id)
    if details is None:
        raise HTTPException(
            status_code=404,
            detail=f"League {league_id} not found")
    sport_id = details.get("sport_id")
    if sport_id not in (HOCKEY_SPORT_ID, BASKETBALL_SPORT_ID):
        raise HTTPException(
            status_code=400,
            detail=f"League {league_id} is not an NHL/NBA sport league")
    return int(sport_id)


@router.get(
    "/{league_id}/sport/matches",
    response_model=SportMatchesListResponse)
async def get_sport_league_matches(
    league_id: int = Path(..., ge=1, description="League ID"),
    season_id: int = Query(..., ge=1, description="Season ID"),
    phase: int | None = Query(
        None,
        description="100 for regular season, 200 for playoffs"),
    date_from: date | None = Query(
        None,
        description="Include matches from this date"),
    date_to: date | None = Query(
        None,
        description="Include matches up to this date")
) -> SportMatchesListResponse:
    """Return NHL/NBA schedule with optional phase and date filters."""
    if (
        date_from is not None
        and date_to is not None
        and date_from > date_to
    ):
        raise HTTPException(
            status_code=422,
            detail="date_from must be less than or equal to date_to")
    _league_sport_id(league_id)
    try:
        matches = sport_league_service.get_sport_matches(
            league_id=league_id,
            season_id=season_id,
            phase=phase,
            date_from=date_from,
            date_to=date_to)
        if matches is None:
            raise HTTPException(
                status_code=400,
                detail=f"League {league_id} is not an NHL/NBA sport league")
        mapped = [MatchSummary(**match) for match in matches]
        return SportMatchesListResponse(
            matches=mapped,
            total_count=len(mapped),
            league_id=league_id,
            season_id=season_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to fetch sport matches for league %s: %s",
            league_id,
            exc)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch sport matches for league {league_id}") from exc


@router.get(
    "/{league_id}/sport/teams",
    response_model=SportTeamsListResponse)
async def get_sport_league_teams(
    league_id: int = Path(..., ge=1, description="League ID"),
    season_id: int = Query(..., ge=1, description="Season ID")
) -> SportTeamsListResponse:
    """Return teams participating in an NHL/NBA season."""
    _league_sport_id(league_id)
    try:
        teams = sport_league_service.get_sport_teams(league_id, season_id)
        if teams is None:
            raise HTTPException(
                status_code=400,
                detail=f"League {league_id} is not an NHL/NBA sport league")
        mapped = [SportTeamSummary(**team) for team in teams]
        return SportTeamsListResponse(
            teams=mapped,
            total_count=len(mapped))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to fetch sport teams for league %s: %s",
            league_id,
            exc)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch sport teams for league {league_id}") from exc


@router.get(
    "/{league_id}/sport/standings",
    response_model=SportStandingsResponse)
async def get_sport_league_standings(
    league_id: int = Path(..., ge=1, description="League ID"),
    season_id: int = Query(..., ge=1, description="Season ID"),
    scope: Literal["overall", "home", "away"] = Query(
        "overall",
        description="Standings scope")
) -> SportStandingsResponse:
    """Return NHL/NBA standings for the requested scope."""
    sport_id = _league_sport_id(league_id)
    try:
        payload = sport_league_service.get_sport_standings(
            league_id=league_id,
            season_id=season_id,
            scope=scope)
        if payload is None:
            raise HTTPException(
                status_code=400,
                detail=f"League {league_id} is not an NHL/NBA sport league")
        if sport_id == HOCKEY_SPORT_ID:
            hockey = [
                HockeyStandingRow(**row)
                for row in payload["standings"]
            ]
            return SportStandingsResponse(
                league_id=league_id,
                season_id=season_id,
                scope=scope,
                sport_id=sport_id,
                hockey_standings=hockey,
                basketball_standings=None,
                total_count=payload["total_count"])
        basketball = [
            BasketballStandingRow(**row)
            for row in payload["standings"]
        ]
        return SportStandingsResponse(
            league_id=league_id,
            season_id=season_id,
            scope=scope,
            sport_id=sport_id,
            hockey_standings=None,
            basketball_standings=basketball,
            total_count=payload["total_count"])
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to fetch sport standings for league %s: %s",
            league_id,
            exc)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch sport standings for league {league_id}") from exc


@router.get(
    "/{league_id}/sport/teams/{team_id}/history",
    response_model=SportTeamHistoryResponse)
async def get_sport_team_history(
    league_id: int = Path(..., ge=1, description="League ID"),
    team_id: int = Path(..., ge=1, description="Team ID"),
    season_id: int = Query(..., ge=1, description="Season ID"),
    phase: int | None = Query(
        None,
        description="100 for regular season, 200 for playoffs"),
    lookback: int = Query(10, ge=1, le=50, description="Recent matches")
) -> SportTeamHistoryResponse:
    """Return recent team match history for NHL/NBA charts."""
    sport_id = _league_sport_id(league_id)
    try:
        history = sport_league_service.get_sport_team_history(
            league_id=league_id,
            season_id=season_id,
            team_id=team_id,
            phase=phase,
            lookback=lookback)
        if history is None:
            raise HTTPException(
                status_code=400,
                detail=f"League {league_id} is not an NHL/NBA sport league")
        if sport_id == HOCKEY_SPORT_ID:
            mapped = [HockeyTeamHistoryPoint(**row) for row in history]
            return SportTeamHistoryResponse(
                team_id=team_id,
                sport_id=sport_id,
                hockey_history=mapped,
                basketball_history=None,
                total_count=len(mapped))
        mapped = [BasketballTeamHistoryPoint(**row) for row in history]
        return SportTeamHistoryResponse(
            team_id=team_id,
            sport_id=sport_id,
            hockey_history=None,
            basketball_history=mapped,
            total_count=len(mapped))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to fetch sport team history for league %s team %s: %s",
            league_id,
            team_id,
            exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch sport team history") from exc


@router.get(
    "/{league_id}/sport/stats/{category}",
    response_model=SportLeagueStatsResponse)
async def get_sport_league_stats(
    league_id: int = Path(..., ge=1, description="League ID"),
    category: str = Path(..., description="Stats category"),
    season_id: int = Query(..., ge=1, description="Season ID"),
    phase: int | None = Query(
        None,
        description="100 for regular season, 200 for playoffs")
) -> SportLeagueStatsResponse:
    """Return NHL/NBA league stats for one category tab."""
    sport_id = _league_sport_id(league_id)
    try:
        payload = sport_league_service.get_sport_league_stats(
            league_id=league_id,
            season_id=season_id,
            category=category,
            phase=phase)
        if payload is None:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown stats category: {category}")
        rows = [SportLeagueStatRow(**row) for row in payload["rows"]]
        distribution = None
        if payload.get("distribution") and payload["distribution"].get("summary"):
            distribution = SportPointsDistributionSummary(
                **payload["distribution"]["summary"])
        return SportLeagueStatsResponse(
            league_id=league_id,
            season_id=season_id,
            sport_id=sport_id,
            category=category,
            rows=rows,
            distribution=distribution)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to fetch sport league stats for league %s: %s",
            league_id,
            exc)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch sport league stats for league {league_id}") from exc


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
