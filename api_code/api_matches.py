# API EkstraBet - Moduł obsługi meczów
# Plik zawiera endpointy FastAPI do zarządzania danymi meczów
# Autor: System EkstraBet

from fastapi import APIRouter, HTTPException, Query
import pandas as pd
from pydantic import BaseModel, Field
import logging
from typing import Optional, List

from pyparsing import Opt
from utils import get_db_connection, execute_query

# Konfiguracja logowania
logger = logging.getLogger(__name__)

# === MODELE PYDANTIC ===

class SeasonResponse(BaseModel):
    """Model odpowiedzi dla sezonu"""
    season_id: int = Field(..., description="ID sezonu")
    years: str = Field(..., description="Lata sezonu (np. '2023/24')")

class SeasonsListResponse(BaseModel):
    """Model odpowiedzi dla listy sezonów"""
    seasons: List[SeasonResponse] = Field(..., description="Lista sezonów")
    total_count: int = Field(..., description="Całkowita liczba sezonów")

class RoundResponse(BaseModel):
    """Model odpowiedzi dla rundy"""
    round_number: int = Field(..., description="Numer rundy")
    game_date: str = Field(..., description="Data gry (ostatnia w rundzie)")

class RoundsListResponse(BaseModel):
    """Model odpowiedzi dla listy rund"""
    rounds: List[RoundResponse] = Field(..., description="Lista rund")
    total_count: int = Field(..., description="Całkowita liczba rund")

class MatchResponse(BaseModel):
    """Model odpowiedzi dla meczu z drużynami"""
    home_id: int = Field(..., description="ID drużyny gospodarzy")
    home: str = Field(..., description="Nazwa drużyny gospodarzy")
    home_shortcut: str = Field(..., description="Skrót drużyny gospodarzy")
    guest_id: int = Field(..., description="ID drużyny gości")
    guest: str = Field(..., description="Nazwa drużyny gości")
    guest_shortcut: str = Field(..., description="Skrót drużyny gości")
    date: str = Field(..., description="Data meczu (format DD.MM)")
    home_goals: Optional[int] = Field(None, description="Bramki drużyny gospodarzy")
    away_goals: Optional[int] = Field(None, description="Bramki drużyny gości")
    round: Optional[int] = Field(None, description="Numer rundy")
    result: str = Field(..., description="Wynik meczu")

class MatchesListResponse(BaseModel):
    """Model odpowiedzi dla listy meczów"""
    matches: List[MatchResponse] = Field(..., description="Lista meczów")
    total_count: int = Field(..., description="Całkowita liczba meczów")

class TeamInSeasonResponse(BaseModel):
    """Model odpowiedzi dla drużyny w sezonie"""
    id: int = Field(..., description="ID drużyny")
    name: str = Field(..., description="Nazwa drużyny")

class TeamsInSeasonListResponse(BaseModel):
    """Model odpowiedzi dla listy drużyn w sezonie"""
    teams: List[TeamInSeasonResponse] = Field(..., description="Lista drużyn")
    total_count: int = Field(..., description="Całkowita liczba drużyn")

# === ROUTER ===
router = APIRouter(prefix="/matches", tags=["Mecze"])

@router.get("/", tags=["System"])
async def matches_info():
    """Endpoint główny - informacje o module matches"""
    return {
        "module": "EkstraBet Matches API",
        "version": "1.0.0", 
        "description": "API do zarządzania danymi meczów",
        "endpoints": [
            "/matches/seasons/{league_id} - Sezony dla danej ligi",
            "/matches/rounds/{league_id}/{season_id} - Rundy dla danego sezonu w lidze",
            "/matches/{league_id}/{season_id} - Mecze z drużynami dla danego sezonu w lidze",
            "/matches/teams-in-season/{league_id}/{season_id} - Drużyny grające w sezonie zasadniczym"
        ]
    }

@router.get("/seasons/{league_id}", response_model=SeasonsListResponse)
async def get_seasons_for_league(
    league_id: int
) -> SeasonsListResponse:
    """
    Pobiera wszystkie sezony dla danej ligi
    
    Args:
        league_id: ID ligi
        
    Returns:
        Lista sezonów posortowana od najnowszych
    """
    try:
        # Zapytanie o sezony dla danej ligi
        season_query = f"""
            SELECT distinct m.season, s.years 
            FROM matches m 
            JOIN seasons s ON m.season = s.id 
            WHERE m.league = {league_id} 
            ORDER BY s.years DESC
        """
        
        logger.info(f"Wykonuję zapytanie o sezony dla ligi {league_id}")
        
        # Wykonanie zapytania
        seasons_df = execute_query(season_query)
        
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
        raise HTTPException(status_code=500, detail=f"Błąd pobierania sezonów dla ligi {league_id}")

@router.get("/rounds/{league_id}/{season_id}", response_model=RoundsListResponse)
async def get_rounds_for_season(
    league_id: int,
    season_id: int
) -> RoundsListResponse:
    """
    Pobiera wszystkie rundy dla danego sezonu w lidze
    
    Args:
        league_id: ID ligi
        season_id: ID sezonu
        
    Returns:
        Lista rund posortowana chronologicznie (najnowsza kolejka na początku, najstarsza na końcu)
    """
    try:
        # Zapytanie o rundy dla danego sezonu w lidze
        rounds_query = f"""
            SELECT round, cast(game_date as date) as game_date
            FROM matches 
            WHERE league = {league_id} AND season = {season_id} 
            ORDER BY game_date DESC
        """
        
        logger.info(f"Wykonuję zapytanie o rundy dla ligi {league_id}, sezonu {season_id}")
        
        # Wykonanie zapytania
        rounds_df = execute_query(rounds_query)
        
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
        raise HTTPException(status_code=500, detail=f"Błąd pobierania rund dla ligi {league_id}, sezonu {season_id}")

@router.get("/{league_id}/{season_id}", response_model=MatchesListResponse)
async def get_matches_with_teams(
    league_id: int,
    season_id: int
) -> MatchesListResponse:
    """
    Pobiera wszystkie mecze z danymi drużyn dla danego sezonu w lidze
    
    Args:
        league_id: ID ligi
        season_id: ID sezonu
        
    Returns:
        Lista meczów z danymi drużyn posortowana od najnowszych dat
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
        raise HTTPException(status_code=500, detail=f"Błąd pobierania meczów z drużynami dla ligi {league_id}, sezonu {season_id}")

@router.get("/teams-in-season/{league_id}/{season_id}", response_model=TeamsInSeasonListResponse)
async def get_teams_in_season(
    league_id: int,
    season_id: int
) -> TeamsInSeasonListResponse:
    """
    Pobiera wszystkie drużyny które rozegrały choć jeden mecz w sezonie zasadniczym
    
    Args:
        league_id: ID ligi
        season_id: ID sezonu
        
    Returns:
        Lista drużyn posortowana alfabetycznie według nazwy
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
        raise HTTPException(status_code=500, detail=f"Błąd pobierania drużyn w sezonie dla ligi {league_id}, sezonu {season_id}")
