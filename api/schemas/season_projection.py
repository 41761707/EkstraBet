"""Pydantic schemas for season-end projection endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from pydantic import Field

SeasonProjectionMode = Literal["from_now", "from_season_start"]


class SeasonProjectionStandingRow(BaseModel):
    """One team row from a cached season projection run."""

    team_id: int = Field(..., description="Team ID")
    team_name: str = Field(..., description="Team display name")
    current_position: int = Field(
        ...,
        description="Current table position after fixed results")
    current_points: int = Field(
        ...,
        description="Current points after fixed results")
    expected_position: float = Field(
        ...,
        description="Mean end-of-season position across trials")
    most_likely_position: int = Field(
        ...,
        description="Mode of the position distribution")
    position_min: int = Field(
        ...,
        description="Best (lowest) position observed in trials")
    position_max: int = Field(
        ...,
        description="Worst (highest) position observed in trials")
    expected_points: float = Field(
        ...,
        description="Mean end-of-season points across trials")
    points_variance: float = Field(
        ...,
        description="Variance of end-of-season points")
    points_stddev: float = Field(
        ...,
        description="Standard deviation of end-of-season points")
    points_p05: float = Field(
        ...,
        description="5th percentile of end-of-season points")
    points_p50: float = Field(
        ...,
        description="Median end-of-season points")
    points_p95: float = Field(
        ...,
        description="95th percentile of end-of-season points")
    points_min: float = Field(
        ...,
        description="Minimum end-of-season points in trials")
    points_max: float = Field(
        ...,
        description="Maximum end-of-season points in trials")
    expected_goal_difference: float = Field(
        ...,
        description="Mean end-of-season goal difference")
    position_probabilities: list[float] = Field(
        ...,
        description="Probabilities for finishing positions 1..N")


class SeasonProjectionResponse(BaseModel):
    """Response model for GET /leagues/{league_id}/season-projection."""

    league_id: int = Field(..., description="League ID")
    season_id: int = Field(..., description="Season ID")
    mode: SeasonProjectionMode = Field(
        ...,
        description="Projection mode used for the cached run")
    generated_at: datetime = Field(
        ...,
        description="When the cached run completed")
    model_name: str = Field(..., description="Model artifact name")
    model_version: str = Field(..., description="Model version label")
    n_trials: int = Field(..., description="Number of Monte Carlo trials")
    fixed_matches: int = Field(
        ...,
        description="Fixtures committed from real results")
    simulated_matches: int = Field(
        ...,
        description="Fixtures sampled during simulation")
    is_stale: bool = Field(
        ...,
        description="True when schedule/results fingerprint changed")
    standings: list[SeasonProjectionStandingRow] = Field(
        ...,
        description="Projected table rows ordered by expected position")
