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
    """League-phase table row used in the admin ranked-table proposal."""

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
        description=(
            "Previous team IDs in table order; "
            "null on the first save"))
    new_team_ids: list[int] = Field(
        default_factory=list,
        description=(
            "New team IDs in table order; empty on text and yes_no"))
    previous_subject_text: str | None = Field(
        None,
        description=(
            "Previous typed name; null on first save or other kinds"))
    new_subject_text: str | None = Field(
        None,
        description="New typed name; null on team and yes_no rows")
    previous_is_text_correct: bool | None = Field(
        None,
        description="Previous YES/NO pick; null on other kinds")
    new_is_text_correct: bool | None = Field(
        None,
        description="New YES/NO pick; null on other kinds")
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
        description="Points awarded for matching a TOP or BOT zone")
    points_per_exact_position: float = Field(
        ...,
        description="Bonus points awarded for an exact table position")
    market_kind: str = Field(
        ...,
        description="Market shape, e.g. ranked_team_table")
    scoring_kind: str = Field(
        ...,
        description="Scoring formula, e.g. zone_and_position")
    top_zone_size: int = Field(
        ...,
        description="TOP zone width; -1 when unused")
    bot_zone_size: int = Field(
        ...,
        description="BOT zone width; -1 when unused")
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
        description="Current user's team IDs in table order")
    result_team_ids: list[int] = Field(
        ...,
        description=(
            "Approved result team IDs in table order; "
            "empty until settled"))
    picked_subject_text: str | None = Field(
        None,
        description=(
            "Current user's typed name; null on team and yes_no"))
    result_subject_texts: list[str] = Field(
        default_factory=list,
        description=(
            "Approved names as the admin typed them; "
            "empty until settled or on non-text markets"))
    picked_is_text_correct: bool | None = Field(
        None,
        description="Current user's YES/NO pick; null on other kinds")
    result_is_text_correct: bool | None = Field(
        None,
        description=(
            "Approved YES/NO; null until settled or on other kinds"))
    points: float | None = Field(
        None,
        description=(
            "Score after settlement; null while the market is unsettled"))
    changes: list[LongTermPickChange] = Field(
        ...,
        description="Private audit of the current user's set")


class LongTermDashboardResponse(BaseModel):
    """Response model for GET /typer-lm/long-term."""

    season_id: int = Field(..., description="Resolved season ID")
    markets: list[LongTermMarketCard] = Field(
        ...,
        description="Long-term markets for the season")


class LongTermPicksRequest(BaseModel):
    """Body for pick save and admin settlement.

    Exactly one branch is required per market kind; the service
    enforces xor. Ranked table still sends only team_ids.
    """

    team_ids: list[int] | None = Field(
        None,
        description=(
            "Team IDs in table order; index 0 is position 1. "
            "Used by ranked_team_table and single_team"))
    subject_texts: list[str] | None = Field(
        None,
        description=(
            "Typed names without sorting; one pick on save, "
            "one or more on free_text settlement"))
    is_text_correct: bool | None = Field(
        None,
        description="YES (true) or NO (false) for yes_no markets")

    @field_validator("team_ids")
    @classmethod
    def require_positive_unique_team_ids(
            cls, value: list[int] | None) -> list[int] | None:
        """Reject non-positive or duplicate ids before domain rules run."""
        if value is None:
            return None
        if any(team_id < 1 for team_id in value):
            raise ValueError("Team ids must be positive integers")
        if len(set(value)) != len(value):
            raise ValueError("Team ids must be unique")
        return value

    @field_validator("subject_texts")
    @classmethod
    def strip_non_empty_subject_texts(
            cls, value: list[str] | None) -> list[str] | None:
        """Trim each name; reject blanks. Do not sort or collapse."""
        if value is None:
            return None
        stripped = [text.strip() for text in value]
        if any(not text for text in stripped):
            raise ValueError("Subject texts must be non-empty after trim")
        return stripped


class SaveLongTermPicksResponse(BaseModel):
    """Result of creating or replacing a long-term pick set."""

    market_id: int = Field(..., description="Long-term market ID")
    team_ids: list[int] = Field(
        ...,
        description="Saved team IDs in table order")
    previous_team_ids: list[int] | None = Field(
        None,
        description="Previous set in table order; null on the first save")
    subject_texts: list[str] = Field(
        default_factory=list,
        description="Saved typed names; empty on team and yes_no")
    previous_subject_text: str | None = Field(
        None,
        description="Previous typed name; null on first save or other kinds")
    is_text_correct: bool | None = Field(
        None,
        description="Saved YES/NO; null on other kinds")
    previous_is_text_correct: bool | None = Field(
        None,
        description="Previous YES/NO; null on first save or other kinds")
    audit_written: bool = Field(
        ...,
        description="False when the identical sequence was a no-op")


class LongTermAutoResultResponse(BaseModel):
    """Admin ranked-table proposal; never awards points by itself."""

    market_id: int = Field(..., description="Long-term market ID")
    league_id: int = Field(..., description="League ID")
    season_id: int = Field(..., description="Season ID")
    market_key: str = Field(..., description="Stable market key")
    selection_size: int = Field(
        ...,
        description="Required number of distinct teams")
    points_per_correct: float = Field(
        ...,
        description="Points awarded for matching a TOP or BOT zone")
    points_per_exact_position: float = Field(
        ...,
        description="Bonus points awarded for an exact table position")
    top_zone_size: int = Field(
        ...,
        description="TOP zone width; -1 when unused")
    bot_zone_size: int = Field(
        ...,
        description="BOT zone width; -1 when unused")
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
        description=(
            "Proposed table IDs in standings order; "
            "empty until the phase is complete"))
    proposed_top_team_ids: list[int] = Field(
        ...,
        description=(
            "Prefix of proposed_team_ids with length top_zone_size; "
            "empty until the phase is complete"))
    proposed_bot_team_ids: list[int] = Field(
        ...,
        description=(
            "Suffix of proposed_team_ids with length bot_zone_size; "
            "empty until the phase is complete"))
    proposed_teams: list[LongTermStandingTeam] = Field(
        ...,
        description=(
            "Proposed table rows in standings order; "
            "empty until the phase is complete"))
    result_team_ids: list[int] = Field(
        ...,
        description=(
            "Approved result team IDs in table order; "
            "empty until settled"))
    standings: list[LongTermStandingTeam] = Field(
        ...,
        description="League-phase table used to build the proposal")


class SettleLongTermResponse(BaseModel):
    """Approved or corrected long-term result set."""

    market_id: int = Field(..., description="Long-term market ID")
    team_ids: list[int] = Field(
        ...,
        description="Approved team IDs in table order")
    subject_texts: list[str] = Field(
        default_factory=list,
        description="Approved names; empty on team and yes_no")
    is_text_correct: bool | None = Field(
        None,
        description="Approved YES/NO; null on other kinds")
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
        description="Approved team IDs in table order")
