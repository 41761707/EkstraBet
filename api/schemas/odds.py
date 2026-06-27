"""Pydantic schemas for bookmaker odds endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field

from api.schemas.prediction import EventFamilyRef


class OddsItem(BaseModel):
    """Unified odds row from ODDS, BOOKMAKERS and EVENTS tables."""

    id: int = Field(..., description="Odds row ID")
    match_id: int = Field(..., description="Match ID")
    bookmaker_id: int = Field(..., description="Bookmaker ID")
    bookmaker_name: str = Field(..., description="Bookmaker name")
    event_id: int = Field(..., description="Event ID")
    event_name: str = Field(..., description="Event name")
    event_family: EventFamilyRef | None = Field(
        None,
        description="Primary event family mapping")
    odds: float = Field(..., description="Decimal odds", ge=1.0)


class MatchOddsListResponse(BaseModel):
    """Response for GET /odds/match/{match_id}."""

    odds: list[OddsItem] = Field(..., description="Bookmaker odds")
    total_count: int = Field(..., description="Total odds rows")
    match_id: int = Field(..., description="Match ID")
