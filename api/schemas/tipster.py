"""Pydantic schemas for tipster bankroll, coupons and ranking."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


StakeInputMode = Literal["money", "units"]
LegSource = Literal["catalog", "custom_odds"]
CurrencyCode = Literal["PLN", "EUR", "USD"]
LeaderboardSortBy = Literal[
    "profit_total",
    "roi_pct",
    "accuracy_pct",
    "avg_odds",
    "avg_profit",
    "bets_count",
    "current_balance"]
LeaderboardSortOrder = Literal["asc", "desc"]


class BankrollSettings(BaseModel):
    """Full bankroll document returned to the owner."""

    model_config = ConfigDict(extra="forbid")

    user_id: int = Field(..., description="Internal user ID")
    currency: CurrencyCode = Field(..., description="Bankroll currency")
    initial_capital: float = Field(..., description="Starting capital")
    unit_size: float = Field(..., description="Stake unit size")
    current_balance: float = Field(
        ...,
        description=(
            "initial_capital plus realized profit, minus stakes "
            "on unsettled coupons"))
    open_stake: float = Field(
        ...,
        description="Sum of stakes on unsettled coupons")
    realized_pnl: float = Field(
        ...,
        description="Sum of profit on settled coupons")


class PublicBankroll(BaseModel):
    """Bankroll fields visible to a non-owner."""

    model_config = ConfigDict(extra="forbid")

    currency: CurrencyCode = Field(..., description="Bankroll currency")
    current_balance: float = Field(
        ...,
        description=(
            "initial_capital plus realized profit, minus stakes "
            "on unsettled coupons"))


class BankrollConfigureRequest(BaseModel):
    """Onboarding or settings update for the caller's bankroll."""

    currency: CurrencyCode = Field(..., description="Bankroll currency")
    initial_capital: float = Field(
        ...,
        description="Starting capital; frozen after the first PUT")
    unit_size: float = Field(..., description="Stake unit size")


class TopUpRequest(BaseModel):
    """Increase initial_capital by a positive amount."""

    amount: float = Field(..., description="Amount added to initial_capital")


class CouponLegCreate(BaseModel):
    """One coupon leg with a single bookmaker price."""

    match_id: int = Field(..., description="Match ID")
    event_ids: list[int] = Field(
        ...,
        min_length=1,
        description="Settleable event IDs; length >= 2 is combined")
    odds: float = Field(
        ...,
        ge=1.01,
        description="Leg odds; combined uses the bookmaker combo price")
    source: LegSource = Field(..., description="catalog or custom_odds")
    bookmaker_id: int | None = Field(
        None,
        description="Bookmaker ID, or null when odds are custom")


class CouponCreateRequest(BaseModel):
    """Payload for placing a coupon via /me or an EB-9 job."""

    stake_input_mode: StakeInputMode = Field(
        ...,
        description="Whether stake_amount or stake_units is used")
    stake_amount: float | None = Field(
        None,
        description="Stake in bankroll currency when mode is money")
    stake_units: float | None = Field(
        None,
        description="Stake in units when mode is units")
    legs: list[CouponLegCreate] = Field(
        ...,
        min_length=1,
        max_length=8,
        description="One to eight legs; at most one per match")


class CouponLegSummary(BaseModel):
    """Persisted coupon leg with match and event labels for history."""

    id: int = Field(..., description="Leg ID")
    match_id: int = Field(..., description="Match ID")
    event_ids: list[int] = Field(..., description="Event IDs on this leg")
    event_names: list[str] = Field(
        default_factory=list,
        description="Catalog event names aligned with event_ids")
    home_name: str | None = Field(
        None, description="Home team name at read time")
    away_name: str | None = Field(
        None, description="Away team name at read time")
    odds: float = Field(..., description="Snapshotted leg odds")
    bookmaker_id: int | None = Field(None, description="Bookmaker ID")
    source: LegSource = Field(..., description="catalog or custom_odds")
    outcome: int | None = Field(
        None,
        description="Null open, 0 lost, 1 won")


