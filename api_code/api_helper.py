from fastapi import APIRouter, HTTPException
import mysql.connector
import db_module
import pandas as pd
from pydantic import BaseModel, Field
import logging
from contextlib import contextmanager
from typing import Optional

# Konfiguracja logowania
logger = logging.getLogger(__name__)

# Utworzenie routera dla endpointów pomocniczych
router = APIRouter()

# Modele Pydantic dla walidacji danych
class CountryResponse(BaseModel):
    """Model odpowiedzi dla pojedynczego kraju"""
    id: int = Field(..., description="ID kraju")
    name: str = Field(..., description="Nazwa kraju")
    short_name: Optional[str] = Field(None, description="Skrót nazwy kraju")
    emoji: Optional[str] = Field(None, description="Emoji flagi kraju")
    teams_count: int = Field(..., description="Liczba drużyn z tego kraju")

class CountriesListResponse(BaseModel):
    """Model odpowiedzi dla listy krajów"""
    countries: list[CountryResponse] = Field(..., description="Lista krajów")
    total_countries: int = Field(..., description="Całkowita liczba krajów")

class SportResponse(BaseModel):
    """Model odpowiedzi dla pojedynczego sportu"""
    id: int = Field(..., description="ID sportu")
    name: str = Field(..., description="Nazwa sportu")
    teams_count: int = Field(..., description="Liczba drużyn w tym sporcie")

class SportsListResponse(BaseModel):
    """Model odpowiedzi dla listy sportów"""
    sports: list[SportResponse] = Field(..., description="Lista sportów")
    total_sports: int = Field(..., description="Całkowita liczba sportów")

class SeasonResponse(BaseModel):
    """Model odpowiedzi dla pojedynczego sezonu"""
    id: int = Field(..., description="ID sezonu")
    years: str = Field(..., description="Lata sezonu (np. 2023/24)")
    matches_count: int = Field(..., description="Liczba meczów w sezonie")

class SeasonsListResponse(BaseModel):
    """Model odpowiedzi dla listy sezonów"""
    seasons: list[SeasonResponse] = Field(..., description="Lista sezonów")
    total_seasons: int = Field(..., description="Całkowita liczba sezonów")

@contextmanager
def get_db_connection():
    """Context manager do zarządzania połączeniami z bazą danych"""
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

def execute_query(query: str, params: tuple = None) -> pd.DataFrame:
    """Wykonuje zapytanie SQL i zwraca wynik jako DataFrame"""
    with get_db_connection() as conn:
        try:
            return pd.read_sql(query, conn, params=params)
        except Exception as e:
            logger.error(f"Błąd wykonania zapytania: {e}")
            raise HTTPException(status_code=500, detail="Błąd wykonania zapytania")

# ==================== ENDPOINTY POMOCNICZE ====================

@router.get("/helper", tags=["Pomocnicze"])
async def helper_info():
    """Endpoint główny - informacje o module helper"""
    return {
        "module": "EkstraBet Teams API",
        "version": "1.0.0",
        "description": "API do zarządzania pomocniczymi danymi",
        "endpoints": [
            "helper/countries - Lista krajów",
            "helper/sports - Lista sportów",
            "helper/seasons - Lista sezonów"
        ]
    }

@router.get("/helper/countries", response_model=CountriesListResponse, tags=["Pomocnicze"])
async def get_countries():
    """
    Pobiera listę wszystkich krajów w systemie
    
    Endpoint pomocniczy do pobierania dostępnych krajów
    dla filtrowania drużyn i innych danych.
    
    Returns:
        CountriesListResponse: Lista krajów z liczbą drużyn
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

@router.get("/helper/sports", response_model=SportsListResponse, tags=["Pomocnicze"])
async def get_sports():
    """
    Pobiera listę wszystkich sportów w systemie
    
    Endpoint pomocniczy do pobierania dostępnych sportów
    dla filtrowania drużyn i innych danych.
    
    Returns:
        SportsListResponse: Lista sportów z liczbą drużyn
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

@router.get("/helper/seasons", response_model=SeasonsListResponse, tags=["Pomocnicze"])
async def get_seasons():
    """
    Pobiera listę wszystkich sezonów w systemie
    
    Endpoint pomocniczy do pobierania dostępnych sezonów
    dla filtrowania statystyk drużyn i innych danych.
    
    Returns:
        SeasonsListResponse: Lista sezonów z liczbą meczów
    """
    try:
        query = """
        SELECT 
            s.ID as id,
            s.YEARS as years,
            COUNT(m.ID) as matches_count
        FROM seasons s
        LEFT JOIN matches m ON s.ID = m.SEASON
        GROUP BY s.ID, s.YEARS
        ORDER BY s.ID DESC
        """
        
        seasons_df = execute_query(query)
        
        seasons = []
        for _, row in seasons_df.iterrows():
            seasons.append({
                "id": int(row['id']),
                "years": str(row['years']),
                "matches_count": int(row['matches_count'] or 0)
            })
        
        return {
            "seasons": seasons,
            "total_seasons": len(seasons)
        }
        
    except Exception as e:
        logger.error(f"Błąd w get_seasons: {e}")
        raise HTTPException(status_code=500, detail="Błąd pobierania listy sezonów")
