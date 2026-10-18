"""Response models for upcoming NHL skater event rankings."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from pydantic import Field


HockeyPlayerEventMetric = Literal["point", "goal", "assist", "shot"]


class HockeyPlayerEventRankingRow(BaseModel):
    """One skater on a single event board."""

    rank: int = Field(
        ...,
        description="1-based position assigned before the limit cut")
    player_id: int = Field(..., description="Player ID")
    player_name: str = Field(..., description="Player display name")
    team_id: int = Field(..., description="Skater club ID")
    team_name: str = Field(..., description="Skater club name")
    team_shortcut: str | None = Field(
        None,
        description="Skater club shortcut")
    match_id: int = Field(..., description="Match ID")
    game_date: datetime = Field(
        ...,
        description="Kickoff as stored on the match")
    opponent_name: str = Field(..., description="Opponent club name")
    opponent_shortcut: str | None = Field(
        None,
        description="Opponent club shortcut")
    is_home: bool = Field(
        ...,
        description="Whether the skater club is at home")
    probability: float = Field(
        ...,
        description="P(stat > line) in percent, from 0 to 100")
    expected_shots: float | None = Field(
        None,
        description="Expected shots, only on the shot board")


class HockeyPlayerEventRanking(BaseModel):
    """One of the four event boards."""

    metric: HockeyPlayerEventMetric = Field(
        ...,
        description="Board key: point, goal, assist or shot")
    label: str = Field(..., description="Polish board title")
    hint: str = Field(..., description="Short probability label")
    rows: list[HockeyPlayerEventRankingRow] = Field(
        ...,
        description="Skaters ordered by descending probability")


class HockeyPlayerEventRankingsResponse(BaseModel):
    """Four boards for unplayed matches that have hockey props."""

    match_count: int = Field(
        ...,
        description="Unplayed matches that still have a kept skater")
    rankings: list[HockeyPlayerEventRanking] = Field(
        ...,
        description="Point, goal, assist and shot, in that order")