class CouponSummary(BaseModel):
    """Coupon row with nested legs."""

    id: int = Field(..., description="Coupon ID")
    user_id: int = Field(..., description="Owner user ID")
    stake_amount: float = Field(..., description="Stake in currency")
    stake_units: float | None = Field(None, description="Stake in units")
    stake_input_mode: StakeInputMode = Field(
        ...,
        description="How the stake was entered")
    combined_odds: float = Field(
        ...,
        description="Product of per-leg odds")
    settled: int = Field(..., description="1 when the coupon is closed")
    outcome: int | None = Field(
        None,
        description="Null open, 0 lost, 1 won")
    profit: float | None = Field(
        None,
        description="Settled profit; negative on a loss")
    created_at: datetime | None = Field(
        None,
        description="Coupon creation timestamp")
    legs: list[CouponLegSummary] = Field(..., description="Coupon legs")


class CouponPage(BaseModel):
    """Paginated coupon history."""

    items: list[CouponSummary] = Field(..., description="Coupon page")
    total: int = Field(..., description="Total matching coupons")
    page: int = Field(..., description="Current page, 1-based")
    page_size: int = Field(..., description="Page size")


class PerformanceItem(BaseModel):
    """One breakdown bucket; unused dimension keys stay null."""

    event_family_id: int | None = Field(
        None,
        description="Event family id; null for the OTHER bucket")
    event_family_name: str | None = Field(
        None,
        description="Event family name; OTHER for unmapped markets")
    league_id: int | None = Field(None, description="League ID")
    league_name: str | None = Field(None, description="League name")
    league_tier: int | None = Field(None, description="League tier")
    country_id: int | None = Field(None, description="Country ID")
    country_name: str | None = Field(None, description="Country name")
    country_emoji: str | None = Field(
        None, description="Country flag emoji")
    count: int = Field(..., description="Coupons in this bucket")
    won: int = Field(..., description="Winning coupons")
    accuracy: float | None = Field(None, description="Win percentage")
    legs_count: int = Field(
        0,
        description="Legs in this bucket; one combined leg counts once")
    legs_won: int = Field(
        0,
        description="Legs whose own outcome is a win")
    legs_accuracy: float | None = Field(
        None,
        description="Leg hit rate, independent of the coupon result")
    legs_won_on_lost_coupons: int = Field(
        0,
        description="Winning legs that sit on a lost coupon")
    stake_total: float = Field(..., description="Sum of stakes")
    profit_total: float = Field(..., description="Sum of profit")
    avg_profit: float | None = Field(None, description="Mean profit")
    avg_odds: float | None = Field(
        None,
        description="Mean odds of the legs in this bucket")
    roi_pct: float | None = Field(None, description="ROI percentage")


class PerformanceBreakdown(BaseModel):
    """Settled-coupon analytics by family, league and country."""

    by_event_family: list[PerformanceItem] = Field(
        ...,
        description="Buckets by event family, including OTHER")
    by_league: list[PerformanceItem] = Field(
        ...,
        description="Buckets by league")
    by_country: list[PerformanceItem] = Field(
        ...,
        description="Buckets by the league country")
    best_event_family: PerformanceItem | None = Field(
        None,
        description="Family with the highest profit_total")
    worst_event_family: PerformanceItem | None = Field(
        None,
        description="Family with the lowest profit_total")
    best_league: PerformanceItem | None = Field(
        None,
        description="League with the highest profit_total")
    worst_league: PerformanceItem | None = Field(
        None,
        description="League with the lowest profit_total")
    best_country: PerformanceItem | None = Field(
        None,
        description="Country with the highest profit_total")
    worst_country: PerformanceItem | None = Field(
        None,
        description="Country with the lowest profit_total")


