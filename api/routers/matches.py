from fastapi import APIRouter, HTTPException, Path, Query
import pandas as pd
from pydantic import BaseModel, Field
import logging
from typing import Optional, List

from api.schemas.match import MatchDetails
from api.utils import execute_query
from api.routers.utils import parse_id_list
from backend.services import match_service

# Konfiguracja logowania
logger = logging.getLogger(__name__)

# === MODELE PYDANTIC ===

class SeasonResponse(BaseModel):
    """Response model for a season."""
    season_id: int = Field(..., description="Season ID")
    years: str = Field(..., description="Season years (e.g. '2023/24')")

class SeasonsListResponse(BaseModel):
    """Response model for a season list."""
    seasons: List[SeasonResponse] = Field(..., description="Season list")
    total_count: int = Field(..., description="Total number of seasons")

class RoundResponse(BaseModel):
    """Response model for a round."""
    round_number: int = Field(..., description="Round number")
    game_date: str = Field(..., description="Game date (latest in the round)")

class RoundsListResponse(BaseModel):
    """Response model for a round list."""
    rounds: List[RoundResponse] = Field(..., description="Round list")
    total_count: int = Field(..., description="Total number of rounds")

class MatchResponse(BaseModel):
    """Response model for a match with team data."""
    home_id: int = Field(..., description="Home team ID")
    home: str = Field(..., description="Home team name")
    home_shortcut: str = Field(..., description="Home team shortcut")
    guest_id: int = Field(..., description="Away team ID")
    guest: str = Field(..., description="Away team name")
    guest_shortcut: str = Field(..., description="Away team shortcut")
    date: str = Field(..., description="Match date (DD.MM format)")
    home_goals: Optional[int] = Field(None, description="Home team goals")
    away_goals: Optional[int] = Field(None, description="Away team goals")
    round: Optional[int] = Field(None, description="Round number")
    result: str = Field(..., description="Match result")

class MatchesListResponse(BaseModel):
    """Response model for a match list."""
    matches: List[MatchResponse] = Field(..., description="Match list")
    total_count: int = Field(..., description="Total number of matches")

class TeamInSeasonResponse(BaseModel):
    """Response model for a team in a season."""
    id: int = Field(..., description="Team ID")
    name: str = Field(..., description="Team name")

class TeamsInSeasonListResponse(BaseModel):
    """Response model for teams in a season."""
    teams: List[TeamInSeasonResponse] = Field(..., description="Team list")
    total_count: int = Field(..., description="Total number of teams")

# === ROUTER ===
router = APIRouter(prefix="/matches", tags=["Matches"])

@router.get("/", tags=["System"])
async def matches_info():
    """Return module metadata and available endpoints."""
    return {
        "module": "EkstraBet Matches API",
        "version": "1.0.0",
        "description": "Match data and schedule endpoints",
        "endpoints": [
            "GET /matches/seasons/{league_id} - Seasons for a league",
            "GET /matches/rounds/{league_id}/{season_id} - Rounds for a season",
            "GET /matches/{match_id}/details - Full match details",
            "GET /matches/{league_id}/{season_id} - Matches with teams for a season",
            "GET /matches/teams-in-season/{league_id}/{season_id} - Teams in regular season",
        ],
    }

@router.get("/seasons/{league_id}", response_model=SeasonsListResponse)
async def get_seasons_for_league(
    league_id: int
) -> SeasonsListResponse:
    """
    Return all seasons for a league.

    Args:
        league_id: League ID

    Returns:
        Season list sorted from newest to oldest
    """
    try:
        # Zapytanie o sezony dla danej ligi (parametryzowane)
        season_query = """
            SELECT distinct m.season, s.years 
            FROM matches m 
            JOIN seasons s ON m.season = s.id 
            WHERE m.league = %s 
            ORDER BY s.years DESC
        """ 
        logger.info(f"Wykonuję zapytanie o sezony dla ligi {league_id}")
        seasons_df = execute_query(season_query, params=(league_id,))
        if seasons_df.empty:
                logger.warning(f"Brak sezonów dla ligi {league_id}")
                return SeasonsListResponse(
                    seasons=[],
                    total_count=0
                )
        # Konwersja wyników
        seasons_list = []
        for _, row in seasons_df.iterrows():
            season = SeasonResponse(
                season_id=int(row['season']),
                years=str(row['years'])
            )
            seasons_list.append(season)
        total_count = len(seasons_list)
        logger.info(f"Znaleziono {total_count} sezonów dla ligi {league_id}")
        return SeasonsListResponse(
            seasons=seasons_list,
            total_count=total_count
        )
    except Exception as e:
        logger.error(f"Błąd w get_seasons_for_league dla ligi {league_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch seasons for league {league_id}")

