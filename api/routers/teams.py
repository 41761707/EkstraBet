
from fastapi import APIRouter, HTTPException, Query
import pandas as pd
from pydantic import BaseModel, Field
import logging
from typing import Optional, List
from api.utils import execute_query
from api.schemas.team_profile import TeamProfileResponse
from backend.services import team_service

# Konfiguracja logowania
logger = logging.getLogger(__name__)

class TeamResponse(BaseModel):
    """Response model for a single team."""
    id: int = Field(..., description="Team ID")
    name: str = Field(..., description="Team name")
    shortcut: str = Field(None, description="Team name shortcut")
    country_id: int = Field(..., description="Country ID")
    country_name: str = Field(None, description="Country name")
    country_emoji: str = Field(None, description="Country flag")
    sport_id: int = Field(..., description="Sport ID")
    sport_name: str = Field(None, description="Sport name")

class TeamsListResponse(BaseModel):
    """Response model for a team list."""
    teams: list[TeamResponse] = Field(..., description="Team list")
    total_count: int = Field(..., description="Total number of teams")
    page: int = Field(..., description="Page number")
    page_size: int = Field(..., description="Page size")

class TeamStatsResponse(BaseModel):
    """Response model for team statistics."""
    team_id: int = Field(..., description="Team ID")
    team_name: str = Field(..., description="Team name")
    season_id: Optional[int] = Field(None, description="Season ID (optional filter)")
    season_years: Optional[str] = Field(None, description="Season years (optional filter)")
    last_n_matches: Optional[int] = Field(None, description="Number of recent matches (optional filter)")
    total_matches: int = Field(..., description="Total number of matches")
    home_matches: int = Field(..., description="Number of home matches")
    away_matches: int = Field(..., description="Number of away matches")
    wins: int = Field(..., description="Number of wins")
    draws: int = Field(..., description="Number of draws")
    losses: int = Field(..., description="Number of losses")
    goals_scored: int = Field(..., description="Goals scored")
    goals_conceded: int = Field(..., description="Goals conceded")

class TeamBTTSResponse(BaseModel):
    """Response model for team BTTS (Both Teams To Score) statistics."""
    team_id: int = Field(..., description="Team ID")
    team_name: str = Field(..., description="Team name")
    season_id: Optional[int] = Field(None, description="Season ID (when filtered)")
    season_years: Optional[str] = Field(None, description="Season years (when filtered)")
    last_n_matches: Optional[int] = Field(None, description="Number of recent matches (when filtered)")
    total_matches: int = Field(..., description="Total number of matches")
    btts_yes: int = Field(..., description="Matches where both teams scored")
    btts_no: int = Field(..., description="Matches where both teams did not score")
    btts_yes_percentage: float = Field(..., description="BTTS yes match percentage")
    btts_no_percentage: float = Field(..., description="BTTS no match percentage")

class TeamHockeyStatsResponse(BaseModel):
    """Response model for hockey team statistics."""
    team_id: int = Field(..., description="Team ID")
    team_name: str = Field(..., description="Team name")
    season_id: Optional[int] = Field(None, description="Season ID")
    last_n_matches: Optional[int] = Field(None, description="Number of recent matches")
    total_matches: int = Field(..., description="Number of matches")
    wins: int = Field(..., description="Number of wins")
    losses: int = Field(..., description="Number of losses")
    overtime_wins: int = Field(..., description="Number of overtime wins")
    overtime_loses: int = Field(..., description="Number of overtime losses")
    goals_for: int = Field(..., description="Goals scored")
    goals_against: int = Field(..., description="Goals conceded")
    overtime_matches: int = Field(..., description="Matches decided in overtime")
    shootout_matches: int = Field(..., description="Matches decided in shootout")
    avg_shots_on_target_for: float = Field(..., description="Average shots on goal per match")
    avg_shots_on_target_against: float = Field(..., description="Average shots on goal against per match")
    avg_saves_percentage: float = Field(..., description="Average save percentage")
    avg_powerplay_percentage: float = Field(..., description="Average power play percentage")
    avg_faceoff_percentage: float = Field(..., description="Average faceoff win percentage")
    avg_hits_per_game: float = Field(..., description="Average hits per match")

class HockeyPlayerRosterResponse(BaseModel):
    """Response model for a roster player."""
    player_id: int = Field(..., description="Player ID")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    common_name: str = Field(..., description="Full name")
    country: str = Field(..., description="Country of origin")
    position: str = Field(..., description="Position (G/D/LW/C/RW)")
    line: Optional[int] = Field(None, description="Line (1-4)")
    is_injured: bool = Field(..., description="Whether the player is injured")

class HockeyTeamRosterResponse(BaseModel):
    """Response model for a hockey team roster."""
    team_id: int = Field(..., description="Team ID")
    team_name: str = Field(..., description="Team name")
    goalkeepers: List[HockeyPlayerRosterResponse] = Field(..., description="Goalkeepers")
    defensemen: List[HockeyPlayerRosterResponse] = Field(..., description="Defensemen")
    forwards: List[HockeyPlayerRosterResponse] = Field(..., description="Forwards")
    injured_players: int = Field(..., description="Number of injured players")

class HeadToHeadResponse(BaseModel):
    """Response model for head-to-head statistics."""
    team_1_id: int = Field(..., description="First team ID")
    team_2_id: int = Field(..., description="Second team ID")
    last_meetings: List[dict] = Field(..., description="Last 5 meetings")

router = APIRouter(prefix="/teams", tags=["Teams"])

