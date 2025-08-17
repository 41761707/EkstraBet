import time
from fastapi import APIRouter, HTTPException
import pandas as pd
from pydantic import BaseModel, Field
import logging
from typing import Optional
from utils import get_db_connection, execute_query

logger = logging.getLogger(__name__)
router = APIRouter()


class EventFamilyResponse(BaseModel):
    """Model odpowiedzi dla pojedynczej rodziny zdarzeń"""
    id: int = Field(..., description="ID rodziny zdarzeń")
    sport_id: int = Field(..., description="ID sportu")
    name: str = Field(..., description="Nazwa rodziny zdarzeń")


class EventFamilyMappingResponse(BaseModel):
    """Model odpowiedzi dla mapowania zdarzenia do rodziny"""
    id: int = Field(..., description="ID mapowania")
    event_id: int = Field(..., description="ID zdarzenia")
    event_family_id: int = Field(..., description="ID rodziny zdarzeń")
    event_name: Optional[str] = Field(None, description="Nazwa zdarzenia")
    family_name: Optional[str] = Field(None, description="Nazwa rodziny")


class ModelFamilyResponse(BaseModel):
    """Model odpowiedzi dla powiązania modelu z rodziną zdarzeń"""
    id: int = Field(..., description="ID powiązania")
    model_id: int = Field(..., description="ID modelu")
    event_family_id: int = Field(..., description="ID rodziny zdarzeń")
    model_name: Optional[str] = Field(None, description="Nazwa modelu")
    family_name: Optional[str] = Field(None, description="Nazwa rodziny")


class DetailedModelResponse(BaseModel):
    """Szczegółowy model odpowiedzi dla modelu z wszystkimi powiązaniami"""
    id: int = Field(..., description="ID modelu")
    name: str = Field(..., description="Nazwa modelu")
    active: int = Field(..., description="Status aktywności modelu")
    sport_id: int = Field(..., description="ID sportu")
    sport_name: Optional[str] = Field(None, description="Nazwa sportu")
    event_families: list[EventFamilyResponse] = Field(
        default=[], description="Rodziny zdarzeń obsługiwane przez model")
    supported_events: list[dict] = Field(
        default=[], description="Wszystkie zdarzenia obsługiwane przez model")
    total_events: int = Field(
        0, description="Łączna liczba obsługiwanych zdarzeń")

# ==================== FUNKCJE POMOCNICZE ====================

