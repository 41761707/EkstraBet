"""Pydantic schemas for league standings endpoints."""

from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field

StandingScope = Literal["overall", "home", "away", "ou_btts"]


class TraditionalStandingRow(BaseModel):
    """Traditional league table row with points and goal difference."""

    position: int = Field(..., description="Table position")
    team_id: int = Field(..., description="Team ID")
    team_name: str = Field(..., description="Team name")
    played: int = Field(..., description="Matches played")
    wins: int = Field(..., description="Wins")
    draws: int = Field(..., description="Draws")
    losses: int = Field(..., description="Losses")
    goals_for: int = Field(..., description="Goals scored")
    goals_against: int = Field(..., description="Goals conceded")
    goal_difference: int = Field(..., description="Goal difference")
    points: int = Field(..., description="League points")


class OuBttsStandingRow(BaseModel):
    """Over/Under and BTTS statistics per team."""

    position: int = Field(..., description="Display position")
    team_id: int = Field(..., description="Team ID")
    team_name: str = Field(..., description="Team name")
    played: int = Field(..., description="Matches played")
    btts_count: int = Field(..., description="Both teams scored count")
    btts_percentage: float = Field(
        ...,
        description="BTTS occurrence percentage")
    over_1_5_count: int = Field(..., description="Over 1.5 goals count")
    over_1_5_percentage: float = Field(
        ...,
        description="Over 1.5 goals percentage")
    over_2_5_count: int = Field(..., description="Over 2.5 goals count")
    over_2_5_percentage: float = Field(
        ...,
        description="Over 2.5 goals percentage")
    over_3_5_count: int = Field(..., description="Over 3.5 goals count")
    over_3_5_percentage: float = Field(
        ...,
        description="Over 3.5 goals percentage")


class LeagueStandingsResponse(BaseModel):
    """Response model for GET /leagues/{league_id}/standings."""

    league_id: int = Field(..., description="League ID")
    season_id: int = Field(..., description="Season ID")
    scope: StandingScope = Field(..., description="Standings scope")
    standings: list[TraditionalStandingRow | OuBttsStandingRow] = Field(
        ...,
        description="Standings rows for the requested scope")
    total_count: int = Field(..., description="Number of teams in table")
