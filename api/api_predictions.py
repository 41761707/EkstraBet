# API EkstraBet - Moduł obsługi predykcji
# Plik zawiera endpointy FastAPI do zarządzania danymi predykcji
# Autor: System EkstraBet

from fastapi import APIRouter, HTTPException, Query, Path
import pandas as pd
from pydantic import BaseModel, Field
import logging
from typing import List, Optional
from utils import get_db_connection, execute_query

# Konfiguracja logowania
logger = logging.getLogger(__name__)

# === MODELE PYDANTIC ===

class PredictionResponse(BaseModel):
    """Model odpowiedzi dla predykcji"""
    id: int = Field(..., description="ID predykcji")
    match_id: int = Field(..., description="ID meczu")
    event_id: int = Field(..., description="ID zdarzenia")
    event_name: str = Field(..., description="Nazwa zdarzenia")
    model_id: int = Field(..., description="ID modelu")
    value: float = Field(..., description="Wartość predykcji", ge=0.0)

class PredictionListResponse(BaseModel):
    """Model odpowiedzi dla listy predykcji"""
    predictions: List[PredictionResponse] = Field(..., description="Lista predykcji")
    total_count: int = Field(..., description="Całkowita liczba predykcji")
    filters_applied: dict = Field(..., description="Zastosowane filtry")

class TeamPredictionResponse(BaseModel):
    """Model odpowiedzi dla predykcji drużyny"""
    event_id: int = Field(..., description="ID zdarzenia")
    outcome: Optional[int] = Field(None, description="Wynik predykcji (0 - niepoprawna, 1 - poprawna, None - nie oceniona)")
    match_id: int = Field(..., description="ID meczu")
    event_name: str = Field(..., description="Nazwa zdarzenia")


class TeamPredictionListResponse(BaseModel):
    """Model odpowiedzi dla listy predykcji drużyny"""
    team_predictions: List[TeamPredictionResponse] = Field(..., description="Lista predykcji drużyny")
    total_count: int = Field(..., description="Całkowita liczba predykcji")
    team_id: int = Field(..., description="ID drużyny")
    season_id: int = Field(..., description="ID sezonu")

class MatchPredictionResponse(BaseModel):
    """Model odpowiedzi dla predykcji meczu"""
    event_id: int = Field(..., description="ID zdarzenia")
    name: str = Field(..., description="Nazwa zdarzenia")
    outcome: Optional[int] = Field(None, description="Wynik predykcji (0 - niepoprawna, 1 - poprawna, None - nie oceniona)")
    model_id: int = Field(..., description="ID modelu")

class MatchPredictionListResponse(BaseModel):
    """Model odpowiedzi dla listy predykcji meczu"""
    match_predictions: List[MatchPredictionResponse] = Field(..., description="Lista predykcji meczu")
    total_count: int = Field(..., description="Całkowita liczba predykcji")
    match_id: int = Field(..., description="ID meczu")

# === ROUTER ===
router = APIRouter(prefix="/predictions", tags=["Predykcje"])

@router.get("/", tags=["System"])
async def module_info():
    """Endpoint główny - informacje o module predykcji"""
    return {
        "module": "EkstraBet Predictions API",
        "version": "1.0.0", 
        "description": "Moduł API do obsługi predykcji modeli",
        "endpoints": [
            "/predictions/search - Wyszukiwanie predykcji z opcjonalnymi filtrami",
            "/predictions/team/{team_id}/{season_id} - Predykcje dla drużyny w danym sezonie",
            "/predictions/match/{match_id} - Końcowe predykcje dla pojedynczego meczu"
        ]
    }

