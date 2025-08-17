# Szablon dla nowych modułów API EkstraBet
# Skopiuj ten plik i dostosuj do konkretnego modułu

from fastapi import APIRouter, HTTPException, Query
import pandas as pd
from pydantic import BaseModel, Field
import logging
from utils import get_db_connection, execute_query

# Konfiguracja logowania
logger = logging.getLogger(__name__)

# === MODELE PYDANTIC ===
# Tutaj definiuj modele odpowiedzi dla tego modułu

class ExampleResponse(BaseModel):
    """Przykładowy model odpowiedzi"""
    id: int = Field(..., description="ID rekordu")
    name: str = Field(..., description="Nazwa")

class ExampleListResponse(BaseModel):
    """Model odpowiedzi dla listy"""
    items: list[ExampleResponse]
    total_count: int = Field(..., description="Całkowita liczba")
    page: int = Field(..., description="Numer strony")
    page_size: int = Field(..., description="Rozmiar strony")

# === FUNKCJE POMOCNICZE ===
# Funkcje pomocnicze są importowane z utils.py

# === ROUTER ===
# Zmień prefix na odpowiedni dla tego modułu (np. "/leagues", "/matches")
router = APIRouter(prefix="/example", tags=["Przykład"])

@router.get("/", tags=["System"])
async def module_info():
    """Endpoint główny - informacje o module"""
    return {
        "module": "EkstraBet Example API",
        "version": "1.0.0", 
        "description": "Przykładowy moduł API",
        "endpoints": [
            "/example/all - Wszystkie rekordy",
            "/example/search - Wyszukiwanie z filtrami"
        ]
    }

@router.get("/all", response_model=ExampleListResponse)
async def get_all_items(
    page: int = Query(1, ge=1, description="Numer strony"),
    page_size: int = Query(50, ge=1, le=500, description="Rozmiar strony")
) -> ExampleListResponse:
    """
    Pobiera wszystkie rekordy z paginacją
    
    Dostosuj zapytanie SQL do konkretnej tabeli w bazie danych.
    """
    try:
        # Obliczenie offsetu dla paginacji
        offset = (page - 1) * page_size
        
        # ZMIEŃ ZAPYTANIE NA ODPOWIEDNIE DLA TEGO MODUŁU
        query = """
        SELECT 
            id,
            name
        FROM example_table
        ORDER BY name
        LIMIT %s OFFSET %s
        """
        
        count_query = "SELECT COUNT(*) as total FROM example_table"
        
        # Wykonanie zapytań
        items_df = execute_query(query, (page_size, offset))
        count_df = execute_query(count_query)
        
        # Konwersja wyników
        items_list = []
        for _, row in items_df.iterrows():
            item = ExampleResponse(
                id=int(row['id']),
                name=str(row['name'])
            )
            items_list.append(item)
        
        total_count = int(count_df.iloc[0]['total'])
        
        return ExampleListResponse(
            items=items_list,
            total_count=total_count,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Błąd w get_all_items: {e}")
        raise HTTPException(status_code=500, detail="Błąd pobierania listy")

# === INSTRUKCJE DODAWANIA NOWEGO MODUŁU ===
"""
1. Skopiuj ten plik jako api_{nazwa_modułu}.py
2. Zmień prefix w router = APIRouter(prefix="/nazwa_modułu", tags=["Tag"])
3. Zdefiniuj odpowiednie modele Pydantic dla tego modułu
4. Napisz zapytania SQL dostosowane do tabel tego modułu
5. Dodaj router do start_api.py:
   - from api_{nazwa_modułu} import router as {nazwa_modułu}_router
   - app.include_router({nazwa_modułu}_router)
6. Dodaj informacje o module do głównego endpointu w start_api.py
7. Dodaj testy do test_api.py
8. Zaktualizuj README.md
"""
