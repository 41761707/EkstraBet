"""Pydantic schemas for the knockout bracket endpoint."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BracketTeamResponse(BaseModel):
    """One side of a knockout tie."""

    team_id: int = Field(..., description="Team ID")
    name: str = Field(..., description="Team name")
    shortcut: str | None = Field(
        ...,
        description="Team shortcut, or null when unknown")


class BracketMatchResponse(BaseModel):
    """One match on a tie card.

    Extra-time goals stay beside the regulation score. A final
    stored as 0:0 can still be 1:0 after extra time.
    """

    match_id: int = Field(..., description="Match ID")
    game_date: datetime | None = Field(
        ...,
        description="Kickoff, or null when the match has no date")
    home_team_id: int = Field(..., description="Home team ID")
    away_team_id: int = Field(..., description="Away team ID")
    home_goals: int | None = Field(
        ...,
        description="Regulation goals by the home team")
    away_goals: int | None = Field(
        ...,
        description="Regulation goals by the away team")
    home_extra_time_goals: int | None = Field(
        ...,
        description="Home goals including extra time")
    away_extra_time_goals: int | None = Field(
        ...,
        description="Away goals including extra time")
    home_penalty_goals: int | None = Field(
        ...,
        description="Home penalty goals")
    away_penalty_goals: int | None = Field(
        ...,
        description="Away penalty goals")
    is_played: bool = Field(..., description="Whether a result is stored")
    decided_by: str | None = Field(
        ...,
        description=(
            "regulation, extra_time, penalties, overtime, "
            "shootout, or null"))


class BracketTieResponse(BaseModel):
    """One pair, bye or opponent that is not drawn yet."""

    tie_id: str = Field(..., description="Stable tie identifier")
    teams: list[BracketTeamResponse] = Field(
        ...,
        description="Teams on the card, lower id first")
    is_bye: bool = Field(
        ...,
        description="True for a bye without a match")
    pending_opponent_label: str | None = Field(
        ...,
        description="Label when the opponent is not drawn yet")
    seed_position: int | None = Field(
        ...,
        description="League-phase place, or null")
    advanced_team_id: int | None = Field(
        ...,
        description="Team that played on, or won the final")
    on_champion_path: bool = Field(
        ...,
        description="True when the tie is on the champion path")
    feeder_tie_ids: list[str] = Field(
        ...,
        description="Ties that feed this one")
    aggregate: list[int] | None = Field(
        ...,
        description="Two-leg totals in team order, or null")
    series_wins: list[int] | None = Field(
        ...,
        description="Series wins in team order, or null")
    matches: list[BracketMatchResponse] = Field(
        ...,
        description="Matches of this tie")


class BracketColumnResponse(BaseModel):
    """One phase column. The earliest phase is first."""

    depth: int = Field(..., description="Phase depth, 1 is the final")
    stage_label: str = Field(..., description="Polish phase label")
    ties: list[BracketTieResponse] = Field(
        ...,
        description="Ties in draw order")


class KnockoutBracketResponse(BaseModel):
    """One drawn bracket, cup or relegation."""

    bracket_id: str = Field(
        ...,
        description="Family: cup or relegation")
    title: str = Field(..., description="Section title")
    columns: list[BracketColumnResponse] = Field(
        ...,
        description="Columns from the earliest phase")
    third_place: BracketTieResponse | None = Field(
        ...,
        description="Third-place tie, or null")


class LeagueBracketResponse(BaseModel):
    """Response model for GET /leagues/{league_id}/bracket."""

    league_id: int = Field(..., description="League ID")
    season_id: int = Field(..., description="Season ID")
    consumed_round_numbers: list[int] = Field(
        ...,
        description="Rounds drawn on a visible bracket")
    brackets: list[KnockoutBracketResponse] = Field(
        ...,
        description="Visible brackets; empty when nothing is drawn")