def get_model_basic_info(model_id: int) -> dict:
    """
    Pobiera podstawowe informacje o modelu
    Args:
        model_id: ID modelu
    Returns:
        dict: Podstawowe informacje o modelu
    Raises:
        HTTPException: Gdy model nie zostanie znaleziony
    """
    try:
        query = """
        SELECT m.ID, m.NAME, m.ACTIVE, m.SPORT_ID, s.NAME as sport_name
        FROM models m
        LEFT JOIN sports s ON m.SPORT_ID = s.ID
        WHERE m.ID = %s
        """
        model_df = execute_query(query, (model_id,))
        if model_df.empty:
            raise HTTPException(
                status_code=404, detail="Model nie został znaleziony")
        model_row = model_df.iloc[0]
        return {
            "id": int(model_row['ID']),
            "name": str(model_row['NAME']),
            "active": int(model_row['ACTIVE']),
            "sport_id": int(model_row['SPORT_ID']),
            "sport_name": str(model_row['sport_name']) if pd.notna(model_row['sport_name']) else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Błąd w get_model_basic_info dla model_id {model_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Błąd pobierania podstawowych informacji o modelu")


def get_model_event_families(model_id: int) -> list[dict]:
    """
    Pobiera rodziny zdarzeń obsługiwane przez model
    Args:
        model_id: ID modelu

    Returns:
        list[dict]: Lista rodzin zdarzeń przypisanych do modelu
    """
    try:
        query = """
        SELECT ef.ID, ef.NAME, ef.SPORT_ID
        FROM event_families ef
        JOIN event_model_families emf ON ef.ID = emf.EVENT_FAMILY_ID
        WHERE emf.MODEL_ID = %s
        ORDER BY ef.NAME
        """
        families_df = execute_query(query, (model_id,))
        event_families = []
        for _, family in families_df.iterrows():
            event_families.append({
                "id": int(family['ID']),
                "sport_id": int(family['SPORT_ID']),
                "name": str(family['NAME'])
            })
        return event_families
    except Exception as e:
        logger.error(
            f"Błąd w get_model_event_families dla model_id {model_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Błąd pobierania rodzin zdarzeń modelu")


def get_model_supported_events(model_id: int) -> list[dict]:
    """
    Pobiera wszystkie zdarzenia obsługiwane przez model
    Args:
        model_id: ID modelu
    Returns:
        list[dict]: Lista wszystkich zdarzeń obsługiwanych przez model
    """
    try:
        query = """
        SELECT DISTINCT e.ID, e.NAME, ef.NAME as family_name
        FROM events e
        JOIN event_family_mappings efm ON e.ID = efm.EVENT_ID
        JOIN event_families ef ON efm.EVENT_FAMILY_ID = ef.ID
        JOIN event_model_families emf ON ef.ID = emf.EVENT_FAMILY_ID
        WHERE emf.MODEL_ID = %s
        ORDER BY ef.NAME, e.NAME
        """
        events_df = execute_query(query, (model_id,))
        supported_events = []
        for _, event in events_df.iterrows():
            supported_events.append({
                "id": int(event['ID']),
                "name": str(event['NAME']),
                "family_name": str(event['family_name'])
            })
        return supported_events
    except Exception as e:
        logger.error(
            f"Błąd w get_model_supported_events dla model_id {model_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Błąd pobierania zdarzeń obsługiwanych przez model")

# ==================== ENDPOINTY  =======================


@router.get("/models", tags=["Modele"])
async def helper_info():
    """Endpoint główny - informacje o module models"""
    return {
        "module": "EkstraBet Module API",
        "version": "1.0.0",
        "description": "API do zarządzania danymi o modelach",
        "endpoints": [
            "models/event-families - Lista rodzin zdarzeń",
            "models/event-family-mappings - Lista mapowań rodzin zdarzeń",
            "models/model-families - Lista powiązań modeli z rodzinami zdarzeń",
            "models/detailed-models - Lista szczegółowych modeli"
        ]
    }


@router.get("/models/event-families", tags=["Modele"])
async def get_event_families(sport_id: Optional[int] = None):
    """
    Pobiera listę rodzin zdarzeń
    Args:
        sport_id: Opcjonalny filtr według sportu
    Returns:
        Lista rodzin zdarzeń
    """
    try:
        query = """
        SELECT ef.ID, ef.SPORT_ID, ef.NAME, s.NAME as sport_name, ef.description
        FROM event_families ef
        LEFT JOIN sports s ON ef.SPORT_ID = s.ID
        """
        params = None
        if sport_id:
            query += " WHERE ef.SPORT_ID = %s"
            params = (sport_id,)
        query += " ORDER BY ef.ID"
        families_df = execute_query(query, params)
        families = []
        for _, row in families_df.iterrows():
            families.append({
                "id": int(row['ID']),
                "sport_id": int(row['SPORT_ID']),
                "name": str(row['NAME']),
                "sport_name": str(row['sport_name']) if pd.notna(row['sport_name']) else None,
                "description": str(row['description']) if pd.notna(row['description']) else None
            })
        return {
            "event_families": families,
            "total_families": len(families)
        }
    except Exception as e:
        logger.error(f"Błąd w get_event_families: {e}")
        raise HTTPException(
            status_code=500, detail="Błąd pobierania rodzin zdarzeń")


@router.get("/models/event-family-mappings/{family_id}", tags=["Modele"])
async def get_family_events(family_id: int):
    """
    Pobiera zdarzenia należące do danej rodziny
    Args:
        family_id: ID rodziny zdarzeń
    Returns:
        Lista zdarzeń w rodzinie
    """
    try:
        query = """
        SELECT efm.ID, efm.EVENT_ID, efm.EVENT_FAMILY_ID,
               e.NAME as event_name, ef.NAME as family_name
        FROM event_family_mappings efm
        LEFT JOIN events e ON efm.EVENT_ID = e.ID
        LEFT JOIN event_families ef ON efm.EVENT_FAMILY_ID = ef.ID
        WHERE efm.EVENT_FAMILY_ID = %s
        ORDER BY e.NAME
        """
        mappings_df = execute_query(query, (family_id,))
        mappings = []
        for _, row in mappings_df.iterrows():
            mappings.append({
                "id": int(row['ID']),
                "event_id": int(row['EVENT_ID']),
                "event_family_id": int(row['EVENT_FAMILY_ID']),
                "event_name": str(row['event_name']) if pd.notna(row['event_name']) else None,
                "family_name": str(row['family_name']) if pd.notna(row['family_name']) else None
            })
        return {
            "family_events": mappings,
            "total_events": len(mappings)
        }
    except Exception as e:
        logger.error(f"Błąd w get_family_events: {e}")
        raise HTTPException(
            status_code=500, detail="Błąd pobierania zdarzeń rodziny")


@router.get("/models/models", response_model=dict, tags=["Modele"])
async def get_models():
    """
    Pobiera listę dostępnych modeli predykcyjnych
    Returns:
        Lista dostępnych modeli z podstawowymi informacjami
    """
    try:
        query = """
        SELECT m.ID, m.NAME, m.ACTIVE, m.SPORT_ID, s.NAME as sport_name
        FROM models m
        LEFT JOIN sports s ON m.SPORT_ID = s.ID
        ORDER BY m.NAME
        """
        models_df = execute_query(query)
        models = []
        for _, row in models_df.iterrows():
            models.append({
                "id": int(row['ID']),
                "name": str(row['NAME']),
                "active": int(row['ACTIVE']),
                "sport_id": int(row['SPORT_ID']),
                "sport_name": str(row['sport_name']) if pd.notna(row['sport_name']) else None
            })
        return {
            "models": models,
            "total_models": len(models)
        }
    except Exception as e:
        logger.error(f"Błąd w get_models: {e}")
        raise HTTPException(
            status_code=500, detail="Błąd pobierania listy modeli")


@router.get("/models/models/{model_id}/details", tags=["Modele"])
async def get_model_details(model_id: int):
    """
    Pobiera szczegółowe informacje o modelu wraz z obsługiwanymi rodzinami zdarzeń
    Args:
        model_id: ID modelu
    Returns:
        Szczegółowe informacje o modelu
    """
    try:
        # Pobierz podstawowe informacje o modelu
        basic_info = get_model_basic_info(model_id)
        # Pobierz rodziny zdarzeń dla modelu
        event_families = get_model_event_families(model_id)
        # Pobierz wszystkie obsługiwane zdarzenia
        supported_events = get_model_supported_events(model_id)
        return {
            **basic_info,  # Rozpakuj podstawowe informacje
            "event_families": event_families,
            "supported_events": supported_events,
            "total_events": len(supported_events)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Błąd w get_model_details dla model_id {model_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Błąd pobierania szczegółów modelu")
