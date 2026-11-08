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
    points_adjustment: int = Field(
        ...,
        description="Sum of point adjustments; 0 when the team has none")
    adjustment_reason: str | None = Field(
        ...,
        description="Joined adjustment reasons, or null when there is none")
    zone_kind: str | None = Field(
        ...,
        description="Zone covering this position, or null when it is neutral")


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


class StandingZone(BaseModel):
    """One coloured block of positions on the overall table."""

    position_from: int = Field(..., description="First position in the zone")
    position_to: int = Field(..., description="Last position in the zone")
    zone_kind: str = Field(..., description="Zone kind key")
    band: str = Field(..., description="top or bot")
    label: str = Field(..., description="Polish legend label")
    sort_order: int = Field(..., description="Legend order")


class LeagueStandingsResponse(BaseModel):
    """Response model for GET /leagues/{league_id}/standings."""

    league_id: int = Field(..., description="League ID")
    season_id: int = Field(..., description="Season ID")
    scope: StandingScope = Field(..., description="Standings scope")
    standings: list[TraditionalStandingRow | OuBttsStandingRow] = Field(
        ...,
        description="Standings rows for the requested scope")
    zones: list[StandingZone] = Field(
        ...,
        description="Overall-table zones; empty outside overall or when unset")
    total_count: int = Field(..., description="Number of teams in table")
