# API EkstraBet - Moduł obsługi drużyn
# Plik zawiera endpointy FastAPI do zarządzania danymi drużyn
# Autor: System EkstraBet

from fastapi import APIRouter, HTTPException, Query
import mysql.connector
import db_module
import pandas as pd
from pydantic import BaseModel, Field
import logging
from contextlib import contextmanager

# Konfiguracja logowania
logger = logging.getLogger(__name__)

# Modele Pydantic dla walidacji danych
class TeamResponse(BaseModel):
    """Model odpowiedzi dla pojedynczej drużyny"""
    id: int = Field(..., description="ID drużyny")
    name: str = Field(..., description="Nazwa drużyny")
    shortcut: str = Field(None, description="Skrót nazwy drużyny")
    country_id: int = Field(..., description="ID kraju")
    country_name: str = Field(None, description="Nazwa kraju")
    country_emoji: str = Field(None, description="Flaga kraju")
    sport_id: int = Field(..., description="ID sportu")
    sport_name: str = Field(None, description="Nazwa sportu")

class TeamsListResponse(BaseModel):
    """Model odpowiedzi dla listy drużyn"""
    teams: list[TeamResponse] = Field(..., description="Lista drużyn")
    total_count: int = Field(..., description="Całkowita liczba drużyn")
    page: int = Field(..., description="Numer strony")
    page_size: int = Field(..., description="Rozmiar strony")

class TeamStatsResponse(BaseModel):
    """Model odpowiedzi dla statystyk drużyny"""
    team_id: int = Field(..., description="ID drużyny")
    team_name: str = Field(..., description="Nazwa drużyny")
    total_matches: int = Field(..., description="Całkowita liczba meczów")
    home_matches: int = Field(..., description="Liczba meczów u siebie")
    away_matches: int = Field(..., description="Liczba meczów na wyjeździe")
    wins: int = Field(..., description="Liczba wygranych")
    draws: int = Field(..., description="Liczba remisów")
    losses: int = Field(..., description="Liczba przegranych")
    goals_scored: int = Field(..., description="Bramki strzelone")
    goals_conceded: int = Field(..., description="Bramki stracone")

# Połączenie z bazą danych
@contextmanager
def get_db_connection():
    """Context manager dla połączenia z bazą danych"""
    conn = None
    try:
        conn = db_module.db_connect()
        yield conn
    except mysql.connector.Error as e:
        logger.error(f"Błąd połączenia z bazą danych: {e}")
        raise HTTPException(status_code=500, detail="Błąd połączenia z bazą danych")
    finally:
        if conn and conn.is_connected():
            conn.close()

# Funkcje pomocnicze
def execute_query(query: str, params: tuple = None) -> pd.DataFrame:
    """Wykonuje zapytanie SQL i zwraca wynik jako DataFrame"""
    with get_db_connection() as conn:
        try:
            return pd.read_sql(query, conn, params=params)
        except Exception as e:
            logger.error(f"Błąd wykonania zapytania: {e}")
            raise HTTPException(status_code=500, detail="Błąd wykonania zapytania")

# Inicjalizacja routera dla modułu teams
router = APIRouter(prefix="/teams", tags=["Drużyny"])

@router.get("/", tags=["System"])
async def teams_info():
    """Endpoint główny - informacje o module teams"""
    return {
        "module": "EkstraBet Teams API",
        "version": "1.0.0",
        "description": "API do zarządzania danymi drużyn",
        "endpoints": [
            "/teams/all - Wszystkie drużyny",
            "/teams/search - Wyszukiwanie drużyn z filtrami",
            "/teams/{team_id}/stats - Statystyki drużyny",
            "/teams/countries - Lista krajów",
            "/teams/sports - Lista sportów"
        ]
    }

