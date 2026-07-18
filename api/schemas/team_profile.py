"""Pydantic schemas for team profile endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from api.schemas.match import (
    FormResult,
    HeadToHeadSummary,
    MatchSummary,
    TeamSeasonMatchPoint)


class TeamSummary(BaseModel):
    """Basic team metadata for profile and navigation."""

    id: int = Field(..., description="Team ID")
    name: str = Field(..., description="Team name")
    shortcut: str | None = Field(None, description="Team shortcut")
    country_id: int | None = Field(None, description="Country ID")
    country_name: str | None = Field(None, description="Country name")
    country_emoji: str | None = Field(None, description="Country flag emoji")
    sport_id: int | None = Field(None, description="Sport ID")
    sport_name: str | None = Field(None, description="Sport name")


class TeamSplitStats(BaseModel):
    """Win/draw/loss and goals statistics for a match scope."""

    played: int = Field(..., description="Matches played")
    wins: int = Field(..., description="Wins")
    draws: int = Field(..., description="Draws")
    losses: int = Field(..., description="Losses")
    goals_for: int = Field(..., description="Goals scored")
    goals_conceded: int = Field(..., description="Goals conceded")
    goal_difference: int = Field(..., description="Goal difference")
    points: int = Field(..., description="League points")


class TeamProfileResponse(BaseModel):
    """Full team profile payload for the team detail page."""

    team: TeamSummary = Field(..., description="Team metadata")
    season_id: int | None = Field(None, description="Season ID filter")
    league_id: int | None = Field(
        None,
        description="League filter when provided")
    form: list[FormResult] = Field(
        ...,
        description="Recent form from oldest to newest match")
    recent_matches: list[MatchSummary] = Field(
        ...,
        description="Most recent played matches")
    overall_stats: TeamSplitStats = Field(
        ...,
        description="Season statistics across all venues")
    home_stats: TeamSplitStats = Field(
        ...,
        description="Season statistics for home matches")
    away_stats: TeamSplitStats = Field(
        ...,
        description="Season statistics for away matches")
    season_matches: list[TeamSeasonMatchPoint] = Field(
        ...,
        description="Played season matches for charts (newest first)")
    head_to_head: HeadToHeadSummary | None = Field(
        None,
        description="H2H summary when opponent_id is provided")