@router.get("/search", response_model=PredictionListResponse)
async def search_predictions(
    match_id: Optional[int] = Query(None, ge=1, description="ID meczu (opcjonalne)"),
    event_id: Optional[int] = Query(None, ge=1, description="ID zdarzenia (opcjonalne)"),
    model_ids: Optional[str] = Query(None, description="Lista ID modeli oddzielona przecinkami (opcjonalne), np. '1,2,3'"),
    page: int = Query(1, ge=1, description="Numer strony"),
    page_size: int = Query(50, ge=1, le=500, description="Rozmiar strony")
) -> PredictionListResponse:
    """
    Wyszukuje predykcje z opcjonalnymi filtrami
    
    Wszystkie filtry są opcjonalne - użytkownik może podać dowolną kombinację:
    - match_id: filtruje po ID meczu
    - event_id: filtruje po ID zdarzenia  
    - model_ids: filtruje po ID modeli (lista oddzielona przecinkami)
    """
    try:
        # Budowanie zapytania z dynamicznymi filtrami
        where_clauses = []
        params = []
        
        # Filtr po ID meczu
        if match_id is not None:
            where_clauses.append("match_id = %s")
            params.append(match_id)
        
        # Filtr po ID zdarzenia
        if event_id is not None:
            where_clauses.append("event_id = %s")
            params.append(event_id)
        
        # Filtr po ID modeli
        parsed_model_ids = None
        if model_ids is not None:
            try:
                # Parsowanie listy ID modeli z stringa
                parsed_model_ids = [int(mid.strip()) for mid in model_ids.split(',')]
                if parsed_model_ids:
                    placeholders = ','.join(['%s'] * len(parsed_model_ids))
                    where_clauses.append(f"model_id IN ({placeholders})")
                    params.extend(parsed_model_ids)
            except ValueError:
                raise HTTPException(
                    status_code=400, 
                    detail="Nieprawidłowy format model_ids. Użyj formatu: '1,2,3'"
                )
        
        # Budowanie klauzuli WHERE
        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)
        
        # Obliczenie offsetu dla paginacji
        offset = (page - 1) * page_size
        
        # Główne zapytanie z paginacją
        query = f"""
        SELECT p.id, p.match_id, p.event_id, e.name as event_name, p.model_id, p.value
        FROM predictions p
        JOIN events e ON p.event_id = e.id
        {where_sql}
        ORDER BY p.match_id, p.event_id, p.model_id
        LIMIT %s OFFSET %s
        """
        
        # Zapytanie zliczające
        count_query = f"""
        SELECT COUNT(*) as total 
        FROM predictions 
        {where_sql}
        """
        
        # Dodanie parametrów paginacji do głównego zapytania
        query_params = params + [page_size, offset]
        count_params = params
        
        # Wykonanie zapytań
        predictions_df = execute_query(query, query_params)
        count_df = execute_query(count_query, count_params)
        
        # Konwersja wyników do modeli Pydantic
        predictions_list = []
        for _, row in predictions_df.iterrows():
            prediction = PredictionResponse(
                id=int(row['id']),
                match_id=int(row['match_id']),
                event_id=int(row['event_id']),
                event_name=str(row['event_name']),
                model_id=int(row['model_id']),
                value=float(row['value'])
            )
            predictions_list.append(prediction)
        
        total_count = int(count_df.iloc[0]['total'])
        
        # Informacje o zastosowanych filtrach
        filters_applied = {
            "match_id": match_id,
            "event_id": event_id,
            "model_ids": parsed_model_ids,
            "page": page,
            "page_size": page_size
        }
        
        return PredictionListResponse(
            predictions=predictions_list,
            total_count=total_count,
            filters_applied=filters_applied
        )
        
    except HTTPException:
        # Przekazanie błędów HTTP dalej
        raise
    except Exception as e:
        logger.error(f"Błąd w search_predictions: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Błąd wyszukiwania predykcji"
        )

