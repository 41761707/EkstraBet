"""Pydantic schemas for NHL/NBA league page endpoints."""

from __future__ import annotations
from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, Field
from api.schemas.match import MatchSummary

SportPhase = Literal[100, 200]
SportStandingScope = Literal["overall", "home", "away"]


class SportTeamSummary(BaseModel):
    """Team entry for sport league team lists."""
    team_id: int = Field(..., description="Team ID")
    team_name: str = Field(..., description="Team name")
    team_shortcut: str | None = Field(None, description="Team shortcut")


class SportTeamsListResponse(BaseModel):
    """Teams available in a sport league season."""
    teams: list[SportTeamSummary] = Field(..., description="Teams")
    total_count: int = Field(..., description="Total teams")


class SportMatchesListResponse(BaseModel):
    """Matches for NHL/NBA league pages."""
    matches: list[MatchSummary] = Field(..., description="Matches")
    total_count: int = Field(..., description="Total matches")
    league_id: int = Field(..., description="League ID")
    season_id: int = Field(..., description="Season ID")


class HockeyStandingRow(BaseModel):
    """Single row in an NHL standings table."""
    position: int = Field(..., description="Table position")
    team_id: int = Field(..., description="Team ID")
    team_name: str = Field(..., description="Team name")
    played: int = Field(..., description="Games played")
    wins: int = Field(..., description="Wins")
    losses: int = Field(..., description="Losses")
    goals_for: int = Field(..., description="Goals for")
    goals_against: int = Field(..., description="Goals against")
    goal_difference: int = Field(..., description="Goal difference")
    points: int = Field(..., description="Points")
    overtime_wins: int = Field(..., description="Overtime wins")
    overtime_losses: int = Field(..., description="Overtime losses")


class BasketballStandingRow(BaseModel):
    """Single row in an NBA standings table."""
    position: int = Field(..., description="Table position")
    team_id: int = Field(..., description="Team ID")
    team_name: str = Field(..., description="Team name")
    played: int = Field(..., description="Games played")
    wins: int = Field(..., description="Wins")
    losses: int = Field(..., description="Losses")
    points_for: int = Field(..., description="Points scored")
    points_against: int = Field(..., description="Points allowed")
    point_difference: int = Field(..., description="Point difference")
    win_percentage: float = Field(..., description="Win percentage")


class SportStandingsResponse(BaseModel):
    """Sport-specific standings payload."""
    league_id: int = Field(..., description="League ID")
    season_id: int = Field(..., description="Season ID")
    scope: SportStandingScope = Field(..., description="Standings scope")
    sport_id: int = Field(..., description="Sport ID")
    hockey_standings: list[HockeyStandingRow] | None = Field(
        None, description="Hockey standings")
    basketball_standings: list[BasketballStandingRow] | None = Field(
        None, description="Basketball standings")
    total_count: int = Field(..., description="Total teams")


class HockeyTeamHistoryPoint(BaseModel):
    """One match in hockey team history charts."""
    match_id: int
    match_date: str
    opponent_shortcut: str
    team_goals: int
    opponent_goals: int
    total_goals: int
    team_shots_on_goal: int | None = None
    opponent_shots_on_goal: int | None = None
    first_period_goals: int | None = None
    result: str
    home_team_name: str
    away_team_name: str
    home_goals: int
    away_goals: int


class BasketballTeamHistoryPoint(BaseModel):
    """One match in basketball team history charts."""
    match_id: int
    match_date: str
    opponent_shortcut: str
    team_points: int
    opponent_points: int
    total_points: int
    result: str
    home_team_name: str
    away_team_name: str
    home_points: int
    away_points: int


class SportTeamHistoryResponse(BaseModel):
    """Recent team match history for sport league charts."""
    team_id: int = Field(..., description="Team ID")
    sport_id: int = Field(..., description="Sport ID")
    hockey_history: list[HockeyTeamHistoryPoint] | None = Field(
        None, description="Hockey history")
    basketball_history: list[BasketballTeamHistoryPoint] | None = Field(
        None, description="Basketball history")
    total_count: int = Field(..., description="History length")


class SportLeagueStatRow(BaseModel):
    """Generic per-team league stat row."""
    team_name: str
    team_shortcut: str
    matches_played: int | None = None
    avg_for: float | None = None
    avg_against: float | None = None
    field_goal_pct: float | None = None
    three_point_pct: float | None = None
    over_4_5_pct: float | None = None
    over_5_5_pct: float | None = None
    over_6_5_pct: float | None = None
    over_7_5_pct: float | None = None
    over_210_5_pct: float | None = None
    over_220_5_pct: float | None = None
    over_230_5_pct: float | None = None


class SportPointsDistributionSummary(BaseModel):
    """League-wide points distribution summary for NBA."""
    average_total: float
    median_total: float
    min_total: int
    max_total: int
    average_home: float
    average_away: float


class SportLeagueStatsResponse(BaseModel):
    """League stats for one sport category tab."""
    league_id: int
    season_id: int
    sport_id: int
    category: str
    rows: list[SportLeagueStatRow] = Field(default_factory=list)
    distribution: SportPointsDistributionSummary | None = None
