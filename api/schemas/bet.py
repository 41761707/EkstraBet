"""Pydantic schemas for bet recommendation endpoints."""

from __future__ import annotations
from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, Field
from api.schemas.match import TeamInMatch
from api.schemas.prediction import EventFamilyRef

SettlementStatus = Literal["pending", "won", "lost"]
BetSortBy = Literal["ev", "probability", "game_date"]
BetSortOrder = Literal["asc", "desc"]


class BetRecommendation(BaseModel):
    """Single bet recommendation with EV and settlement metadata."""

    bet_id: int = Field(..., description="Bet row ID")
    match_id: int = Field(..., description="Match ID")
    league_id: int = Field(..., description="League ID")
    league_name: str = Field(..., description="League name")
    season_id: int = Field(..., description="Season ID")
    game_date: datetime | date = Field(..., description="Match kick-off date")
    home_team: TeamInMatch = Field(..., description="Home team")
    away_team: TeamInMatch = Field(..., description="Away team")
    event_id: int = Field(..., description="Event ID")
    event_name: str = Field(..., description="Event name")
    event_family: EventFamilyRef | None = Field(
        None,
        description="Primary event family mapping")
    odds: float = Field(..., description="Decimal odds", ge=1.0)
    probability: float = Field(
        ...,
        description="Model probability in 0-1 range",
        ge=0.0,
        le=1.0)
    probability_pct: float = Field(
        ...,
        description="Model probability as percentage",
        ge=0.0,
        le=100.0)
    ev: float = Field(..., description="Expected value from database")
    ev_after_tax: float | None = Field(
        None,
        description="EV after 12% betting tax when apply_tax is enabled")
    bookmaker_id: int | None = Field(None, description="Bookmaker ID")
    bookmaker_name: str | None = Field(None, description="Bookmaker name")
    model_id: int = Field(..., description="Model ID")
    model_name: str = Field(..., description="Model name")
    settlement_status: SettlementStatus = Field(
        ...,
        description="Bet settlement status")
    custom_bet: bool = Field(
        ...,
        description="Whether the bet was added manually")


class BetRecommendationsResponse(BaseModel):
    """Response for GET /bets/recommendations."""

    recommendations: list[BetRecommendation] = Field(
        ...,
        description="Matching bet recommendations")
    total_count: int = Field(..., description="Total matching rows")
    filters_applied: dict[str, object] = Field(
        ...,
        description="Applied query filters")