@router.get("/team/{team_id}/{season_id}", response_model=TeamPredictionListResponse)
async def get_team_predictions(
    team_id: int = Path(..., ge=1, description="ID drużyny"),
    season_id: int = Path(..., ge=1, description="ID sezonu")
) -> TeamPredictionListResponse:
    """
    Pobiera predykcje dla drużyny w danym sezonie
    
    Zwraca listę predykcji z wynikami (poprawne/niepoprawne) dla meczów drużyny w określonym sezonie.
    Uwzględniane są tylko mecze z wynikiem (nie równym '0').
    """
    try:
        # Zapytanie zgodne z wymaganiami użytkownika
        query = f"""
            SELECT p.event_id, f.outcome, e.name as event_name, m.id as match_id
            FROM predictions p 
            JOIN final_predictions f ON p.id = f.predictions_id 
            JOIN matches m ON m.id = p.match_id 
            JOIN events e ON e.id = p.event_id
            WHERE (m.home_team = %s OR m.away_team = %s) 
            AND m.season = %s
            AND m.result != '0' 
            ORDER BY m.game_date DESC
        """
        
        # Wykonanie zapytania
        predictions_df = execute_query(query, (team_id, team_id, season_id))
        
        # Sprawdzenie, czy znaleziono jakiekolwiek predykcje
        if predictions_df.empty:
            # Sprawdzenie, czy drużyna i sezon w ogóle istnieją
            team_check_query = "SELECT id FROM teams WHERE id = %s"
            season_check_query = "SELECT id FROM seasons WHERE id = %s"
            
            team_check_df = execute_query(team_check_query, (team_id,))
            season_check_df = execute_query(season_check_query, (season_id,))
            
            if team_check_df.empty:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Drużyna o ID {team_id} nie została znaleziona"
                )
            
            if season_check_df.empty:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Sezon o ID {season_id} nie został znaleziony"
                )
            
            # Drużyna i sezon istnieją, ale nie ma predykcji
            return TeamPredictionListResponse(
                team_predictions=[],
                total_count=0,
                team_id=team_id,
                season_id=season_id
            )
        
        # Konwersja wyników do modeli Pydantic
        team_predictions_list = []
        for _, row in predictions_df.iterrows():
            # Obsługa wartości NULL dla outcome
            outcome_value = None
            if row['outcome'] is not None:
                outcome_value = int(row['outcome'])
            
            prediction = TeamPredictionResponse(
                event_id=int(row['event_id']),
                outcome=outcome_value,
                match_id=int(row['match_id']),
                event_name=str(row['event_name'])
            )
            team_predictions_list.append(prediction)
        
        return TeamPredictionListResponse(
            team_predictions=team_predictions_list,
            total_count=len(team_predictions_list),
            team_id=team_id,
            season_id=season_id
        )
        
    except HTTPException:
        # Przekazanie błędów HTTP dalej
        raise
    except Exception as e:
        logger.error(f"Błąd w get_team_predictions dla drużyny {team_id}, sezon {season_id}: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Błąd pobierania predykcji dla drużyny {team_id} w sezonie {season_id}"
        )

@router.get("/match/{match_id}", response_model=MatchPredictionListResponse)
async def get_match_predictions(
    match_id: int = Path(..., ge=1, description="ID meczu")
) -> MatchPredictionListResponse:
    """
    Pobiera końcowe predykcje dla pojedynczego meczu
    
    Zwraca listę predykcji z wynikami (poprawne/niepoprawne) dla wszystkich zdarzeń w danym meczu.
    """
    try:
        # Zapytanie zgodne z wymaganiami użytkownika
        query = """
            SELECT p.event_id as event_id, e.name as name, fp.outcome, p.model_id 
            FROM predictions p 
            JOIN final_predictions fp ON p.id = fp.predictions_id
            JOIN events e ON p.event_id = e.id 
            WHERE p.match_id = %s
            ORDER BY p.event_id, p.model_id
        """
        
        # Wykonanie zapytania
        predictions_df = execute_query(query, (match_id,))
        
        # Sprawdzenie, czy znaleziono jakiekolwiek predykcje
        if predictions_df.empty:
            # Sprawdzenie, czy mecz w ogóle istnieje
            match_check_query = "SELECT id FROM matches WHERE id = %s"
            match_check_df = execute_query(match_check_query, (match_id,))
            
            if match_check_df.empty:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Mecz o ID {match_id} nie został znaleziony"
                )
            
            # Mecz istnieje, ale nie ma predykcji
            return MatchPredictionListResponse(
                match_predictions=[],
                total_count=0,
                match_id=match_id
            )
        
        # Konwersja wyników do modeli Pydantic
        match_predictions_list = []
        for _, row in predictions_df.iterrows():
            # Obsługa wartości NULL dla outcome
            outcome_value = None
            if row['outcome'] is not None:
                outcome_value = int(row['outcome'])
            
            prediction = MatchPredictionResponse(
                event_id=int(row['event_id']),
                name=str(row['name']),
                outcome=outcome_value,
                model_id=int(row['model_id'])
            )
            match_predictions_list.append(prediction)
        
        return MatchPredictionListResponse(
            match_predictions=match_predictions_list,
            total_count=len(match_predictions_list),
            match_id=match_id
        )
        
    except HTTPException:
        # Przekazanie błędów HTTP dalej
        raise
    except Exception as e:
        logger.error(f"Błąd w get_match_predictions dla meczu {match_id}: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Błąd pobierania predykcji dla meczu {match_id}"
        )
