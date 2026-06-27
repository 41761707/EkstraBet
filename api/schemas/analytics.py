"""Pydantic schemas for analytics endpoints."""

from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field

StatType = Literal["ou", "btts", "result", "all"]
GroupBy = Literal["none", "team", "league"]
AggregationMetric = Literal["accuracy", "profit"]


class ChartDistribution(BaseModel):
    """Pie or bar chart data for event type distribution."""

    labels: list[str] = Field(..., description="Human-readable labels")
    values: list[int] = Field(..., description="Absolute counts")
    percentages: list[float] = Field(
        ...,
        description="Share of total as percentage")


class ChartComparison(BaseModel):
    """Stacked bar chart data for correct vs incorrect outcomes."""

    labels: list[str] = Field(..., description="Human-readable labels")
    correct: list[int] = Field(..., description="Correct counts per label")
    incorrect: list[int] = Field(
        ...,
        description="Incorrect counts per label")


class ChartData(BaseModel):
    """Chart payloads for frontend visualization libraries."""

    distribution: ChartDistribution
    comparison: ChartComparison


class TypeBreakdownRow(BaseModel):
    """Statistics for a single event type within a category."""

    key: str = Field(..., description="Machine-readable event key")
    total: int = Field(..., description="Total predictions or bets")
    correct: int = Field(..., description="Correct predictions or bets")
    accuracy_pct: float | None = Field(
        None,
        description="Accuracy percentage")
    share_pct: float | None = Field(
        None,
        description="Share of category total as percentage")
    profit: float | None = Field(
        None,
        description="Unit profit for settled bets")


class PredictionBetBreakdown(BaseModel):
    """Aggregated prediction or bet statistics with chart data."""

    total: int = Field(..., description="Total count")
    correct: int = Field(..., description="Correct count")
    accuracy_pct: float | None = Field(
        None,
        description="Accuracy percentage")
    profit_total: float | None = Field(
        None,
        description="Total unit profit for bets")
    by_type: list[TypeBreakdownRow] = Field(
        ...,
        description="Per-event-type breakdown")
    charts: ChartData = Field(..., description="Chart-ready data")


class CategoryStatistics(BaseModel):
    """OU, BTTS or 1X2 prediction and bet statistics."""

    predictions: PredictionBetBreakdown
    bets: PredictionBetBreakdown


class DistributionBucket(BaseModel):
    """Count and percentage for league characteristic buckets."""

    count: int
    percentage: float


class LeagueCharacteristics(BaseModel):
    """Actual OU, BTTS and 1X2 distribution for a league season."""

    played_matches: int
    avg_goals_per_match: float
    ou: dict[str, DistributionBucket]
    btts: dict[str, DistributionBucket]
    result: dict[str, DistributionBucket]


class EntityAggregationRow(BaseModel):
    """Accuracy or profit aggregation for a team or league."""

    entity_id: int | None = Field(
        None,
        description="Team or league ID; null for average row")
    entity_name: str = Field(..., description="Team or league name")
    total_predictions: int | None = Field(
        None,
        description="Total predictions when metric is accuracy")
    correct_predictions: int | None = Field(
        None,
        description="Correct predictions when metric is accuracy")
    accuracy_pct: float | None = Field(
        None,
        description="Accuracy percentage when metric is accuracy")
    profit: float | None = Field(
        None,
        description="Unit profit when metric is profit")


class AccuracyAggregation(BaseModel):
    """Per-entity accuracy comparison for one or more stat families."""

    metric: Literal["accuracy"] = "accuracy"
    ou: list[EntityAggregationRow] | None = None
    btts: list[EntityAggregationRow] | None = None
    result: list[EntityAggregationRow] | None = None


class ProfitAggregation(BaseModel):
    """Per-league profit comparison for one or more stat families."""

    metric: Literal["profit"] = "profit"
    ou: list[EntityAggregationRow] | None = None
    btts: list[EntityAggregationRow] | None = None
    result: list[EntityAggregationRow] | None = None


class AnalyticsAggregations(BaseModel):
    """Optional team or league aggregations."""

    by_team: AccuracyAggregation | None = None
    by_league: AccuracyAggregation | ProfitAggregation | None = None


class ModelAnalyticsResponse(BaseModel):
    """Response for GET /analytics/models."""

    categories: dict[str, CategoryStatistics] = Field(
        ...,
        description="Statistics keyed by ou, btts or result")
    aggregations: AnalyticsAggregations = Field(
        default_factory=AnalyticsAggregations,
        description="Optional team or league aggregations")
    league_characteristics: LeagueCharacteristics | None = Field(
        None,
        description="Actual league outcome distribution")
    filters_applied: dict[str, object] = Field(
        ...,
        description="Applied query filters")
