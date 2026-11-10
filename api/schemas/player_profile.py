"""Pydantic schemas for the shared player profile."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel
from pydantic import Field

from api.schemas.player import HockeyPlayerStatsSummary


class PlayerProfileFilters(BaseModel):
    """Filters shared by every sport profile."""

    player_id: int = Field(..., description="Player ID")
    season_id: int | None = Field(
        None,
        description="Season ID, or all seasons when omitted")
    opponent_team_id: int | None = Field(
        None,
        description="Opponent team ID")
    own_team_id: int | None = Field(
        None,
        description="Club from the stats row of that match")
    teammate_id: int | None = Field(
        None,
        description="Teammate with a stats row on the same side")


class HockeyPlayerEventSplit(BaseModel):
    """Hockey event counters for the selected slice."""

    goals: int = Field(..., description="Goals, event 181")
    power_play_goals: int = Field(
        ...,
        description="Power-play goals")
    empty_net_goals: int = Field(..., description="Empty-net goals")
    goals_period_1: int = Field(..., description="Goals in period 1")
    goals_period_2: int = Field(..., description="Goals in period 2")
    goals_period_3: int = Field(..., description="Goals in period 3")
    goals_overtime: int = Field(..., description="Overtime goals")
    shootout_goals: int = Field(..., description="Shootout goals")
    minor_penalties: int = Field(..., description="Minor penalties")
    major_penalties: int = Field(..., description="Major penalties")
    misconduct_penalties: int = Field(
        ...,
        description="Misconduct penalties")
    unsportsmanlike_penalties: int = Field(
        ...,
        description="Unsportsmanlike penalties")
    disallowed_goals: int = Field(..., description="Disallowed goals")


class HockeyPlayerSliceMatch(BaseModel):
    """One hockey match in a profile slice."""

    match_id: int = Field(..., description="Match ID")
    game_date: str = Field(..., description="Match date as YYYY-MM-DD")
    season_id: int = Field(..., description="Season ID")
    season_years: str = Field(..., description="Season label")
    own_team_id: int = Field(..., description="Club on the stats row")
    own_team_name: str = Field(..., description="Club name")
    opponent_team_id: int = Field(..., description="Opponent team ID")
    opponent_name: str = Field(..., description="Opponent name")
    opponent_shortcut: str = Field(..., description="Opponent shortcut")
    venue: Literal["home", "away"] = Field(
        ...,
        description="Home when the stats club is the home side")
    home_goals: int | None = Field(None, description="Home goals")
    away_goals: int | None = Field(None, description="Away goals")
    result: str | None = Field(None, description="Match result code")
    toi: str = Field(..., description="Time on ice")
    toi_minutes: float = Field(..., description="Time on ice in minutes")
    points: int | None = Field(None, description="Points")
    goals: int | None = Field(None, description="Goals")
    assists: int | None = Field(None, description="Assists")
    plus_minus: int | None = Field(None, description="Plus-minus")
    penalty_minutes: int | None = Field(
        None,
        description="Penalty minutes")
    sog: int | None = Field(None, description="Shots on goal")
    shots_against: int | None = Field(None, description="Shots faced")
    shots_saved: int | None = Field(None, description="Saves")
    saves_acc: float | None = Field(None, description="Save percentage")
    power_play_goals: int = Field(..., description="Power-play goals")
    empty_net_goals: int = Field(..., description="Empty-net goals")


class HockeyPlayerProfileBody(BaseModel):
    """Hockey body inside the shared profile envelope."""

    sport_id: Literal[2] = Field(..., description="Hockey sport ID")
    player_role: Literal["skater", "goalie"] = Field(
        ...,
        description="Skater, or goalie when position is G")
    summary: HockeyPlayerStatsSummary = Field(
        ...,
        description="Box-score summary")
    event_split: HockeyPlayerEventSplit = Field(
        ...,
        description="Hockey event counters")
    matches: list[HockeyPlayerSliceMatch] = Field(
        ...,
        description="Match log")


class PlayerProfileResponse(BaseModel):
    """Envelope shared by every sport profile."""

    player_id: int = Field(..., description="Player ID")
    player_name: str = Field(..., description="Player display name")
    sport_id: int = Field(..., description="Sport ID")
    filters: PlayerProfileFilters = Field(
        ...,
        description="Applied filters")
    match_count: int = Field(..., description="Matches in the slice")
    truncated: bool = Field(
        ...,
        description="True when the slice hit the match limit")
    # Kolejny sport zamienia ten typ na unię rozróżnianą po sport_id
    # (HockeyPlayerProfileBody | FootballPlayerProfileBody | ...),
    # bez zmiany pozostałych pól koperty.
    body: HockeyPlayerProfileBody = Field(
        ...,
        description="Sport-specific profile body")


class PlayerSearchHit(BaseModel):
    """One player row from the profile teammate search."""

    player_id: int = Field(..., description="Player ID")
    player_name: str = Field(..., description="Player display name")
    position: str | None = Field(None, description="Player position")
    current_team_name: str | None = Field(
        None,
        description="Current club name")


class PlayerSearchResponse(BaseModel):
    """Teammate search result. total_count equals len(players)."""

    players: list[PlayerSearchHit] = Field(..., description="Matching players")
    total_count: int = Field(..., description="Length of players")
