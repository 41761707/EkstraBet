"""Pydantic schemas for league navigation endpoints."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class LeagueSummary(BaseModel):
    """Summary data for a single league."""

    id: int = Field(..., description="League ID")
    name: str = Field(..., description="League name")
    country_id: int | None = Field(None, description="Country ID")
    country_name: str | None = Field(None, description="Country name")
    country_emoji: str | None = Field(None, description="Country flag emoji")
    sport_id: int | None = Field(None, description="Sport ID")
    sport_name: str | None = Field(None, description="Sport name")
    active: bool = Field(..., description="Whether the league is active")
    last_update: date | None = Field(
        None,
        description="Last data update timestamp")
    slug: str = Field(..., description="URL-friendly league slug")


class LeaguesListResponse(BaseModel):
    """Response model for GET /leagues."""

    leagues: list[LeagueSummary] = Field(..., description="League list")
    total_count: int = Field(..., description="Total number of leagues")


class LeagueSeasonResponse(BaseModel):
    """Season available for a league."""

    season_id: int = Field(..., description="Season ID")
    years: str = Field(..., description="Season years label")
    match_count: int = Field(..., description="Number of matches in season")


class LeagueDetails(LeagueSummary):
    """Detailed league metadata for navigation and filters."""

    current_season_id: int | None = Field(
        None,
        description="Current season ID configured for the league")
    tier: int | None = Field(None, description="League tier level")
    has_player_stats: bool = Field(
        ...,
        description="Whether player stats are available")
    match_count: int = Field(..., description="Total matches in the league")
    seasons: list[LeagueSeasonResponse] = Field(
        ...,
        description="Seasons with matches for this league")


class LeagueSeasonsListResponse(BaseModel):
    """Response model for GET /leagues/{league_id}/seasons."""

    seasons: list[LeagueSeasonResponse] = Field(
        ...,
        description="Season list")
    total_count: int = Field(..., description="Total number of seasons")


class LeagueRoundResponse(BaseModel):
    """Round metadata for a league season."""

    round_number: int = Field(..., description="Round number")
    game_date: str = Field(..., description="Latest game date in the round")


class LeagueRoundsListResponse(BaseModel):
    """Response model for GET /leagues/{league_id}/rounds/{season_id}."""

    rounds: list[LeagueRoundResponse] = Field(..., description="Round list")
    total_count: int = Field(..., description="Total number of rounds")
