"""Pydantic schemas for prediction model metadata endpoints.

These schemas describe rows from the database MODELS table and related
event-family metadata. They are unrelated to ML artifacts stored under
the repository ``models/`` directory.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class EventFamilySummary(BaseModel):
    """Event family metadata."""

    id: int = Field(..., description="Event family ID")
    sport_id: int = Field(..., description="Sport ID")
    name: str = Field(..., description="Event family name")
    sport_name: str | None = Field(None, description="Sport name")
    description: str | None = Field(
        None,
        description="Event family description")


class EventFamilyListResponse(BaseModel):
    """Response for GET /models/event-families."""

    event_families: list[EventFamilySummary] = Field(
        ...,
        description="Event families")
    total_families: int = Field(..., description="Total families returned")


class EventFamilyMappingItem(BaseModel):
    """Mapping between an event and an event family."""

    id: int = Field(..., description="Mapping ID")
    event_id: int = Field(..., description="Event ID")
    event_family_id: int = Field(..., description="Event family ID")
    event_name: str | None = Field(None, description="Event name")
    family_name: str | None = Field(None, description="Event family name")


class EventFamilyEventsResponse(BaseModel):
    """Response for GET /models/event-family-mappings/{family_id}."""

    family_events: list[EventFamilyMappingItem] = Field(
        ...,
        description="Events in the family")
    total_events: int = Field(..., description="Total events returned")


class ModelSummary(BaseModel):
    """Prediction model metadata from the MODELS table."""

    id: int = Field(..., description="Model ID")
    name: str = Field(..., description="Model name")
    active: int = Field(..., description="Active flag (0/1)")
    sport_id: int = Field(..., description="Sport ID")
    sport_name: str | None = Field(None, description="Sport name")


class ModelListResponse(BaseModel):
    """Response for GET /models/models."""

    models: list[ModelSummary] = Field(..., description="Prediction models")
    total_models: int = Field(..., description="Total models returned")


class ModelEventFamily(BaseModel):
    """Event family supported by a model."""

    id: int = Field(..., description="Event family ID")
    sport_id: int = Field(..., description="Sport ID")
    name: str = Field(..., description="Event family name")


class ModelSupportedEvent(BaseModel):
    """Event supported by a model through family mappings."""

    id: int = Field(..., description="Event ID")
    name: str = Field(..., description="Event name")
    family_id: int = Field(..., description="Event family ID")
    family_name: str = Field(..., description="Event family name")


class ModelDetailsResponse(BaseModel):
    """Response for GET /models/models/{model_id}/details."""

    id: int = Field(..., description="Model ID")
    name: str = Field(..., description="Model name")
    active: int = Field(..., description="Active flag (0/1)")
    sport_id: int = Field(..., description="Sport ID")
    sport_name: str | None = Field(None, description="Sport name")
    event_families: list[ModelEventFamily] = Field(
        default_factory=list,
        description="Event families handled by the model")
    supported_events: list[ModelSupportedEvent] = Field(
        default_factory=list,
        description="Events supported by the model")
    total_events: int = Field(
        0,
        description="Number of supported events")