@router.get("/all", response_model=TeamsListResponse)
async def get_all_teams(
    page: int = Query(1, ge=1, description="Numer strony"),
    page_size: int  = Query(50, ge=1, le=500, description="Rozmiar strony")
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
        ORDER BY t.country, t.NAME
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
        raise HTTPException(status_code=500, detail="Błąd pobierania listy drużyn")

@router.get("/search", response_model=TeamsListResponse)
async def get_specific_teams(
    country_id = Query(None, description="ID kraju"),
    country_name = Query(None, description="Nazwa kraju (częściowe dopasowanie)"),
    sport_id = Query(None, description="ID sportu"),
    sport_name = Query(None, description="Nazwa sportu (częściowe dopasowanie)"),
    team_name = Query(None, description="Nazwa drużyny (częściowe dopasowanie)"),
    team_shortcut = Query(None, description="Skrót drużyny"),
    page: int = Query(1, ge=1, description="Numer strony"),
    page_size: int = Query(50, ge=1, le=500, description="Rozmiar strony")
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
        ORDER BY t.country, t.NAME
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
        raise HTTPException(status_code=500, detail="Błąd wyszukiwania drużyn")

@router.get("/{team_id}/stats", response_model=TeamStatsResponse, tags=["Statystyki"])
async def get_team_stats(team_id: int) -> TeamStatsResponse:
    """
    Pobiera szczegółowe statystyki dla konkretnej drużyny
    
    Endpoint zwraca statystyki meczowe drużyny:
    - Całkowita liczba meczów
    - Mecze u siebie vs na wyjeździe
    - Bilans zwycięstw/remisów/porażek
    - Bramki strzelone i stracone
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
            raise HTTPException(status_code=404, detail="Drużyna nie została znaleziona")
        
        team_name = team_df.iloc[0]['NAME']
        
        # Zapytanie o statystyki drużyny
        stats_query = """
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
        """
        
        stats_params = (team_id,) * 12  # 12 razy team_id w zapytaniu
        stats_df = execute_query(stats_query, stats_params)
        
        if stats_df.empty:
            # Jeśli brak meczów, zwróć zerowe statystyki
            return TeamStatsResponse(
                team_id=team_id,
                team_name=team_name,
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
        raise HTTPException(status_code=500, detail="Błąd pobierania statystyk drużyny")

@router.get("/countries", tags=["Pomocnicze"])
async def get_countries():
    """
    Pobiera listę wszystkich krajów w systemie
    
    Endpoint pomocniczy do pobierania dostępnych krajów
    dla filtrowania drużyn.
    """
    try:
        query = """
        SELECT 
            c.ID as id,
            c.NAME as name,
            c.SHORT as short_name,
            c.EMOJI as emoji,
            COUNT(t.ID) as teams_count
        FROM countries c
        LEFT JOIN teams t ON c.ID = t.COUNTRY
        GROUP BY c.ID, c.NAME, c.SHORT, c.EMOJI
        ORDER BY c.NAME
        """
        
        countries_df = execute_query(query)
        
        countries = []
        for _, row in countries_df.iterrows():
            countries.append({
                "id": int(row['id']),
                "name": str(row['name']),
                "short_name": str(row['short_name']) if pd.notna(row['short_name']) else None,
                "emoji": str(row['emoji']) if pd.notna(row['emoji']) else None,
                "teams_count": int(row['teams_count'] or 0)
            })
        
        return {
            "countries": countries,
            "total_countries": len(countries)
        }
        
    except Exception as e:
        logger.error(f"Błąd w get_countries: {e}")
        raise HTTPException(status_code=500, detail="Błąd pobierania listy krajów")

@router.get("/sports", tags=["Pomocnicze"])
async def get_sports():
    """
    Pobiera listę wszystkich sportów w systemie
    
    Endpoint pomocniczy do pobierania dostępnych sportów
    dla filtrowania drużyn.
    """
    try:
        query = """
        SELECT 
            s.ID as id,
            s.NAME as name,
            COUNT(t.ID) as teams_count
        FROM sports s
        LEFT JOIN teams t ON s.ID = t.SPORT_ID
        GROUP BY s.ID, s.NAME
        ORDER BY s.NAME
        """
        
        sports_df = execute_query(query)
        
        sports = []
        for _, row in sports_df.iterrows():
            sports.append({
                "id": int(row['id']),
                "name": str(row['name']),
                "teams_count": int(row['teams_count'] or 0)
            })
        
        return {
            "sports": sports,
            "total_sports": len(sports)
        }
        
    except Exception as e:
        logger.error(f"Błąd w get_sports: {e}")
        raise HTTPException(status_code=500, detail="Błąd pobierania listy sportów")
