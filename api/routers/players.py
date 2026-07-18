"""Player statistics endpoints for the EkstraBet API."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Path, Query

from api.schemas.player import (
    FootballPlayerMatchStatsResponse,
    FootballPlayersListResponse,
    FootballPlayerSummary,
    HockeyPlayerMatchStatsResponse,
    PlayerCountriesResponse,
    PlayerCountryOption,
    PlayerSeasonOption,
    PlayerSeasonsResponse,
    PlayerSportResponse,
    PlayerSportsListResponse,
    PlayerTeamOption,
    PlayerTeamsResponse)
from backend.services import player_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/players", tags=["Players"])


@router.get("/", tags=["System"])
async def players_info() -> dict[str, object]:
    """Return module metadata and available endpoints."""
    return {
        "module": "EkstraBet Players API",
        "version": "1.0.0",
        "description": "Player statistics and filter endpoints by sport",
        "endpoints": [
            "GET /players/sports - Sports available on the players page",
            "GET /players/{sport_id}/filters/countries - Country filters",
            "GET /players/{sport_id}/filters/teams - Team filters",
            "GET /players/{sport_id}/filters/seasons - Season filters",
            "GET /players/{sport_id} - Player list for selected filters",
            "GET /players/{sport_id}/{player_id}/match-stats - Player match stats",
        ],
    }


def _require_available_sport(sport_id: int) -> dict:
    """Return sport config or raise HTTP errors."""
    sport = player_service.resolve_player_sport(sport_id)
    if sport is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown sport: {sport_id}")
    if not sport["available"]:
        raise HTTPException(
            status_code=501,
            detail=f"Player stats for sport {sport_id} are not available yet")
    return sport


@router.get("/sports", response_model=PlayerSportsListResponse)
async def get_player_sports() -> PlayerSportsListResponse:
    """Return sports available on the players page."""
    sports = [
        PlayerSportResponse(**sport)
        for sport in player_service.get_player_sports()
    ]
    return PlayerSportsListResponse(
        sports=sports,
        total_count=len(sports))


@router.get(
    "/{sport_id}/filters/countries",
    response_model=PlayerCountriesResponse)
async def get_player_countries(
    sport_id: int = Path(..., ge=1, description="Sport ID")
) -> PlayerCountriesResponse:
    """Return country filter options for a sport."""
    _require_available_sport(sport_id)
    if sport_id == player_service.HOCKEY_SPORT_ID:
        return PlayerCountriesResponse(countries=[], total_count=0)
    if sport_id != player_service.FOOTBALL_SPORT_ID:
        raise HTTPException(
            status_code=501,
            detail=f"Country filters for sport {sport_id} are not implemented")

    countries = [
        PlayerCountryOption(**country)
        for country in player_service.get_football_filter_countries()
    ]
    return PlayerCountriesResponse(
        countries=countries,
        total_count=len(countries))


@router.get(
    "/{sport_id}/filters/teams",
    response_model=PlayerTeamsResponse)
async def get_player_teams(
    sport_id: int = Path(..., ge=1, description="Sport ID"),
    country_id: int | None = Query(None, ge=1, description="Country ID")
) -> PlayerTeamsResponse:
    """Return team filter options for a sport and country."""
    _require_available_sport(sport_id)
    if sport_id == player_service.HOCKEY_SPORT_ID:
        teams = [
            PlayerTeamOption(**team)
            for team in player_service.get_hockey_filter_teams()
        ]
        return PlayerTeamsResponse(teams=teams, total_count=len(teams))

    if sport_id != player_service.FOOTBALL_SPORT_ID:
        raise HTTPException(
            status_code=501,
            detail=f"Team filters for sport {sport_id} are not implemented")
    if country_id is None:
        raise HTTPException(
            status_code=422,
            detail="Provide country_id to list football teams")

    teams = [
        PlayerTeamOption(**team)
        for team in player_service.get_football_filter_teams(country_id)
    ]
    return PlayerTeamsResponse(teams=teams, total_count=len(teams))


@router.get(
    "/{sport_id}/filters/seasons",
    response_model=PlayerSeasonsResponse)
async def get_player_seasons(
    sport_id: int = Path(..., ge=1, description="Sport ID")
) -> PlayerSeasonsResponse:
    """Return season filter options for a sport."""
    _require_available_sport(sport_id)
    if sport_id == player_service.HOCKEY_SPORT_ID:
        seasons = [
            PlayerSeasonOption(**season)
            for season in player_service.get_hockey_filter_seasons()
        ]
        return PlayerSeasonsResponse(
            seasons=seasons,
            total_count=len(seasons))

    if sport_id != player_service.FOOTBALL_SPORT_ID:
        raise HTTPException(
            status_code=501,
            detail=f"Season filters for sport {sport_id} are not implemented")

    seasons = [
        PlayerSeasonOption(**season)
        for season in player_service.get_football_filter_seasons()
    ]
    return PlayerSeasonsResponse(
        seasons=seasons,
        total_count=len(seasons))


@router.get(
    "/{sport_id}",
    response_model=FootballPlayersListResponse)
async def get_players(
    sport_id: int = Path(..., ge=1, description="Sport ID"),
    season_id: int = Query(..., ge=1, description="Season ID"),
    team_id: int | None = Query(
        None,
        ge=1,
        description="Filter by current team ID"),
    search: str | None = Query(
        None,
        min_length=1,
        description="Filter by player name")
) -> FootballPlayersListResponse:
    """Return players for the selected sport filters."""
    _require_available_sport(sport_id)
    if sport_id == player_service.HOCKEY_SPORT_ID:
        if not search and team_id is None:
            raise HTTPException(
                status_code=422,
                detail="Provide team_id or search to list players")

        players = [
            FootballPlayerSummary(**player)
            for player in player_service.get_hockey_players(
                season_id=season_id,
                team_id=team_id,
                search=search)
        ]
        return FootballPlayersListResponse(
            players=players,
            total_count=len(players),
            season_id=season_id)

    if sport_id != player_service.FOOTBALL_SPORT_ID:
        raise HTTPException(
            status_code=501,
            detail=f"Player list for sport {sport_id} is not implemented")

    if not search and team_id is None:
        raise HTTPException(
            status_code=422,
            detail="Provide team_id or search to list players")

    players = [
        FootballPlayerSummary(**player)
        for player in player_service.get_football_players(
            season_id=season_id,
            team_id=team_id,
            search=search)
    ]
    return FootballPlayersListResponse(
        players=players,
        total_count=len(players),
        season_id=season_id)


@router.get(
    "/{sport_id}/{player_id}/match-stats",
    response_model=FootballPlayerMatchStatsResponse
    | HockeyPlayerMatchStatsResponse)
async def get_player_match_stats(
    sport_id: int = Path(..., ge=1, description="Sport ID"),
    player_id: int = Path(..., ge=1, description="Player ID"),
    season_id: int = Query(..., ge=1, description="Season ID"),
    limit: int = Query(
        50,
        ge=1,
        le=200,
        description="Number of recent matches")
) -> FootballPlayerMatchStatsResponse | HockeyPlayerMatchStatsResponse:
    """Return match log and summary stats for a player."""
    _require_available_sport(sport_id)
    if sport_id == player_service.HOCKEY_SPORT_ID:
        try:
            payload = player_service.get_hockey_player_match_stats(
                player_id=player_id,
                season_id=season_id,
                limit=limit)
        except Exception as exc:
            logger.error(
                "Failed to fetch hockey player stats for %s season %s: %s",
                player_id,
                season_id,
                exc)
            raise HTTPException(
                status_code=500,
                detail="Failed to fetch player match stats") from exc

        if payload is None:
            raise HTTPException(
                status_code=404,
                detail=f"No match stats for player {player_id}")

        return HockeyPlayerMatchStatsResponse(**payload)

    if sport_id != player_service.FOOTBALL_SPORT_ID:
        raise HTTPException(
            status_code=501,
            detail=f"Player stats for sport {sport_id} are not implemented")

    try:
        payload = player_service.get_football_player_match_stats(
            player_id=player_id,
            season_id=season_id,
            limit=limit)
    except Exception as exc:
        logger.error(
            "Failed to fetch player stats for %s season %s: %s",
            player_id,
            season_id,
            exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch player match stats") from exc

    if payload is None:
        raise HTTPException(
            status_code=404,
            detail=f"No match stats for player {player_id}")

    return FootballPlayerMatchStatsResponse(**payload)
