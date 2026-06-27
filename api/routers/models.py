"""Prediction model metadata endpoints for the EkstraBet API.

This router exposes database metadata about prediction models, event families
and event mappings
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Path, Query

from api.schemas.model_metadata import (
    EventFamilyEventsResponse,
    EventFamilyListResponse,
    EventFamilyMappingItem,
    EventFamilySummary,
    ModelDetailsResponse,
    ModelEventFamily,
    ModelListResponse,
    ModelSummary,
    ModelSupportedEvent)
from backend.services import model_metadata_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/models", tags=["Model metadata"])


@router.get("/", tags=["System"])
async def model_metadata_info() -> dict[str, object]:
    """Return module metadata and available endpoints."""
    return {
        "module": "EkstraBet Model Metadata API",
        "version": "1.0.0",
        "description": (
            "Database metadata for prediction models and event families. "
            "Not related to ML artifacts in the models/ directory."),
        "endpoints": [
            "GET /models/event-families - Event families",
            "GET /models/event-family-mappings/{family_id} - Family events",
            "GET /models/models - Prediction model list",
            "GET /models/models/{model_id}/details - Model details",
        ],
    }


@router.get("/event-families", response_model=EventFamilyListResponse)
async def get_event_families(
    sport_id: int | None = Query(
        None,
        ge=1,
        description="Optional sport ID filter")
) -> EventFamilyListResponse:
    """Return event families with optional sport filter."""
    try:
        families = model_metadata_service.get_event_families(sport_id)
        summaries = [EventFamilySummary(**family) for family in families]
        return EventFamilyListResponse(
            event_families=summaries,
            total_families=len(summaries))
    except Exception as exc:
        logger.error("Failed to fetch event families: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch event families") from exc


@router.get(
    "/event-family-mappings/{family_id}",
    response_model=EventFamilyEventsResponse)
async def get_family_events(
    family_id: int = Path(..., ge=1, description="Event family ID")
) -> EventFamilyEventsResponse:
    """Return events mapped to the given event family."""
    try:
        events = model_metadata_service.get_family_events(family_id)
        mappings = [
            EventFamilyMappingItem(**event)
            for event in events
        ]
        return EventFamilyEventsResponse(
            family_events=mappings,
            total_events=len(mappings))
    except Exception as exc:
        logger.error(
            "Failed to fetch events for family %s: %s",
            family_id,
            exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch family events") from exc


@router.get("/models", response_model=ModelListResponse)
async def get_models() -> ModelListResponse:
    """Return prediction models from the database MODELS table."""
    try:
        models = model_metadata_service.get_models()
        summaries = [ModelSummary(**model) for model in models]
        return ModelListResponse(
            models=summaries,
            total_models=len(summaries))
    except Exception as exc:
        logger.error("Failed to fetch models: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch models") from exc


@router.get("/models/{model_id}/details", response_model=ModelDetailsResponse)
async def get_model_details(
    model_id: int = Path(..., ge=1, description="Model ID")
) -> ModelDetailsResponse:
    """Return model metadata with supported event families and events."""
    try:
        details = model_metadata_service.get_model_details(model_id)
        if details is None:
            raise HTTPException(
                status_code=404,
                detail=f"Model {model_id} not found")
        return ModelDetailsResponse(
            id=details["id"],
            name=details["name"],
            active=details["active"],
            sport_id=details["sport_id"],
            sport_name=details["sport_name"],
            event_families=[
                ModelEventFamily(**family)
                for family in details["event_families"]
            ],
            supported_events=[
                ModelSupportedEvent(**event)
                for event in details["supported_events"]
            ],
            total_events=details["total_events"])
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to fetch model details for %s: %s",
            model_id,
            exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch model details") from exc
