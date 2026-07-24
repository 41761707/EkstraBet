"""Pydantic schemas for prediction endpoints."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field
from pydantic import model_validator


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
    value: float = Field(
        ...,
        description="Predicted probability in 0-1 range",
        ge=0.0)


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
        description="Predicted probability in 0-1 range when available")
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
        description="Predicted probability in 0-1 range when available")
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


class PredictionPreviewRequest(BaseModel):
    """Input pair and optional match context for synchronous inference."""

    home_team_id: int = Field(..., ge=1, description="Home team ID")
    away_team_id: int = Field(..., ge=1, description="Away team ID")
    league_id: int | None = Field(None, ge=1, description="Optional league ID")
    as_of_date: date = Field(
        default_factory=date.today,
        description="Prediction cutoff date")

    @model_validator(mode="after")
    def validate_distinct_teams(self) -> PredictionPreviewRequest:
        """Ensure a team is not matched against itself."""
        if self.home_team_id == self.away_team_id:
            raise ValueError("Home and away teams must be different")
        return self


class ResultPredictionPreview(BaseModel):
    """Three-way football result probabilities."""

    p_home: float = Field(..., ge=0.0, le=1.0)
    p_draw: float = Field(..., ge=0.0, le=1.0)
    p_away: float = Field(..., ge=0.0, le=1.0)


class BttsPredictionPreview(BaseModel):
    """Both-teams-to-score probabilities."""

    p_yes: float = Field(..., ge=0.0, le=1.0)
    p_no: float = Field(..., ge=0.0, le=1.0)


class ExactScorePredictionPreview(BaseModel):
    """Probability assigned to one exact scoreline."""

    score: str = Field(..., description="Scoreline in home:away format")
    probability: float = Field(..., ge=0.0, le=1.0)


class GoalsPredictionPreview(BaseModel):
    """Poisson goal projections and derived markets."""

    lambda_home: float = Field(..., ge=0.0)
    lambda_away: float = Field(..., ge=0.0)
    total_buckets: dict[str, float] = Field(
        ...,
        description="Total-goal bucket probabilities")
    over_25: float = Field(..., ge=0.0, le=1.0)
    under_25: float = Field(..., ge=0.0, le=1.0)
    top_exact_scores: list[ExactScorePredictionPreview] = Field(
        ...,
        description="Most probable exact scorelines")


class PredictionPreviewResponse(BaseModel):
    """Typed prediction preview returned for a team pair."""

    result: ResultPredictionPreview
    btts: BttsPredictionPreview
    goals: GoalsPredictionPreview