@router.get("/rounds/{league_id}/{season_id}", response_model=RoundsListResponse)
async def get_rounds_for_season(
    league_id: int,
    season_id: int
) -> RoundsListResponse:
    """
    Return all rounds for a season in a league.

    Args:
        league_id: League ID
        season_id: Season ID

    Returns:
        Round list sorted chronologically (newest round first)
    """
    try:
        # Zapytanie o rundy dla danego sezonu w lidze (parametryzowane)
        rounds_query = """
            SELECT round, cast(game_date as date) as game_date
            FROM matches 
            WHERE league = %s AND season = %s 
            ORDER BY game_date DESC
        """
        
        logger.info(f"Wykonuję zapytanie o rundy dla ligi {league_id}, sezonu {season_id}")
            
        # Wykonanie zapytania z parametrami
        rounds_df = execute_query(rounds_query, params=(league_id, season_id))
            
        if rounds_df.empty:
            logger.warning(f"Brak rund dla ligi {league_id}, sezonu {season_id}")
            return RoundsListResponse(
                rounds=[],
                total_count=0
            )
        
        # Konwersja wyników - grupowanie po rundach i wybór najnowszej daty dla każdej rundy
        rounds_grouped = rounds_df.groupby('round')['game_date'].max().reset_index()
        # Sortowanie chronologiczne - najstarsza kolejka na końcu (ascending=False)
        rounds_grouped = rounds_grouped.sort_values('game_date', ascending=False)
        
        rounds_list = []
        for _, row in rounds_grouped.iterrows():
            round_data = RoundResponse(
                round_number=int(row['round']),
                game_date=str(row['game_date'])
            )
            rounds_list.append(round_data)
        
        total_count = len(rounds_list)
        
        logger.info(f"Znaleziono {total_count} rund dla ligi {league_id}, sezonu {season_id}")
        
        return RoundsListResponse(
            rounds=rounds_list,
            total_count=total_count
        )
        
    except Exception as e:
        logger.error(f"Błąd w get_rounds_for_season dla ligi {league_id}, sezonu {season_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to fetch rounds for league {league_id}, "
                f"season {season_id}"))

@router.get("/{match_id}/details", response_model=MatchDetails)
async def get_match_details(
    match_id: int = Path(..., ge=1, description="Match ID"),
    model_ids: str | None = Query(
        None,
        description="Comma-separated model IDs, e.g. '1,2,3'")
) -> MatchDetails:
    """Return teams, score, predictions, odds and basic stats for a match."""
    parsed_model_ids = parse_id_list(model_ids)
    try:
        details = match_service.get_match_details(
            match_id,
            model_ids=parsed_model_ids)
        if details is None:
            raise HTTPException(
                status_code=404,
                detail=f"Match {match_id} not found")
        return MatchDetails(**details)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to fetch match details for %s: %s",
            match_id,
            exc)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch match {match_id}") from exc