@router.get("/", tags=["System"])
async def teams_info():
    """Return module metadata and available endpoints."""
    return {
        "module": "EkstraBet Teams API",
        "version": "1.0.0",
        "description": "Team data, statistics and profile endpoints",
        "endpoints": [
            "GET /teams/all - All teams",
            "GET /teams/search - Search teams with filters",
            "GET /teams/{team_id}/profile - Team profile with form and split stats",
            "GET /teams/{team_id}/stats - Team statistics (optional season filter)",
            "GET /teams/{team_id}/btts - Team BTTS statistics (optional season filter)",
            "GET /teams/{team_id}/hockey-stats - Detailed hockey team statistics",
            "GET /teams/{team_id}/roster - Current hockey team roster",
            "GET /teams/head-to-head - Head-to-head statistics",
        ],
    }

@router.get("/{team_id}/profile", response_model=TeamProfileResponse)
async def get_team_profile(
    team_id: int,
    season_id: int | None = Query(
        None,
        ge=1,
        description="Optional season ID filter"),
    league_id: int | None = Query(
        None,
        ge=1,
        description="Optional league filter"),
    limit: int = Query(
        5,
        ge=1,
        le=100,
        description="Number of recent matches and H2H meetings"),
    opponent_id: int | None = Query(
        None,
        ge=1,
        description="Opponent team ID for head-to-head summary")
) -> TeamProfileResponse:
    """Return team profile with form, split stats and recent matches."""
    try:
        profile = team_service.get_team_profile(
            team_id=team_id,
            season_id=season_id,
            league_id=league_id,
            limit=limit,
            opponent_id=opponent_id)
        if profile is None:
            raise HTTPException(
                status_code=404,
                detail=f"Team {team_id} not found")
        return TeamProfileResponse(**profile)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to fetch profile for team %s: %s",
            team_id,
            exc)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch team profile for {team_id}") from exc

