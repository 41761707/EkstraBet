"""Pydantic schemas for bet recommendation endpoints."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from api.schemas.match import TeamInMatch
from api.schemas.prediction import EventFamilyRef

SettlementStatus = Literal["pending", "won", "lost"]
HistorySide = Literal["over", "under"]
HistorySample = Literal["home", "away"]
BetSortBy = Literal["ev", "probability", "game_date", "history"]
BetSortOrder = Literal["asc", "desc"]
OpportunitySource = Literal["bet", "prediction"]
RankingBasis = Literal["ev_after_tax", "ev", "probability"]


class TeamBetHistoryPoint(BaseModel):
    """One past-match stat shown on the team history strip."""

    value: float = Field(..., description="Stat value for one past match")


class TeamBetHistorySeries(BaseModel):
    """One team's recent-match bars for a bet."""

    sample: HistorySample = Field(
        ...,
        description="Home or away side of the recommended match")
    played: int = Field(
        ...,
        description="Matches included in the denominator")
    hits: int = Field(
        ...,
        description="Matches where this bet would have won")
    points: list[TeamBetHistoryPoint] = Field(
        ...,
        description="Stat values from oldest to newest")
    subject_name: str | None = Field(
        None,
        description="Team name. Set when the event does not name the side")
    subject_shortcut: str | None = Field(
        None,
        description="Short team label drawn beside the strip")


class TeamBetHistory(BaseModel):
    """Line, side and one strip per sampled team."""

    window: int = Field(
        ...,
        description="Requested history window, 5 or 10")
    line: float = Field(..., description="Threshold drawn on the strip")
    side: HistorySide = Field(
        ...,
        description="Green bar when the value is over or under the line")
    series: list[TeamBetHistorySeries] = Field(
        ...,
        description=(
            "Home then away for a match-level event. "
            "One entry when the event names a side"))


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
        description="Bet settlement status")
    custom_bet: bool = Field(
        ...,
        description="Whether the bet was added manually")
    history: TeamBetHistory | None = Field(
        None,
        description="Recent-match strip for this bet, when the event has one")


class BetRecommendationsResponse(BaseModel):
    """Response for GET /bets/recommendations."""

    recommendations: list[BetRecommendation] = Field(
        ...,
        description="Matching bet recommendations")
    total_count: int = Field(..., description="Total matching rows")
    filters_applied: dict[str, object] = Field(
        ...,
        description="Applied query filters")


class MarketOpportunity(BaseModel):
    """Single ranked market opportunity across bets or predictions."""

    match_id: int = Field(..., description="Match ID")
    sport_id: int = Field(..., description="Sport ID")
    league_id: int = Field(..., description="League ID")
    league_name: str = Field(..., description="League name")
    game_date: datetime | date = Field(..., description="Match kick-off")
    home_team: str = Field(..., description="Home team name")
    away_team: str = Field(..., description="Away team name")
    event_id: int = Field(..., description="Event ID")
    event_name: str = Field(..., description="Event name")
    model_id: int | None = Field(None, description="Model ID")
    model_name: str | None = Field(None, description="Model name")
    probability: float | None = Field(
        None,
        description="Model probability in 0-1 range",
        ge=0.0,
        le=1.0)
    probability_pct: float | None = Field(
        None,
        description="Model probability as percentage",
        ge=0.0,
        le=100.0)
    odds: float | None = Field(
        None,
        description="Best available decimal odds",
        ge=1.0)
    bookmaker_id: int | None = Field(None, description="Bookmaker ID")
    bookmaker_name: str | None = Field(None, description="Bookmaker name")
    implied_probability: float | None = Field(
        None,
        description="Implied probability from odds (1/odds)")
    ev: float | None = Field(
        None,
        description="Expected value when odds are available")
    ev_after_tax: float | None = Field(
        None,
        description="EV after 12% tax when apply_tax and odds exist")
    source: OpportunitySource = Field(
        ...,
        description="Primary evidence source for this row")
    ranking_basis: RankingBasis = Field(
        ...,
        description="Metric used to rank this row within its tier")


class MarketOpportunitiesResponse(BaseModel):
    """Response for GET /bets/opportunities."""

    opportunities: list[MarketOpportunity] = Field(
        ...,
        description="Ranked market opportunities")
    total_count: int = Field(..., description="Number of returned rows")
    filters_applied: dict[str, object] = Field(
        ...,
        description="Applied query filters")
    source_counts: dict[str, int] = Field(
        ...,
        description="Counts by source tier (bet / prediction)")
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal notes about ranking composition")