class LeaderboardRow(BaseModel):
    """One ranking row; coupon lists are never included."""

    user_id: int = Field(..., description="Internal user ID")
    username: str = Field(..., description="Login username")
    display_name: str | None = Field(None, description="Display name")
    is_system: bool = Field(
        ...,
        description="True when the account is a system agent")
    currency: CurrencyCode = Field(..., description="Bankroll currency")
    bets_count: int = Field(..., description="Settled coupon count")
    won_count: int = Field(..., description="Winning coupon count")
    accuracy_pct: float | None = Field(
        None,
        description="Win percentage; null when bets_count is 0")
    legs_count: int = Field(
        0,
        description="Legs matching the active ranking filters")
    legs_won: int = Field(
        0,
        description="Matching legs whose own outcome is a win")
    legs_won_on_lost_coupons: int = Field(
        0,
        description="Matching legs that won inside a lost coupon")
    stake_total: float = Field(..., description="Sum of settled stakes")
    profit_total: float = Field(..., description="Sum of settled profit")
    avg_profit: float | None = Field(
        None,
        description="Mean profit; null when bets_count is 0")
    avg_odds: float | None = Field(
        None,
        description=(
            "Mean combined coupon odds, or mean matching leg odds "
            "when a league, tier or family filter is set"))
    roi_pct: float | None = Field(
        None,
        description="ROI percentage; null when stake_total is 0")
    current_balance: float = Field(
        ...,
        description="Unfiltered bankroll current_balance")


class LeaderboardResponse(BaseModel):
    """Paginated ranking of users who have a bankroll row."""

    items: list[LeaderboardRow] = Field(..., description="Ranking page")
    total: int = Field(..., description="Total matching ranking rows")


class TipsterProfileResponse(BaseModel):
    """Public identity; coupons only for the owner or a system target."""

    user_id: int = Field(..., description="Internal user ID")
    username: str = Field(..., description="Login username")
    display_name: str | None = Field(None, description="Display name")
    is_system: bool = Field(
        ...,
        description="True when the account is a system agent")
    bankroll: BankrollSettings | PublicBankroll | None = Field(
        None,
        description="Full bankroll for the owner; currency and balance otherwise")
    coupons: CouponPage | None = Field(
        None,
        description="Coupon page for owner or system target; null otherwise")
    performance: PerformanceBreakdown | None = Field(
        None,
        description="Analytics when coupons are visible")


class CatalogMatch(BaseModel):
    """Upcoming unfinished football match for the coupon picker."""

    id: int = Field(..., description="Match ID")
    league_id: int = Field(..., description="League ID")
    league_name: str | None = Field(None, description="League name")
    league_tier: int | None = Field(None, description="League tier")
    game_date: datetime | None = Field(None, description="Kick-off")
    result: str | None = Field(None, description="Match result when set")
    home_id: int = Field(..., description="Home team ID")
    home_name: str = Field(..., description="Home team name")
    home_shortcut: str | None = Field(None, description="Home shortcut")
    away_id: int = Field(..., description="Away team ID")
    away_name: str = Field(..., description="Away team name")
    away_shortcut: str | None = Field(None, description="Away shortcut")


class CatalogEvent(BaseModel):
    """Settleable catalog event shown in the picker."""

    id: int = Field(..., description="Event ID")
    name: str = Field(..., description="Event name")


class SuggestedCatalogOdds(BaseModel):
    """Default price for one catalog event; null when none is stored."""

    model_config = ConfigDict(extra="forbid")

    odds: float | None = Field(
        None,
        description=(
            "Best bookmaker odds when a prediction exists; "
            "the client may edit this value"))


class CatalogMatchesResponse(BaseModel):
    """Matches and settleable events as separate lists."""

    matches: list[CatalogMatch] = Field(
        ...,
        description="Upcoming unfinished matches")
    events: list[CatalogEvent] = Field(
        ...,
        description="Settleable events; combined is composed in the UI")


class SettlementResult(BaseModel):
    """Counters from an admin-triggered settlement cycle."""

    legs_settled: int = Field(..., description="Legs written this cycle")
    coupons_settled: int = Field(
        ...,
        description="Coupons closed this cycle (rowcount 1)")
    legs_skipped: int = Field(
        ...,
        description="Open legs left pending missing stats")
