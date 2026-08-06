"""Pydantic schemas for league rating-progress endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

RatingMetric = Literal["elo"]


class RatingPoint(BaseModel):
    """One post-match rating observation for a team."""

    match_id: int = Field(..., description="Finished match ID")
    round_number: int | None = Field(
        None,
        description="Round number when available")
    played_at: datetime = Field(..., description="Match kickoff datetime")
    rating: float = Field(..., description="Post-match rating value")


class TeamRatingProgress(BaseModel):
    """Seasonal rating series and summary for one participating team."""

    team_id: int = Field(..., description="Team ID")
    team_name: str = Field(..., description="Team display name")
    team_shortcut: str | None = Field(
        None,
        description="Short team label when available")
    start_rating: float = Field(
        ...,
        description="First pre-match rating in the target season")
    current_rating: float = Field(
        ...,
        description="Latest post-match rating in the target season")
    change: float = Field(
        ...,
        description="Seasonal change: current_rating - start_rating")
    current_rank: int = Field(
        ...,
        description="Rank by current_rating descending (ties: lower team_id)")
    points: list[RatingPoint] = Field(
        ...,
        description="Chronological post-match rating points")


class RatingProgressResponse(BaseModel):
    """Full seasonal rating-progress payload for GET rating-progress."""

    league_id: int = Field(..., description="League ID")
    league_name: str = Field(..., description="League display name")
    season_id: int = Field(..., description="Season ID")
    season_years: str = Field(..., description="Season years label")
    metric: RatingMetric = Field(..., description="Rating metric key")
    last_played_match_id: int | None = Field(
        None,
        description="Last finished match ID used as cutoff")
    last_played_at: datetime | None = Field(
        None,
        description="Kickoff of the last finished match")
    teams: list[TeamRatingProgress] = Field(
        ...,
        description="All teams with at least one finished match")
    biggest_rise: TeamRatingProgress | None = Field(
        None,
        description="Team with the largest seasonal rating gain")
    biggest_fall: TeamRatingProgress | None = Field(
        None,
        description="Team with the largest seasonal rating drop")
