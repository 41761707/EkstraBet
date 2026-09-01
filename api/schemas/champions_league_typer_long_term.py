"""Pydantic schemas for Typer long-term market endpoints."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


class LongTermTeam(BaseModel):
    """League-phase participant offered as a long-term pick."""

    team_id: int = Field(..., description="Team ID")
    team_name: str = Field(..., description="Team name")
    team_shortcut: str = Field(..., description="Team shortcut")


class LongTermStandingTeam(LongTermTeam):
    """League-phase table row used in the admin TOP 8 proposal."""

    played: int = Field(..., description="Settled league-phase matches")
    points: int = Field(..., description="League-phase points")
    goal_difference: int = Field(..., description="Goal difference")
    goals_for: int = Field(..., description="Goals scored")


class LongTermPickChange(BaseModel):
    """One append-only audit snapshot of a full pick set."""

    id: int = Field(..., description="Audit row ID")
    market_id: int = Field(..., description="Long-term market ID")
    user_uuid: str = Field(..., description="Public user UUID")
    display_name: str = Field(..., description="Display name")
    previous_team_ids: list[int] | None = Field(
        None,
        description="Previous sorted team IDs; null on the first save")
    new_team_ids: list[int] = Field(
        ...,
        description="New sorted team IDs")
    changed_at: datetime = Field(
        ...,
        description="When the set was saved")


class LongTermMarketCard(BaseModel):
    """One long-term market with private picks and own audit."""

    market_id: int = Field(..., description="Long-term market ID")
    league_id: int = Field(..., description="League ID")
    season_id: int = Field(..., description="Season ID")
    market_key: str = Field(..., description="Stable market key")
    title: str = Field(..., description="Market title")
    description: str | None = Field(
        None,
        description="Optional market description")
    selection_size: int = Field(
        ...,
        description="Required number of distinct teams")
    points_per_correct: float = Field(
        ...,
        description="Points awarded for each correct team")
    settled_at: datetime | date | None = Field(
        None,
        description="When an admin approved the result")
    deadline_at: datetime | date | None = Field(
        None,
        description="First league-phase kick-off")
    is_locked: bool = Field(
        ...,
        description="True when the first league-phase match has started")
    candidates: list[LongTermTeam] = Field(
        ...,
        description="Distinct league-phase participants")
    picked_team_ids: list[int] = Field(
        ...,
        description="Current user's selected team IDs")
    result_team_ids: list[int] = Field(
        ...,
        description="Approved result team IDs; empty until settled")
    points: float | None = Field(
        None,
        description=(
            "Hits times points_per_correct after settlement; "
            "null while the market is unsettled"))
    changes: list[LongTermPickChange] = Field(
        ...,
        description="Private audit of the current user's set")


class LongTermDashboardResponse(BaseModel):
    """Response model for GET /typer-lm/long-term."""

    season_id: int = Field(..., description="Resolved season ID")
    markets: list[LongTermMarketCard] = Field(
        ...,
        description="Long-term markets for the season")


class LongTermTeamIdsRequest(BaseModel):
    """Body for pick save and admin settlement."""

    team_ids: list[int] = Field(
        ...,
        min_length=1,
        description=(
            "Team IDs; order is ignored. Count must match "
            "the market selection size"))

    @field_validator("team_ids")
    @classmethod
    def require_positive_unique_team_ids(
            cls, value: list[int]) -> list[int]:
        """Reject non-positive or duplicate ids before domain rules run."""
        if any(team_id < 1 for team_id in value):
            raise ValueError("Team ids must be positive integers")
        if len(set(value)) != len(value):
            raise ValueError("Team ids must be unique")
        return value


class SaveLongTermPicksResponse(BaseModel):
    """Result of creating or replacing a long-term pick set."""

    market_id: int = Field(..., description="Long-term market ID")
    team_ids: list[int] = Field(
        ...,
        description="Saved team IDs sorted ascending")
    previous_team_ids: list[int] | None = Field(
        None,
        description="Previous set; null on the first save")
    audit_written: bool = Field(
        ...,
        description="False when the identical set was a no-op")


class LongTermAutoResultResponse(BaseModel):
    """Admin TOP 8 proposal; never awards points by itself."""

    market_id: int = Field(..., description="Long-term market ID")
    league_id: int = Field(..., description="League ID")
    season_id: int = Field(..., description="Season ID")
    market_key: str = Field(..., description="Stable market key")
    selection_size: int = Field(
        ...,
        description="Required number of distinct teams")
    points_per_correct: float = Field(
        ...,
        description="Points awarded for each correct team")
    settled_at: datetime | date | None = Field(
        None,
        description="When an admin approved the result")
    settled_by_uuid: str | None = Field(
        None,
        description="Public UUID of the admin who settled the market")
    settled_by_display_name: str | None = Field(
        None,
        description="Display name of the admin who settled the market")
    is_complete: bool = Field(
        ...,
        description="True when 36 teams each have 8 settled matches")
    is_proposal: bool = Field(
        ...,
        description="Always true: UEFA tie-breakers are incomplete")
    participant_count: int = Field(
        ...,
        description="Distinct teams with settled league-phase matches")
    settled_match_count: int = Field(
        ...,
        description="Settled league-phase matches")
    min_matches_per_team: int = Field(
        ...,
        description="Fewest settled matches among participants")
    max_matches_per_team: int = Field(
        ...,
        description="Most settled matches among participants")
    required_participant_count: int = Field(
        ...,
        description="Expected league-phase team count")
    required_matches_per_team: int = Field(
        ...,
        description="Expected matches per team")
    required_settled_match_count: int = Field(
        ...,
        description="Expected settled league-phase matches")
    proposed_team_ids: list[int] = Field(
        ...,
        description="Proposed TOP 8 IDs; empty until the phase is complete")
    proposed_teams: list[LongTermStandingTeam] = Field(
        ...,
        description="Proposed TOP 8 rows; empty until the phase is complete")
    result_team_ids: list[int] = Field(
        ...,
        description="Approved result team IDs; empty until settled")
    standings: list[LongTermStandingTeam] = Field(
        ...,
        description="League-phase table used to build the proposal")


class SettleLongTermResponse(BaseModel):
    """Approved or corrected long-term result set."""

    market_id: int = Field(..., description="Long-term market ID")
    team_ids: list[int] = Field(
        ...,
        description="Approved team IDs sorted ascending")
    settled_by_uuid: str | None = Field(
        None,
        description="Public UUID of the admin who wrote the result")
    settled_by_display_name: str | None = Field(
        None,
        description="Display name of the admin who wrote the result")
    settled_at: datetime | date = Field(
        ...,
        description="When the result was written")
    result_team_ids: list[int] = Field(
        ...,
        description="Approved team IDs sorted ascending")
