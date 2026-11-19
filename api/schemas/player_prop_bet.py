"""Pydantic schemas for hockey player-prop recommendation endpoints."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from api.schemas.bet import SettlementStatus
from api.schemas.match import TeamInMatch


class PlayerPropHistoryPoint(BaseModel):
    """One past-match stat shown on the history strip."""

    value: int = Field(..., description="Stat value for one past match")


class PlayerPropHistory(BaseModel):
    """Hit count and bar values for the requested window."""

    window: int = Field(
        ...,
        description="Requested history window, 5 or 10")
    played: int = Field(
        ...,
        description="Matches included in the denominator")
    hits: int = Field(
        ...,
        description="Matches that cleared the line")
    points: list[PlayerPropHistoryPoint] = Field(
        ...,
        description="Stat values from oldest to newest")


class PlayerPropRecommendation(BaseModel):
    """One player-prop line joined with a model prediction."""

    line_id: int = Field(..., description="player_props_lines row ID")
    player_id: int = Field(..., description="Player ID")
    player_name: str = Field(..., description="Player common name")
    line: float = Field(..., description="Bookmaker line")
    match_id: int = Field(..., description="Match ID")
    league_id: int = Field(..., description="League ID")
    league_name: str = Field(..., description="League name")
    season_id: int = Field(..., description="Season ID")
    game_date: datetime | date = Field(..., description="Match kick-off date")
    home_team: TeamInMatch = Field(..., description="Home team")
    away_team: TeamInMatch = Field(..., description="Away team")
    event_id: int = Field(..., description="Event ID")
    event_name: str = Field(
        ...,
        description="Event name with the line substituted")
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
    ev: float = Field(
        ...,
        description="Recalculated EV: probability * odds - 1")
    ev_after_tax: float | None = Field(
        None,
        description="EV after 12% betting tax when apply_tax is enabled")
    bookmaker_id: int | None = Field(None, description="Bookmaker ID")
    bookmaker_name: str | None = Field(None, description="Bookmaker name")
    model_id: int = Field(..., description="Model ID")
    model_name: str = Field(..., description="Model name")
    settlement_status: SettlementStatus = Field(
        ...,
        description="Settlement status from this match stat")
    history: PlayerPropHistory = Field(
        ...,
        description="Recent matches before this fixture")


class PlayerPropRecommendationsResponse(BaseModel):
    """Response for GET /bets/player-recommendations."""

    recommendations: list[PlayerPropRecommendation] = Field(
        ...,
        description="Matching player-prop recommendations")
    total_count: int = Field(..., description="Total matching rows")
    filters_applied: dict[str, object] = Field(
        ...,
        description="Applied query filters")
