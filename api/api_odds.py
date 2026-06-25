# API EkstraBet - Moduł obsługi kursów
# Plik zawiera endpointy FastAPI do zarządzania danymi kursów
# Autor: System EkstraBet

from fastapi import APIRouter, HTTPException, Query, Path
import pandas as pd
from pydantic import BaseModel, Field
import logging
from typing import List
from utils import get_db_connection, execute_query

# Konfiguracja logowania
logger = logging.getLogger(__name__)

# === MODELE PYDANTIC ===

class OddsResponse(BaseModel):
    """Model odpowiedzi dla kursu"""
    bookmaker: str = Field(..., description="Nazwa bukmachera")
    event: str = Field(..., description="Nazwa zdarzenia/typu zakładu")
    odds: float = Field(..., description="Kurs dla danego zdarzenia", ge=1.0)

class OddsListResponse(BaseModel):
    """Model odpowiedzi dla listy kursów"""
    odds: List[OddsResponse] = Field(..., description="Lista kursów")
    total_count: int = Field(..., description="Całkowita liczba kursów")
    match_id: int = Field(..., description="ID meczu")

# === ROUTER ===
router = APIRouter(prefix="/odds", tags=["Kursy"])

@router.get("/", tags=["System"])
async def module_info():
    """Endpoint główny - informacje o module kursów"""
    return {
        "module": "EkstraBet Odds API",
        "version": "1.0.0", 
        "description": "Moduł API do obsługi kursów bukmacherskich",
        "endpoints": [
            "/odds/match/{match_id} - Wszystkie kursy dla danego meczu"
        ]
    }

@router.get("/match/{match_id}", response_model=OddsListResponse)
async def get_odds_for_match(
    match_id: int = Path(..., ge=1, description="ID meczu")
) -> OddsListResponse:
    """
    Pobiera wszystkie kursy dla danego meczu
    
    Zwraca listę kursów z nazwami bukmacherów i zdarzeń dla określonego meczu.
    """
    try:
        # Zapytanie zgodne z wymaganiami użytkownika
        query = f"""
            SELECT b.name as bookmaker, e.name as event, o.odds as odds 
            FROM odds o 
            JOIN bookmakers b ON o.bookmaker = b.id 
            JOIN events e ON o.event = e.id
            WHERE o.match_id = {match_id}
            ORDER BY b.name, e.name
        """
        
        # Wykonanie zapytania
        odds_df = execute_query(query)
        
        # Sprawdzenie, czy znaleziono jakiekolwiek kursy
        if odds_df.empty:
            # Sprawdzenie, czy mecz w ogóle istnieje
            match_check_query = f"SELECT id FROM matches WHERE id = {match_id}"
            match_check_df = execute_query(match_check_query)
            
            if match_check_df.empty:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Mecz o ID {match_id} nie został znaleziony"
                )
            else:
                # Mecz istnieje, ale nie ma kursów
                return OddsListResponse(
                    odds=[],
                    total_count=0,
                    match_id=match_id
                )
        
        # Konwersja wyników do modeli Pydantic
        odds_list = []
        for _, row in odds_df.iterrows():
            odds_item = OddsResponse(
                bookmaker=str(row['bookmaker']),
                event=str(row['event']),
                odds=float(row['odds'])
            )
            odds_list.append(odds_item)
        
        return OddsListResponse(
            odds=odds_list,
            total_count=len(odds_list),
            match_id=match_id
        )
        
    except HTTPException:
        # Przekazanie błędów HTTP dalej
        raise
    except Exception as e:
        logger.error(f"Błąd w get_odds_for_match dla meczu {match_id}: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Błąd pobierania kursów dla meczu {match_id}"
        )
