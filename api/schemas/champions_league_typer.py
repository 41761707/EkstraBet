"""Pydantic schemas for Champions League Typer endpoints."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


TyperOutcome = Literal["1", "X", "2"]


class TyperTeam(BaseModel):
    """Team reference embedded in a Typer match."""

    id: int = Field(..., description="Team ID")
    name: str = Field(..., description="Team name")
    shortcut: str = Field(..., description="Team shortcut")


class TyperPredictionChange(BaseModel):
    """One append-only audit row for a 1X2 pick change."""

    match_id: int = Field(..., description="Published match ID")
    user_uuid: str = Field(..., description="Public user UUID")
    display_name: str = Field(..., description="Display name")
    previous_outcome: TyperOutcome | None = Field(
        None,
        description="Previous 1X2 pick; null on the first save")
    new_outcome: TyperOutcome = Field(..., description="New 1X2 pick")
    changed_at: datetime = Field(..., description="When the change was saved")


class TyperMatch(BaseModel):
    """Published Typer match with private pick, odds and own audit."""

    match_id: int = Field(..., description="Match ID")
    season_id: int = Field(..., description="Season ID")
    round_number: int = Field(..., description="Round number")
    game_date: datetime | date = Field(..., description="Kick-off datetime")
    published_at: datetime | date = Field(
        ...,
        description="When the match was published to Typer")
    is_locked: bool = Field(
        ...,
        description="True when kick-off has started or passed")
    result: str | None = Field(
        None,
        description="Regulation 1/X/2 result when available")
    home_team: TyperTeam = Field(..., description="Home team")
    away_team: TyperTeam = Field(..., description="Away team")
    odds_home: float | None = Field(
        None,
        description="Superbet home win odds; null when missing")
    odds_draw: float | None = Field(
        None,
        description="Superbet draw odds; null when missing")
    odds_away: float | None = Field(
        None,
        description="Superbet away win odds; null when missing")
    outcome: TyperOutcome | None = Field(
        None,
        description="Current user's 1X2 pick")
    points: float | None = Field(
        None,
        description=(
            "Superbet odds when the pick is correct, 0 when missed, "
            "null when unsettled"))
    changes: list[TyperPredictionChange] = Field(
        ...,
        description="Private audit of the current user's pick")


class TyperRound(BaseModel):
    """Published matches grouped by round."""

    round_number: int = Field(..., description="Round number")
    matches: list[TyperMatch] = Field(..., description="Published matches")


class TyperDashboardResponse(BaseModel):
    """Response model for GET /typer-lm/dashboard."""

    season_id: int = Field(..., description="Resolved season ID")
    rounds: list[TyperRound] = Field(..., description="Published rounds")


class SavePredictionRequest(BaseModel):
    """Body for PUT /typer-lm/predictions/{match_id}."""

    outcome: TyperOutcome = Field(
        ...,
        description="1X2 pick: 1 home, X draw, 2 away")


class SavePredictionResponse(BaseModel):
    """Result of creating or updating a 1X2 pick."""

    match_id: int = Field(..., description="Published match ID")
    outcome: TyperOutcome = Field(..., description="Saved 1X2 pick")
    previous_outcome: TyperOutcome | None = Field(
        None,
        description="Previous 1X2 pick; null on the first save")
    audit_written: bool = Field(
        ...,
        description="False when the identical pick was a no-op")
    created_at: datetime = Field(..., description="First save timestamp")
    updated_at: datetime = Field(..., description="Last save timestamp")


class TyperLeaderboardRow(BaseModel):
    """One ranking row with aggregates only."""

    place: int = Field(..., description="1-based rank")
    user_uuid: str = Field(..., description="Public user UUID")
    display_name: str = Field(..., description="Display name")
    total_points: float = Field(..., description="Sum of settled points")
    correct_predictions: int = Field(..., description="Number of hits")
    settled_predictions: int = Field(
        ...,
        description="Number of picks with an official 1X2 result and score")


class TyperAdminCandidate(BaseModel):
    """Champions League match offered for publication."""

    match_id: int = Field(..., description="Match ID")
    season_id: int = Field(..., description="Season ID")
    round_number: int = Field(..., description="Round number")
    game_date: datetime | date = Field(..., description="Kick-off datetime")
    home_team: TyperTeam = Field(..., description="Home team")
    away_team: TyperTeam = Field(..., description="Away team")
    is_published: bool = Field(..., description="Whether already published")
    has_complete_superbet_odds: bool = Field(
        ...,
        description="Informational Superbet 1/X/2 completeness; not blocking")


class TyperAdminCandidatesResponse(BaseModel):
    """Response model for GET /typer-lm/admin/candidates."""

    season_id: int = Field(..., description="Season ID")
    round_number: int = Field(..., description="Round number")
    candidates: list[TyperAdminCandidate] = Field(
        ...,
        description="Matches available in the round")
    total_count: int = Field(..., description="Number of candidates")


class PublishMatchesRequest(BaseModel):
    """Body for POST /typer-lm/admin/publications."""

    season_id: int = Field(..., ge=1, description="Season ID")
    round_number: int = Field(..., ge=1, description="Round number")
    match_ids: list[int] = Field(
        ...,
        min_length=1,
        description="Match IDs to publish atomically")

    @field_validator("match_ids")
    @classmethod
    def require_positive_match_ids(cls, value: list[int]) -> list[int]:
        """Reject non-positive match ids before domain rules run."""
        if any(match_id < 1 for match_id in value):
            raise ValueError("Match ids must be positive integers")
        return value


class TyperPublication(BaseModel):
    """One published Typer match."""

    match_id: int = Field(..., description="Match ID")
    season_id: int = Field(..., description="Season ID")
    round_number: int = Field(..., description="Round number")
    published_at: datetime | date = Field(
        ...,
        description="When the match was published")


class PublishMatchesResponse(BaseModel):
    """Response model for POST /typer-lm/admin/publications."""

    publications: list[TyperPublication] = Field(
        ...,
        description="Newly published matches")
    total_count: int = Field(..., description="Number of published matches")