@router.get("/{league_id}/{season_id}", response_model=MatchesListResponse)
async def get_matches_with_teams(
    league_id: int,
    season_id: int
) -> MatchesListResponse:
    """
    Return all matches with team data for a season in a league.

    Args:
        league_id: League ID
        season_id: Season ID

    Returns:
        Match list with team data sorted from newest dates
    """
    try:
        # Zapytanie o mecze z danymi drużyn dla danego sezonu w lidze
        matches_query = """
            SELECT 
                m.home_team AS home_id, 
                t1.name AS home, 
                t1.shortcut AS home_shortcut, 
                m.away_team AS guest_id, 
                t2.name AS guest, 
                t2.shortcut AS guest_shortcut, 
                m.game_date as date, 
                m.home_team_goals AS home_goals, 
                m.away_team_goals AS away_goals, 
                m.round as round,
                m.result AS result
            FROM matches m 
            JOIN teams t1 ON m.home_team = t1.id 
            JOIN teams t2 ON m.away_team = t2.id 
            WHERE league = %s 
            AND season = %s 
            ORDER BY m.game_date DESC
        """
        
        logger.info(f"Wykonuję zapytanie o mecze z drużynami dla ligi {league_id}, sezonu {season_id}")
        
        # Wykonanie zapytania z parametrami
        matches_df = execute_query(matches_query, params=(league_id, season_id))
        
        if matches_df.empty:
            logger.warning(f"Brak meczów dla ligi {league_id}, sezonu {season_id}")
            return MatchesListResponse(
                matches=[],
                total_count=0
            )
        
        # Konwersja wyników
        matches_list = []
        for _, row in matches_df.iterrows():
            match = MatchResponse(
                home_id=int(row['home_id']),
                home=str(row['home']),
                home_shortcut=str(row['home_shortcut']),
                guest_id=int(row['guest_id']),
                guest=str(row['guest']),
                guest_shortcut=str(row['guest_shortcut']),
                date=str(row['date']),
                home_goals=int(row['home_goals']) if pd.notna(row['home_goals']) else None,
                away_goals=int(row['away_goals']) if pd.notna(row['away_goals']) else None,
                round=int(row['round']) if pd.notna(row['round']) else None,
                result=str(row['result'])
            )
            matches_list.append(match)
        
        total_count = len(matches_list)
        
        logger.info(f"Znaleziono {total_count} meczów z drużynami dla ligi {league_id}, sezonu {season_id}")
        
        return MatchesListResponse(
            matches=matches_list,
            total_count=total_count
        )
        
    except Exception as e:
        logger.error(f"Błąd w get_matches_with_teams dla ligi {league_id}, sezonu {season_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to fetch matches with teams for league {league_id}, "
                f"season {season_id}"))

@router.get("/teams-in-season/{league_id}/{season_id}", response_model=TeamsInSeasonListResponse)
async def get_teams_in_season(
    league_id: int,
    season_id: int
) -> TeamsInSeasonListResponse:
    """
    Return all teams that played at least one match in the regular season.

    Args:
        league_id: League ID
        season_id: Season ID

    Returns:
        Team list sorted alphabetically by name
    """
    try:
        # Zapytanie o drużyny grające w sezonie zasadniczym
        teams_query = """
            SELECT DISTINCT t.id, t.name 
            FROM matches m 
            JOIN teams t ON (m.home_team = t.id OR m.away_team = t.id)
            WHERE m.league = %s AND m.season = %s AND m.round < 900
            ORDER BY t.name
        """
        
        logger.info(f"Wykonuję zapytanie o drużyny w sezonie zasadniczym dla ligi {league_id}, sezonu {season_id}")
        
        # Wykonanie zapytania z parametrami
        teams_df = execute_query(teams_query, params=(league_id, season_id))
        
        if teams_df.empty:
            logger.warning(f"Brak drużyn dla ligi {league_id}, sezonu {season_id}")
            return TeamsInSeasonListResponse(
                teams=[],
                total_count=0
            )
        
        # Konwersja wyników
        teams_list = []
        for _, row in teams_df.iterrows():
            team = TeamInSeasonResponse(
                id=int(row['id']),
                name=str(row['name'])
            )
            teams_list.append(team)
        
        total_count = len(teams_list)
        
        logger.info(f"Znaleziono {total_count} drużyn w sezonie zasadniczym dla ligi {league_id}, sezonu {season_id}")
        
        return TeamsInSeasonListResponse(
            teams=teams_list,
            total_count=total_count
        )
        
    except Exception as e:
        logger.error(f"Błąd w get_teams_in_season dla ligi {league_id}, sezonu {season_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to fetch teams in season for league {league_id}, "
                f"season {season_id}"))
