"""Pydantic schemas for match schedule and detail endpoints."""

from __future__ import annotations
from datetime import date, datetime
from pydantic import BaseModel, Field

from api.schemas.odds import OddsItem
from api.schemas.prediction import MatchPredictionItem


class TeamInMatch(BaseModel):
    """Team reference embedded in a match response."""

    id: int = Field(..., description="Team ID")
    name: str = Field(..., description="Team name")
    shortcut: str | None = Field(None, description="Team shortcut")


class MatchSummary(BaseModel):
    """Summary data for a single match in a league schedule."""

    id: int = Field(..., description="Match ID")
    league_id: int = Field(..., description="League ID")
    season_id: int = Field(..., description="Season ID")
    round: int | None = Field(None, description="Round number")
    game_date: datetime | date = Field(..., description="Match kick-off date")
    home_team: TeamInMatch = Field(..., description="Home team")
    away_team: TeamInMatch = Field(..., description="Away team")
    home_goals: int | None = Field(None, description="Home team goals")
    away_goals: int | None = Field(None, description="Away team goals")
    result: str = Field(..., description="Match result code")
    is_played: bool = Field(
        ...,
        description="Whether the match has been played")


class LeagueMatchesListResponse(BaseModel):
    """Response model for GET /leagues/{league_id}/matches."""

    matches: list[MatchSummary] = Field(..., description="Match list")
    total_count: int = Field(..., description="Total number of matches")
    league_id: int = Field(..., description="League ID")
    season_id: int = Field(..., description="Season ID")


class MatchBasicStats(BaseModel):
    """Aggregated in-match statistics stored on the match row."""

    home_xg: float | None = Field(None, description="Home expected goals")
    away_xg: float | None = Field(None, description="Away expected goals")
    home_possession: int | None = Field(None, description="Home ball possession %")
    away_possession: int | None = Field(None, description="Away ball possession %")
    home_shots: int | None = Field(None, description="Home total shots")
    away_shots: int | None = Field(None, description="Away total shots")
    home_shots_on_goal: int | None = Field(
        None,
        description="Home shots on goal")
    away_shots_on_goal: int | None = Field(
        None,
        description="Away shots on goal")
    home_corners: int | None = Field(None, description="Home corner kicks")
    away_corners: int | None = Field(None, description="Away corner kicks")
    home_fouls: int | None = Field(None, description="Home fouls")
    away_fouls: int | None = Field(None, description="Away fouls")
    home_yellow_cards: int | None = Field(
        None,
        description="Home yellow cards")
    away_yellow_cards: int | None = Field(
        None,
        description="Away yellow cards")
    home_red_cards: int | None = Field(None, description="Home red cards")
    away_red_cards: int | None = Field(None, description="Away red cards")


class MatchDetails(BaseModel):
    """Full match payload for the match detail page."""

    id: int = Field(..., description="Match ID")
    league_id: int = Field(..., description="League ID")
    season_id: int = Field(..., description="Season ID")
    round: int | None = Field(None, description="Round number")
    game_date: datetime | date = Field(..., description="Match kick-off date")
    home_team: TeamInMatch = Field(..., description="Home team")
    away_team: TeamInMatch = Field(..., description="Away team")
    home_goals: int | None = Field(None, description="Home team goals")
    away_goals: int | None = Field(None, description="Away team goals")
    result: str = Field(..., description="Match result code")
    is_played: bool = Field(
        ...,
        description="Whether the match has been played")
    final_predictions: list[MatchPredictionItem] = Field(
        ...,
        description="Final model predictions")
    odds: list[OddsItem] = Field(..., description="Bookmaker odds")
    stats: MatchBasicStats | None = Field(
        None,
        description="Basic match statistics when available")
