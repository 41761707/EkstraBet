"""Pydantic schemas for prediction endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EventFamilyRef(BaseModel):
    """Reference to an event family used to group betting events."""

    id: int = Field(..., description="Event family ID")
    name: str = Field(..., description="Event family name")


class PredictionItem(BaseModel):
    """Single raw model prediction."""

    id: int = Field(..., description="Prediction ID")
    match_id: int = Field(..., description="Match ID")
    event_id: int = Field(..., description="Event ID")
    event_name: str = Field(..., description="Event name")
    event_family: EventFamilyRef | None = Field(
        None,
        description="Primary event family mapping")
    model_id: int = Field(..., description="Model ID")
    model_name: str | None = Field(None, description="Model name")
    value: float = Field(..., description="Predicted probability", ge=0.0)


class PredictionSearchResponse(BaseModel):
    """Response for GET /predictions/search."""

    predictions: list[PredictionItem] = Field(
        ...,
        description="Matching predictions")
    total_count: int = Field(..., description="Total matching rows")
    filters_applied: dict[str, object] = Field(
        ...,
        description="Applied query filters")


class TeamPredictionItem(BaseModel):
    """Evaluated final prediction for a team match."""

    event_id: int = Field(..., description="Event ID")
    event_name: str = Field(..., description="Event name")
    event_family: EventFamilyRef | None = Field(
        None,
        description="Primary event family mapping")
    match_id: int = Field(..., description="Match ID")
    model_id: int = Field(..., description="Model ID")
    model_name: str | None = Field(None, description="Model name")
    value: float | None = Field(
        None,
        description="Predicted probability when available")
    outcome: int | None = Field(
        None,
        description="Prediction outcome (0/1) when evaluated")


class TeamPredictionListResponse(BaseModel):
    """Response for GET /predictions/team/{team_id}/{season_id}."""

    team_predictions: list[TeamPredictionItem] = Field(
        ...,
        description="Team predictions")
    total_count: int = Field(..., description="Total predictions returned")
    team_id: int = Field(..., description="Team ID")
    season_id: int = Field(..., description="Season ID")


class MatchPredictionItem(BaseModel):
    """Final prediction for a single match event and model."""

    prediction_id: int = Field(..., description="Prediction ID")
    event_id: int = Field(..., description="Event ID")
    event_name: str = Field(..., description="Event name")
    event_family: EventFamilyRef | None = Field(
        None,
        description="Primary event family mapping")
    model_id: int = Field(..., description="Model ID")
    model_name: str | None = Field(None, description="Model name")
    value: float | None = Field(
        None,
        description="Predicted probability when available")
    outcome: int | None = Field(
        None,
        description="Prediction outcome (0/1) when evaluated")


class MatchPredictionListResponse(BaseModel):
    """Response for GET /predictions/match/{match_id}."""

    match_predictions: list[MatchPredictionItem] = Field(
        ...,
        description="Match predictions")
    total_count: int = Field(..., description="Total predictions returned")
    match_id: int = Field(..., description="Match ID")