@router.get("/all", response_model=TeamsListResponse)
async def get_all_teams(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int  = Query(50, ge=1, le=500, description="Page size")
) -> TeamsListResponse:
    """
    Zwraca wszystkie drużyny w bazie danych z paginacją
    
    Endpoint pobiera pełną listę drużyn wraz z informacjami o krajach i sportach.
    Obsługuje paginację dla lepszej wydajności.
    """
    try:
        # Obliczenie offsetu dla paginacji
        offset = (page - 1) * page_size
        
        # Zapytanie główne z JOIN do tabel countries i sports
        query = """
        SELECT 
            t.ID as id,
            t.NAME as name,
            t.SHORTCUT as shortcut,
            t.COUNTRY as country_id,
            c.NAME as country_name,
            c.EMOJI as country_emoji,
            t.SPORT_ID as sport_id,
            s.NAME as sport_name
        FROM teams t
        LEFT JOIN countries c ON t.COUNTRY = c.ID
        LEFT JOIN sports s ON t.SPORT_ID = s.ID
        ORDER BY t.id
        LIMIT %s OFFSET %s
        """
        # Zapytanie do liczenia wszystkich rekordów
        count_query = "SELECT COUNT(*) as total FROM teams"
        # Wykonanie zapytań
        teams_df = execute_query(query, (page_size, offset))
        count_df = execute_query(count_query)
        # Konwersja wyników do modeli Pydantic
        teams_list = []
        for _, row in teams_df.iterrows():
            team = TeamResponse(
                id=int(row['id']),
                name=str(row['name']),
                shortcut=str(row['shortcut']) if pd.notna(row['shortcut']) else None,
                country_id=int(row['country_id']),
                country_name=str(row['country_name']) if pd.notna(row['country_name']) else None,
                country_emoji=str(row['country_emoji']) if pd.notna(row['country_emoji']) else None,
                sport_id=int(row['sport_id']),
                sport_name=str(row['sport_name']) if pd.notna(row['sport_name']) else None
            )
            teams_list.append(team)
        total_count = int(count_df.iloc[0]['total'])
        return TeamsListResponse(
            teams=teams_list,
            total_count=total_count,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        logger.error(f"Błąd w get_all_teams: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch team list")

@router.get("/search", response_model=TeamsListResponse)
async def get_specific_teams(
    country_id = Query(None, description="Country ID"),
    country_name = Query(None, description="Country name (partial match)"),
    sport_id = Query(None, description="Sport ID"),
    sport_name = Query(None, description="Sport name (partial match)"),
    team_name = Query(None, description="Team name (partial match)"),
    team_shortcut = Query(None, description="Team shortcut"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Page size")
) -> TeamsListResponse:
    """
    Wyszukuje drużyny na podstawie różnych filtrów
    
    Endpoint umożliwia filtrowanie drużyn według:
    - Kraju (ID lub nazwa)
    - Sportu (ID lub nazwa)
    - Nazwy drużyny
    - Skrótu drużyny
    
    Obsługuje częściowe dopasowanie tekstów oraz paginację.
    """
    try:
        # Budowanie warunków WHERE dynamicznie
        where_conditions = []
        params = []
        
        if country_id is not None:
            where_conditions.append("t.COUNTRY = %s")
            params.append(country_id)
            
        if country_name is not None:
            where_conditions.append("c.NAME LIKE %s")
            params.append(f"%{country_name}%")
            
        if sport_id is not None:
            where_conditions.append("t.SPORT_ID = %s")
            params.append(sport_id)
            
        if sport_name is not None:
            where_conditions.append("s.NAME LIKE %s")
            params.append(f"%{sport_name}%")
            
        if team_name is not None:
            where_conditions.append("t.NAME LIKE %s")
            params.append(f"%{team_name}%")
            
        if team_shortcut is not None:
            where_conditions.append("t.SHORTCUT = %s")
            params.append(team_shortcut)
        
        # Konstrukcja zapytania z warunkami WHERE
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        # Obliczenie offsetu dla paginacji
        offset = (page - 1) * page_size
        
        # Zapytanie główne
        query = f"""
        SELECT 
            t.ID as id,
            t.NAME as name,
            t.SHORTCUT as shortcut,
            t.COUNTRY as country_id,
            c.NAME as country_name,
            c.EMOJI as country_emoji,
            t.SPORT_ID as sport_id,
            s.NAME as sport_name
        FROM teams t
        LEFT JOIN countries c ON t.COUNTRY = c.ID
        LEFT JOIN sports s ON t.SPORT_ID = s.ID
        WHERE {where_clause}
        ORDER BY t.id
        LIMIT %s OFFSET %s
        """
        
        # Zapytanie do liczenia rekordów
        count_query = f"""
        SELECT COUNT(*) as total 
        FROM teams t
        LEFT JOIN countries c ON t.COUNTRY = c.ID
        LEFT JOIN sports s ON t.SPORT_ID = s.ID
        WHERE {where_clause}
        """
        
        # Dodanie parametrów paginacji
        query_params = params + [page_size, offset]
        count_params = params
        
        # Wykonanie zapytań
        teams_df = execute_query(query, tuple(query_params))
        count_df = execute_query(count_query, tuple(count_params))
        
        # Konwersja wyników
        teams_list = []
        for _, row in teams_df.iterrows():
            team = TeamResponse(
                id=int(row['id']),
                name=str(row['name']),
                shortcut=str(row['shortcut']) if pd.notna(row['shortcut']) else None,
                country_id=int(row['country_id']),
                country_name=str(row['country_name']) if pd.notna(row['country_name']) else None,
                country_emoji=str(row['country_emoji']) if pd.notna(row['country_emoji']) else None,
                sport_id=int(row['sport_id']),
                sport_name=str(row['sport_name']) if pd.notna(row['sport_name']) else None
            )
            teams_list.append(team)
        
        total_count = int(count_df.iloc[0]['total'])
        
        return TeamsListResponse(
            teams=teams_list,
            total_count=total_count,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Błąd w get_specific_teams: {e}")
        raise HTTPException(status_code=500, detail="Failed to search teams")

@router.get("/{team_id}/stats", response_model=TeamStatsResponse)
async def get_team_stats(
    team_id: int,
    season_id: Optional[int] = Query(None, description="Season ID (optional filter)"),
    last_n_matches: Optional[int] = Query(
        None, ge=1, le=100,
        description="Last N matches (optional filter, max 100)")
) -> TeamStatsResponse:
    """
    Pobiera szczegółowe statystyki dla konkretnej drużyny
    
    Endpoint zwraca statystyki meczowe drużyny:
    - Całkowita liczba meczów
    - Mecze u siebie vs na wyjeździe
    - Bilans zwycięstw/remisów/porażek
    - Bramki strzelone i stracone
    
    Opcjonalnie można filtrować wyniki według:
    - Sezonu (season_id)
    - Ostatnich N meczów (last_n_matches)
    
    Filtry można łączyć - najpierw filtruje się po sezonie, potem brane są ostatnie N meczów.
    """
    try:
        # Sprawdzenie czy drużyna istnieje
        team_query = """
        SELECT t.ID, t.NAME
        FROM teams t
        WHERE t.ID = %s
        """
        
        team_df = execute_query(team_query, (team_id,))
        
        if team_df.empty:
            raise HTTPException(status_code=404, detail="Team not found")
        
        team_name = team_df.iloc[0]['NAME']
        
        # Inicjalizacja zmiennych dla informacji o sezonie
        season_info = None
        season_years = None
        
        # Sprawdzenie sezonu jeśli podano
        if season_id is not None:
            season_query = """
            SELECT s.ID, s.YEARS
            FROM seasons s
            WHERE s.ID = %s
            """
            
            season_df = execute_query(season_query, (season_id,))
            
            if season_df.empty:
                raise HTTPException(status_code=404, detail="Season not found")
                
            season_info = season_id
            season_years = season_df.iloc[0]['YEARS']
        
        # Budowanie zapytania z opcjonalnymi filtrami
        if last_n_matches is not None:
            # Jeśli filtrujemy po ostatnich N meczach, najpierw pobieramy ID meczu
            # z użyciem subcquery aby ograniczyć zbiór danych przed obliczeniami

            subquery_where = ""
            subquery_params = []

            if season_id is not None:
                subquery_where = "AND SEASON = %s"
                subquery_params.append(season_id)

            # Zapytanie o statystyki z ograniczeniem do ostatnich N meczów
            stats_query = f"""
            SELECT 
                COUNT(*) as total_matches,
                SUM(CASE WHEN HOME_TEAM = %s THEN 1 ELSE 0 END) as home_matches,
                SUM(CASE WHEN AWAY_TEAM = %s THEN 1 ELSE 0 END) as away_matches,
                SUM(CASE 
                    WHEN (HOME_TEAM = %s AND RESULT = '1') OR (AWAY_TEAM = %s AND RESULT = '2') 
                    THEN 1 ELSE 0 
                END) as wins,
                SUM(CASE WHEN RESULT = 'X' THEN 1 ELSE 0 END) as draws,
                SUM(CASE 
                    WHEN (HOME_TEAM = %s AND RESULT = '2') OR (AWAY_TEAM = %s AND RESULT = '1') 
                    THEN 1 ELSE 0 
                END) as losses,
                SUM(CASE 
                    WHEN HOME_TEAM = %s THEN COALESCE(HOME_TEAM_GOALS, 0)
                    WHEN AWAY_TEAM = %s THEN COALESCE(AWAY_TEAM_GOALS, 0)
                    ELSE 0
                END) as goals_scored,
                SUM(CASE 
                    WHEN HOME_TEAM = %s THEN COALESCE(AWAY_TEAM_GOALS, 0)
                    WHEN AWAY_TEAM = %s THEN COALESCE(HOME_TEAM_GOALS, 0)
                    ELSE 0
                END) as goals_conceded
            FROM (
                SELECT * FROM matches 
                WHERE (HOME_TEAM = %s OR AWAY_TEAM = %s) 
                AND RESULT IN ('1', '2', 'X')
                {subquery_where}
                ORDER BY GAME_DATE DESC
                LIMIT %s
            ) as recent_matches
            """

            # Liczba parametrów: 12 dla głównego SELECT + 2 (team_id, team_id) + [season_id jeśli podano] + last_n_matches
            params_list = (
                [team_id] * 12 + subquery_params + [last_n_matches]
            )
            # Jeśli season_id podano, subquery_params ma 3 elementy, jeśli nie - 2
            # W zapytaniu subquery WHERE jest dodawane tylko jeśli season_id podano
            
        else:
            # Standardowe zapytanie bez ograniczenia do ostatnich N meczów
            where_clause = ""
            params_list = [team_id] * 12  # podstawowe parametry dla team_id
            
            if season_id is not None:
                where_clause = "AND SEASON = %s"
                params_list.append(season_id)
            
            stats_query = f"""
            SELECT 
                COUNT(*) as total_matches,
                SUM(CASE WHEN HOME_TEAM = %s THEN 1 ELSE 0 END) as home_matches,
                SUM(CASE WHEN AWAY_TEAM = %s THEN 1 ELSE 0 END) as away_matches,
                SUM(CASE 
                    WHEN (HOME_TEAM = %s AND RESULT = '1') OR (AWAY_TEAM = %s AND RESULT = '2') 
                    THEN 1 ELSE 0 
                END) as wins,
                SUM(CASE WHEN RESULT = 'X' THEN 1 ELSE 0 END) as draws,
                SUM(CASE 
                    WHEN (HOME_TEAM = %s AND RESULT = '2') OR (AWAY_TEAM = %s AND RESULT = '1') 
                    THEN 1 ELSE 0 
                END) as losses,
                SUM(CASE 
                    WHEN HOME_TEAM = %s THEN COALESCE(HOME_TEAM_GOALS, 0)
                    WHEN AWAY_TEAM = %s THEN COALESCE(AWAY_TEAM_GOALS, 0)
                    ELSE 0
                END) as goals_scored,
                SUM(CASE 
                    WHEN HOME_TEAM = %s THEN COALESCE(AWAY_TEAM_GOALS, 0)
                    WHEN AWAY_TEAM = %s THEN COALESCE(HOME_TEAM_GOALS, 0)
                    ELSE 0
                END) as goals_conceded
            FROM matches 
            WHERE (HOME_TEAM = %s OR AWAY_TEAM = %s) 
            AND RESULT IN ('1', '2', 'X')
            {where_clause}
            """
        stats_df = execute_query(stats_query, tuple(params_list))
        
        if stats_df.empty:
            # Jeśli brak meczów, zwróć zerowe statystyki
            return TeamStatsResponse(
                team_id=team_id,
                team_name=team_name,
                season_id=season_info,
                season_years=season_years,
                last_n_matches=last_n_matches,
                total_matches=0,
                home_matches=0,
                away_matches=0,
                wins=0,
                draws=0,
                losses=0,
                goals_scored=0,
                goals_conceded=0
            )
        
        stats_row = stats_df.iloc[0]
        
        return TeamStatsResponse(
            team_id=team_id,
            team_name=team_name,
            season_id=season_info,
            season_years=season_years,
            last_n_matches=last_n_matches,
            total_matches=int(stats_row['total_matches'] or 0),
            home_matches=int(stats_row['home_matches'] or 0),
            away_matches=int(stats_row['away_matches'] or 0),
            wins=int(stats_row['wins'] or 0),
            draws=int(stats_row['draws'] or 0),
            losses=int(stats_row['losses'] or 0),
            goals_scored=int(stats_row['goals_scored'] or 0),
            goals_conceded=int(stats_row['goals_conceded'] or 0)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Błąd w get_team_stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch team statistics")

@router.get("/{team_id}/btts", response_model=TeamBTTSResponse)
async def get_team_btts_stats(
    team_id: int,
    season_id: Optional[int] = Query(None, description="Season ID (optional filter)"),
    last_n_matches: Optional[int] = Query(
        None, ge=1, le=100,
        description="Last N matches (optional filter, max 100)")
) -> TeamBTTSResponse:
    """
    Pobiera statystyki BTTS (Both Teams To Score) dla konkretnej drużyny
    
    Endpoint zwraca:
    - Liczbę meczów, w których obie drużyny strzeliły (BTTS Tak)
    - Liczbę meczów, w których nie obie drużyny strzeliły (BTTS Nie)
    - Procentowe wartości dla obu kategorii
    
    Opcjonalnie można filtrować wyniki według:
    - Sezonu (season_id)
    - Ostatnich N meczów (last_n_matches)
    
    Filtry można łączyć - najpierw filtruje się po sezonie, potem brane są ostatnie N meczów.
    """
    try:
        # Sprawdzenie czy drużyna istnieje
        team_query = """
        SELECT t.ID, t.NAME
        FROM teams t
        WHERE t.ID = %s
        """
        
        team_df = execute_query(team_query, (team_id,))
        
        if team_df.empty:
            raise HTTPException(status_code=404, detail="Team not found")
        
        team_name = team_df.iloc[0]['NAME']
        
        # Inicjalizacja zmiennych dla informacji o sezonie
        season_info = None
        season_years = None
        
        # Sprawdzenie sezonu jeśli podano
        if season_id is not None:
            season_query = """
            SELECT s.ID, s.YEARS
            FROM seasons s
            WHERE s.ID = %s
            """
            
            season_df = execute_query(season_query, (season_id,))
            
            if season_df.empty:
                raise HTTPException(status_code=404, detail="Season not found")
                
            season_info = season_id
            season_years = season_df.iloc[0]['YEARS']
        
        # Budowanie zapytania z opcjonalnymi filtrami
        if last_n_matches is not None:
            # Jeśli filtrujemy po ostatnich N meczach, używamy subcquery
            
            subquery_where = ""
            subquery_params = [team_id, team_id]
            
            if season_id is not None:
                subquery_where = "AND SEASON = %s"
                subquery_params.append(season_id)
            
            # Zapytanie o statystyki BTTS z ograniczeniem do ostatnich N meczów
            btts_query = f"""
            SELECT 
                COUNT(*) as total_matches,
                SUM(CASE 
                    WHEN COALESCE(HOME_TEAM_GOALS, 0) > 0 AND COALESCE(AWAY_TEAM_GOALS, 0) > 0 
                    THEN 1 ELSE 0 
                END) as btts_yes,
                SUM(CASE 
                    WHEN COALESCE(HOME_TEAM_GOALS, 0) = 0 OR COALESCE(AWAY_TEAM_GOALS, 0) = 0 
                    THEN 1 ELSE 0 
                END) as btts_no
            FROM (
                SELECT * FROM matches 
                WHERE (HOME_TEAM = %s OR AWAY_TEAM = %s) 
                AND RESULT IN ('1', '2', 'X')
                AND HOME_TEAM_GOALS IS NOT NULL 
                AND AWAY_TEAM_GOALS IS NOT NULL
                {subquery_where}
                ORDER BY GAME_DATE DESC
                LIMIT %s
            ) as recent_matches
            """ 
            params_list = subquery_params + [last_n_matches]         
        else:
            where_clause = ""
            params_list = [team_id, team_id]  # podstawowe parametry dla team_id
            
            if season_id is not None:
                where_clause = "AND SEASON = %s"
                params_list.append(season_id)
            
            # Zapytanie o statystyki BTTS drużyny
            btts_query = f"""
            SELECT 
                COUNT(*) as total_matches,
                SUM(CASE 
                    WHEN COALESCE(HOME_TEAM_GOALS, 0) > 0 AND COALESCE(AWAY_TEAM_GOALS, 0) > 0 
                    THEN 1 ELSE 0 
                END) as btts_yes,
                SUM(CASE 
                    WHEN COALESCE(HOME_TEAM_GOALS, 0) = 0 OR COALESCE(AWAY_TEAM_GOALS, 0) = 0 
                    THEN 1 ELSE 0 
                END) as btts_no
            FROM matches 
            WHERE (HOME_TEAM = %s OR AWAY_TEAM = %s) 
            AND RESULT IN ('1', '2', 'X')
            AND HOME_TEAM_GOALS IS NOT NULL 
            AND AWAY_TEAM_GOALS IS NOT NULL
            {where_clause}
            """
        
        btts_df = execute_query(btts_query, tuple(params_list))
        
        if btts_df.empty or btts_df.iloc[0]['total_matches'] == 0:
            # Jeśli brak meczów, zwróć zerowe statystyki
            return TeamBTTSResponse(
                team_id=team_id,
                team_name=team_name,
                season_id=season_info,
                season_years=season_years,
                last_n_matches=last_n_matches,
                total_matches=0,
                btts_yes=0,
                btts_no=0,
                btts_yes_percentage=0.0,
                btts_no_percentage=0.0
            )
        
        btts_row = btts_df.iloc[0]
        total_matches = int(btts_row['total_matches'] or 0)
        btts_yes = int(btts_row['btts_yes'] or 0)
        btts_no = int(btts_row['btts_no'] or 0)
        
        # Obliczenie procentów
        btts_yes_percentage = round((btts_yes / total_matches * 100), 2) if total_matches > 0 else 0.0
        btts_no_percentage = round((btts_no / total_matches * 100), 2) if total_matches > 0 else 0.0
        
        return TeamBTTSResponse(
            team_id=team_id,
            team_name=team_name,
            season_id=season_info,
            season_years=season_years,
            last_n_matches=last_n_matches,
            total_matches=total_matches,
            btts_yes=btts_yes,
            btts_no=btts_no,
            btts_yes_percentage=btts_yes_percentage,
            btts_no_percentage=btts_no_percentage
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Błąd w get_team_btts_stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch team BTTS statistics")
    
@router.get("/head-to-head", response_model=HeadToHeadResponse)
async def get_head_to_head_stats(
    team_1_id: int = Query(..., description="First team ID"),
    team_2_id: int = Query(..., description="Second team ID"),
    last_n_meetings: Optional[int] = Query(
        5, ge=1, le=100,
        description="Number of recent meetings to include in statistics")
) -> HeadToHeadResponse:
    """
    Pobiera statystyki bezpośrednich pojedynków (H2H) między dwiema drużynami
    
    Endpoint zwraca:
    - Całkowitą liczbę meczów między drużynami
    - Liczbę zwycięstw dla każdej drużyny
    - Liczbę remisów
    - Ostatnie 5 spotkań z datami, wynikami i strzelonymi bramkami
    - Średnią liczbę bramek na mecz w meczach H2H
    - Procent meczów BTTS (Both Teams To Score) w meczach H2H
    
    Parametry:
    - team_1_id: ID pierwszej drużyny
    - team_2_id: ID drugiej drużyny
    - last_n_meetings: Opcjonalna liczba ostatnich spotkań do uwzględnienia w statystykach (domyślnie 5)
    """
    try:
        # Zapytanie o ostatnie N spotkań
        last_meetings_query = """
        SELECT 
            GAME_DATE,
            HOME_TEAM,
            AWAY_TEAM,
            HOME_TEAM_GOALS,
            AWAY_TEAM_GOALS,
            RESULT
        FROM matches
        WHERE ((HOME_TEAM = %s AND AWAY_TEAM = %s) OR (HOME_TEAM = %s AND AWAY_TEAM = %s)) AND RESULT != '0'
        ORDER BY GAME_DATE DESC
        LIMIT %s
        """
        last_meetings_df = execute_query(last_meetings_query, (team_1_id, team_2_id, team_2_id, team_1_id, last_n_meetings))
        last_meetings = []
        for _, row in last_meetings_df.iterrows():
            meeting = {
                "date": row['GAME_DATE'],
                "home_team": row['HOME_TEAM'],
                "away_team": row['AWAY_TEAM'],
                "home_team_goals": row['HOME_TEAM_GOALS'],
                "away_team_goals": row['AWAY_TEAM_GOALS'],
                "result": row['RESULT']
            }
            last_meetings.append(meeting)

        return HeadToHeadResponse(
            team_1_id=team_1_id,
            team_2_id=team_2_id,
            last_meetings=last_meetings,
        )
        
    except Exception as e:
        logger.error(f"Błąd w get_head_to_head_stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch head-to-head statistics")

@router.get("/{team_id}/hockey-stats", response_model=TeamHockeyStatsResponse)
async def get_team_hockey_stats(
    team_id: int,
    season_id: Optional[int] = Query(None, description="Season ID (optional filter)"),
    last_n_matches: Optional[int] = Query(
        None, ge=1, le=100,
        description="Last N matches (optional filter, max 100)")
) -> TeamHockeyStatsResponse:
    """
    Pobiera szczegółowe statystyki hokejowe dla konkretnej drużyny
    
    Endpoint zwraca statystyki hokejowe drużyny w tym:
    - Podstawowe statystyki meczowe
    - Statystyki dogrywek i karnych
    - Średnie statystyki strzałów, obron, przewag
    - Statystyki fauli i wznowień
    
    Opcjonalnie można filtrować wyniki według:
    - Sezonu (season_id) 
    - Ostatnich N meczów (last_n_matches)
    """
    try:
        # Sprawdzenie czy drużyna istnieje
        team_query = """
        SELECT t.ID, t.NAME, t.SPORT_ID
        FROM teams t
        WHERE t.ID = %s
        """
        
        team_df = execute_query(team_query, (team_id,))
        
        if team_df.empty:
            raise HTTPException(status_code=404, detail="Team not found")
        
        team_name = team_df.iloc[0]['NAME']
        sport_id = team_df.iloc[0]['SPORT_ID']
        
        # Sprawdzenie czy to drużyna hokejowa (sport_id = 2 dla hokeja)
        sport_query = """
        SELECT s.NAME FROM sports s WHERE s.ID = %s
        """
        sport_df = execute_query(sport_query, (int(sport_id),))
        
        if not sport_df.empty and 'hokej' not in sport_df.iloc[0]['NAME'].lower():
            raise HTTPException(status_code=400, detail="Hockey statistics are available only for hockey teams")
        
        # Sprawdzenie sezonu jeśli podano
        season_years = None
        if season_id is not None:
            season_query = """
            SELECT s.ID, s.YEARS
            FROM seasons s
            WHERE s.ID = %s
            """
            
            season_df = execute_query(season_query, (season_id,))
            
            if season_df.empty:
                raise HTTPException(status_code=404, detail="Season not found")
                
            season_years = season_df.iloc[0]['YEARS']
        
        # Budowanie zapytania z opcjonalnymi filtrami
        where_conditions = ["(m.HOME_TEAM = %s OR m.AWAY_TEAM = %s)", "m.RESULT IN ('1', '2', 'X')"]
        params = [team_id, team_id]
        
        if season_id is not None:
            where_conditions.append("m.SEASON = %s")
            params.append(season_id)
        
        # Jeśli filtrujemy po ostatnich N meczach
        if last_n_matches is not None:
            # Podkwerenda do znalezienia ID ostatnich N meczów
            match_ids_subquery = f"""
            SELECT m.ID 
            FROM matches m
            WHERE (m.HOME_TEAM = %s OR m.AWAY_TEAM = %s) 
            AND m.RESULT IN ('1', '2', 'X')
            {f"AND m.SEASON = %s" if season_id is not None else ""}
            ORDER BY m.GAME_DATE DESC 
            LIMIT %s
            """
            
            subquery_params = [team_id, team_id]
            if season_id is not None:
                subquery_params.append(season_id)
            subquery_params.append(last_n_matches)
            
            match_ids_df = execute_query(match_ids_subquery, tuple(subquery_params))
            
            if match_ids_df.empty:
                # Brak meczów - zwracamy zerowe statystyki
                return TeamHockeyStatsResponse(
                    team_id=team_id,
                    team_name=team_name,
                    season_id=season_id,
                    last_n_matches=last_n_matches,
                    total_matches=0,
                    wins=0,
                    losses=0,
                    overtime_wins=0,
                    overtime_loses=0,
                    goals_for=0,
                    goals_against=0,
                    overtime_matches=0,
                    shootout_matches=0,
                    avg_shots_on_target_for=0.0,
                    avg_shots_on_target_against=0.0,
                    avg_saves_percentage=0.0,
                    avg_powerplay_percentage=0.0,
                    avg_faceoff_percentage=0.0,
                    avg_hits_per_game=0.0
                )
            
            match_ids = tuple(match_ids_df['ID'].tolist())
            where_conditions.append(f"m.ID IN {match_ids}")
        
        where_clause = " AND ".join(where_conditions)
        
        # Zapytanie główne o statystyki meczowe
        main_query = f"""
        SELECT 
            m.ID,
            m.HOME_TEAM,
            m.AWAY_TEAM,
            m.HOME_TEAM_GOALS,
            m.AWAY_TEAM_GOALS,
            m.RESULT,
            hma.OT,
            hma.SO,
            m.home_team_sog,
            m.away_team_sog,
            hma.home_team_saves,
            hma.away_team_saves,
            hma.home_team_pp_goals,
            hma.away_team_pp_goals,
            hma.home_team_pp_acc,
            hma.away_team_pp_acc,
            hma.home_team_faceoffs,
            hma.away_team_faceoffs,
            hma.home_team_faceoffs_acc,
            hma.away_team_faceoffs_acc,
            hma.home_team_hits,
            hma.away_team_hits
        FROM matches m
        LEFT JOIN hockey_matches_add hma ON m.ID = hma.MATCH_ID
        WHERE {where_clause}
        ORDER BY m.GAME_DATE DESC
        """
        
        matches_df = execute_query(main_query, tuple(params))
        
        if matches_df.empty:
            # Brak meczów - zwracamy zerowe statystyki
            return TeamHockeyStatsResponse(
                team_id=team_id,
                team_name=team_name,
                season_id=season_id,
                last_n_matches=last_n_matches,
                total_matches=0,
                wins=0,
                losses=0,
                overtime_wins=0,
                overtime_loses=0,
                goals_for=0,
                goals_against=0,
                overtime_matches=0,
                shootout_matches=0,
                avg_shots_on_target_for=0.0,
                avg_shots_on_target_against=0.0,
                avg_saves_percentage=0.0,
                avg_powerplay_percentage=0.0,
                avg_faceoff_percentage=0.0,
                avg_hits_per_game=0.0
            )
        
        # Obliczenia statystyk
        total_matches = len(matches_df)
        wins = 0
        losses = 0
        overtime_wins = 0
        overtime_loses = 0
        goals_for = 0
        goals_against = 0
        overtime_matches = 0
        shootout_matches = 0
        shots_for_total = 0
        shots_against_total = 0
        saves_for_total = 0
        saves_against_total = 0
        pp_goals_for = 0
        pp_opportunities_for = 0
        faceoff_won_total = 0
        faceoff_total_total = 0
        hits_total = 0
        
        for _, match in matches_df.iterrows():
            is_home = match['HOME_TEAM'] == team_id
            
            # Bramki
            if is_home:
                goals_for += match['HOME_TEAM_GOALS'] or 0
                goals_against += match['AWAY_TEAM_GOALS'] or 0
                # Zwycięstwa/porażki
                if match['RESULT'] == '1':  # Zwycięstwo gospodarzy
                    wins += 1
                elif match['RESULT'] == '2':  # Zwycięstwo gości
                    losses += 1
                if match['OT'] == 1 or match['SO'] == 1:
                    overtime_wins += 1
                elif match['OT'] == 2 or match['SO'] == 2:
                    overtime_loses += 1
                # Statystyki hokejowe - poprawione nazwy kolumn
                if pd.notna(match['home_team_sog']):
                    shots_for_total += match['home_team_sog']
                if pd.notna(match['away_team_sog']):
                    shots_against_total += match['away_team_sog']
                if pd.notna(match['home_team_saves']):
                    saves_for_total += match['home_team_saves']
                if pd.notna(match['away_team_saves']):
                    saves_against_total += match['away_team_saves']
                if pd.notna(match['home_team_pp_goals']):
                    pp_goals_for += match['home_team_pp_goals']
                if pd.notna(match['home_team_pp_acc']):
                    pp_opportunities_for += match['home_team_pp_acc']
                if pd.notna(match['home_team_faceoffs']):
                    faceoff_won_total += match['home_team_faceoffs']
                if pd.notna(match['home_team_faceoffs_acc']):
                    faceoff_total_total += match['home_team_faceoffs_acc']
                if pd.notna(match['home_team_hits']):
                    hits_total += match['home_team_hits']
            else:
                goals_for += match['AWAY_TEAM_GOALS'] or 0
                goals_against += match['HOME_TEAM_GOALS'] or 0
                # Zwycięstwa/porażki
                if match['RESULT'] == '2':  # Zwycięstwo gości
                    wins += 1
                elif match['RESULT'] == '1':  # Zwycięstwo gospodarzy
                    losses += 1
                if match['OT'] == 2 or match['SO'] == 2:
                    overtime_wins += 1
                elif match['OT'] == 1 or match['SO'] == 1:
                    overtime_loses += 1
                # Statystyki hokejowe - poprawione nazwy kolumn
                if pd.notna(match['away_team_sog']):
                    shots_for_total += match['away_team_sog']
                if pd.notna(match['home_team_sog']):
                    shots_against_total += match['home_team_sog']
                if pd.notna(match['away_team_saves']):
                    saves_for_total += match['away_team_saves']
                if pd.notna(match['home_team_saves']):
                    saves_against_total += match['home_team_saves']
                if pd.notna(match['away_team_pp_goals']):
                    pp_goals_for += match['away_team_pp_goals']
                if pd.notna(match['away_team_pp_acc']):
                    pp_opportunities_for += match['away_team_pp_acc']
                if pd.notna(match['away_team_faceoffs']):
                    faceoff_won_total += match['away_team_faceoffs']
                if pd.notna(match['away_team_faceoffs_acc']):
                    faceoff_total_total += match['away_team_faceoffs_acc']
                if pd.notna(match['away_team_hits']):
                    hits_total += match['away_team_hits']
            
            # Dogrywki i karne
            if pd.notna(match['OT']) and match['OT'] == 1:
                overtime_matches += 1
            if pd.notna(match['SO']) and match['SO'] == 1:
                shootout_matches += 1
        
        # Obliczenia średnich
        avg_shots_on_target_for = round(shots_for_total / total_matches, 2) if total_matches > 0 else 0.0
        avg_shots_on_target_against = round(shots_against_total / total_matches, 2) if total_matches > 0 else 0.0
        
        # Skuteczność obron (saves / (saves + goals_against))
        total_shots_against = saves_for_total + goals_against
        avg_saves_percentage = round((saves_for_total / total_shots_against * 100), 2) if total_shots_against > 0 else 0.0
        
        # Skuteczność przewagi
        avg_powerplay_percentage = round((pp_goals_for / pp_opportunities_for * 100), 2) if pp_opportunities_for > 0 else 0.0
        
        # Skuteczność wznowień
        avg_faceoff_percentage = round((faceoff_won_total / faceoff_total_total * 100), 2) if faceoff_total_total > 0 else 0.0
        
        # Średnia uderzeń na mecz
        avg_hits_per_game = round(hits_total / total_matches, 2) if total_matches > 0 else 0.0
        
        return TeamHockeyStatsResponse(
            team_id=team_id,
            team_name=team_name,
            season_id=season_id,
            last_n_matches=last_n_matches,
            total_matches=total_matches,
            wins=wins,
            losses=losses,
            overtime_wins=overtime_wins,
            overtime_loses=overtime_loses,
            goals_for=goals_for,
            goals_against=goals_against,
            overtime_matches=overtime_matches,
            shootout_matches=shootout_matches,
            avg_shots_on_target_for=avg_shots_on_target_for,
            avg_shots_on_target_against=avg_shots_on_target_against,
            avg_saves_percentage=avg_saves_percentage,
            avg_powerplay_percentage=avg_powerplay_percentage,
            avg_faceoff_percentage=avg_faceoff_percentage,
            avg_hits_per_game=avg_hits_per_game
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Błąd w get_team_hockey_stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch hockey team statistics")

@router.get("/{team_id}/roster", response_model=HockeyTeamRosterResponse)
async def get_hockey_team_roster(team_id: int) -> HockeyTeamRosterResponse:
    """
    Pobiera aktualny skład drużyny hokejowej
    
    Endpoint zwraca pełny skład drużyny hokejowej z podziałem na:
    - Bramkarzy (G)
    - Obrońców (D) 
    - Napastników (LW, C, RW)
    
    Dla każdego zawodnika wyświetlane są:
    - Dane osobowe (imię, nazwisko)
    - Pozycja
    - Linia (1-4)
    - Linia przewagi (0/1/2)
    - Status kontuzji
    """
    try:
        # Sprawdzenie czy drużyna istnieje
        team_query = """
        SELECT t.ID, t.NAME, t.SPORT_ID
        FROM teams t
        WHERE t.ID = %s
        """
        
        team_df = execute_query(team_query, (team_id,))
        
        if team_df.empty:
            raise HTTPException(status_code=404, detail="Team not found")
        
        team_name = team_df.iloc[0]['NAME']
        sport_id = team_df.iloc[0]['SPORT_ID']
        
        # Sprawdzenie czy to drużyna hokejowa (sport_id = 2 dla hokeja)
        sport_query = """
        SELECT s.NAME FROM sports s WHERE s.ID = %s
        """
        sport_df = execute_query(sport_query, (int(sport_id),))
        
        if not sport_df.empty and 'hokej' not in sport_df.iloc[0]['NAME'].lower():
            raise HTTPException(status_code=400, detail="Roster is available only for hockey teams")
        
        # Zapytanie o aktualny skład drużyny
        roster_query = """
        SELECT 
            hr.PLAYER_ID,
            p.FIRST_NAME,
            p.LAST_NAME,
            p.COMMON_NAME,
            p.CURRENT_COUNTRY,
            p.EXTERNAL_ID,
            p.EXTERNAL_FLASH_ID,  
            hr.POSITION,
            hr.number,
            hr.LINE,
            hr.IS_INJURED
        FROM hockey_rosters hr
        JOIN players p ON hr.PLAYER_ID = p.ID
        WHERE hr.TEAM_ID = %s
        ORDER BY 
            hr.LINE ASC,
            CASE hr.POSITION 
                WHEN 'G' THEN 1 
                WHEN 'D' THEN 2 
                WHEN 'LW' THEN 3
                WHEN 'C' THEN 4
                WHEN 'RW' THEN 5
            END
        """
        
        roster_df = execute_query(roster_query, (team_id,))
        
        # Przetwarzanie składu na kategorie
        goalkeepers = []
        defensemen = []
        forwards = []
        injured_count = 0
        
        for _, player in roster_df.iterrows():
            is_injured = bool(player['IS_INJURED']) if pd.notna(player['IS_INJURED']) else False
            if is_injured:
                injured_count += 1
            
            player_data = HockeyPlayerRosterResponse(
                player_id=int(player['PLAYER_ID']),
                first_name=str(player['FIRST_NAME']) if pd.notna(player['FIRST_NAME']) else "",
                last_name=str(player['LAST_NAME']) if pd.notna(player['LAST_NAME']) else "",
                common_name=str(player['COMMON_NAME']) if pd.notna(player['COMMON_NAME']) else "",
                country=str(player['CURRENT_COUNTRY']) if pd.notna(player['CURRENT_COUNTRY']) else "",
                position=str(player['POSITION']) if pd.notna(player['POSITION']) else "",
                line=int(player['LINE']) if pd.notna(player['LINE']) else None,
                is_injured=is_injured
            )
            
            # Kategorizacja według pozycji
            if player['POSITION'] == 'G':
                goalkeepers.append(player_data)
            elif player['POSITION'] == 'D':
                defensemen.append(player_data)
            elif player['POSITION'] in ['LW', 'C', 'RW']:
                forwards.append(player_data)
            else:
                # Jeśli pozycja nieznana, domyślnie do napastników
                forwards.append(player_data)
        
        return HockeyTeamRosterResponse(
            team_id=team_id,
            team_name=team_name,
            goalkeepers=goalkeepers,
            defensemen=defensemen,
            forwards=forwards,
            injured_players=injured_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Błąd w get_team_roster: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch team roster")
