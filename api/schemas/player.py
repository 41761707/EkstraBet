"""Pydantic schemas for player statistics endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PlayerSportResponse(BaseModel):
    """Sport exposed on the players page."""

    sport_id: int = Field(..., description="Sport ID")
    label: str = Field(..., description="Display label")
    emoji: str = Field(..., description="Sport emoji")
    available: bool = Field(..., description="Whether the sport is enabled")


class PlayerSportsListResponse(BaseModel):
    """Response for GET /players/sports."""

    sports: list[PlayerSportResponse] = Field(..., description="Sport list")
    total_count: int = Field(..., description="Total number of sports")


class PlayerCountryOption(BaseModel):
    """Country filter option for player pages."""

    id: int = Field(..., description="Country ID")
    name: str = Field(..., description="Country name")
    emoji: str | None = Field(None, description="Country flag emoji")


class PlayerCountriesResponse(BaseModel):
    """Response for country filter options."""

    countries: list[PlayerCountryOption] = Field(
        ...,
        description="Country list")
    total_count: int = Field(..., description="Total number of countries")


class PlayerTeamOption(BaseModel):
    """Team filter option for player pages."""

    id: int = Field(..., description="Team ID")
    name: str = Field(..., description="Team name")
    country_id: int | None = Field(None, description="Country ID")


class PlayerTeamsResponse(BaseModel):
    """Response for team filter options."""

    teams: list[PlayerTeamOption] = Field(..., description="Team list")
    total_count: int = Field(..., description="Total number of teams")


class PlayerSeasonOption(BaseModel):
    """Season filter option for player pages."""

    season_id: int = Field(..., description="Season ID")
    years: str = Field(..., description="Season label")


class PlayerSeasonsResponse(BaseModel):
    """Response for season filter options."""

    seasons: list[PlayerSeasonOption] = Field(
        ...,
        description="Season list")
    total_count: int = Field(..., description="Total number of seasons")


class FootballPlayerSummary(BaseModel):
    """Player list item."""

    id: int = Field(..., description="Player ID")
    common_name: str = Field(..., description="Player display name")
    current_team_id: int = Field(..., description="Current team ID")
    position: str | None = Field(None, description="Player position")


class FootballPlayersListResponse(BaseModel):
    """Response for football player list."""

    players: list[FootballPlayerSummary] = Field(
        ...,
        description="Player list")
    total_count: int = Field(..., description="Total number of players")
    season_id: int = Field(..., description="Selected season ID")


class FootballPlayerStatsSummary(BaseModel):
    """Aggregated football player stats for selected matches."""

    goals: int = Field(..., description="Total goals")
    assists: int = Field(..., description="Total assists")
    shots: int = Field(..., description="Total shots")
    shots_on_target: int = Field(..., description="Total shots on target")
    fouls_conceded: int = Field(..., description="Total fouls conceded")
    yellow_cards: int = Field(..., description="Total yellow cards")


class FootballPlayerMatchStat(BaseModel):
    """Single-match football player stats row."""

    match_id: int = Field(..., description="Match ID")
    home_team: str = Field(..., description="Home team name")
    away_team: str = Field(..., description="Away team name")
    match_date: str = Field(..., description="Match date label")
    opponent_shortcut: str = Field(..., description="Opponent shortcut")
    goals: int = Field(..., description="Goals scored")
    assists: int = Field(..., description="Assists")
    shots: int = Field(..., description="Shots")
    shots_on_target: int = Field(..., description="Shots on target")
    fouls_conceded: int = Field(..., description="Fouls conceded")
    yellow_cards: int = Field(..., description="Yellow cards")


class FootballPlayerMatchStatsResponse(BaseModel):
    """Response for football player match log."""

    player_id: int = Field(..., description="Player ID")
    season_id: int = Field(..., description="Season ID")
    match_count: int = Field(..., description="Number of returned matches")
    summary: FootballPlayerStatsSummary = Field(
        ...,
        description="Aggregated totals")
    matches: list[FootballPlayerMatchStat] = Field(
        ...,
        description="Match log")


class HockeyPlayerStatsSummary(BaseModel):
    """Aggregated hockey player stats for selected matches."""

    is_goalie: bool = Field(..., description="Whether the player is a goalie")
    points: int | None = Field(None, description="Total points")
    goals: int | None = Field(None, description="Total goals")
    assists: int | None = Field(None, description="Total assists")
    plus_minus: int | None = Field(None, description="Total plus-minus")
    penalty_minutes: int | None = Field(None, description="Total penalty minutes")
    average_penalty_minutes: float | None = Field(
        None,
        description="Average penalty minutes")
    average_sog: float | None = Field(None, description="Average shots on goal")
    average_toi: str | None = Field(None, description="Average time on ice")
    shots_against: float | None = Field(None, description="Average shots faced")
    shots_saved: float | None = Field(None, description="Average saves")
    saves_acc: float | None = Field(None, description="Average save percentage")


class HockeyPlayerMatchStat(BaseModel):
    """Single-match hockey player stats row."""

    match_id: int = Field(..., description="Match ID")
    home_team: str = Field(..., description="Home team name")
    away_team: str = Field(..., description="Away team name")
    match_date: str = Field(..., description="Match date label")
    opponent_shortcut: str = Field(..., description="Opponent shortcut")
    toi: str = Field(..., description="Time on ice")
    toi_minutes: float = Field(..., description="Time on ice in minutes")
    points: int | None = Field(None, description="Points")
    goals: int | None = Field(None, description="Goals")
    assists: int | None = Field(None, description="Assists")
    plus_minus: int | None = Field(None, description="Plus-minus")
    penalty_minutes: int | None = Field(None, description="Penalty minutes")
    sog: int | None = Field(None, description="Shots on goal")
    shots_against: int | None = Field(None, description="Shots faced")
    shots_saved: int | None = Field(None, description="Saves")
    saves_acc: float | None = Field(None, description="Save percentage")


class HockeyPlayerMatchStatsResponse(BaseModel):
    """Response for hockey player match log."""

    player_id: int = Field(..., description="Player ID")
    season_id: int = Field(..., description="Season ID")
    match_count: int = Field(..., description="Number of returned matches")
    player_role: str = Field(..., description="Player role")
    summary: HockeyPlayerStatsSummary = Field(
        ...,
        description="Aggregated totals or averages")
    matches: list[HockeyPlayerMatchStat] = Field(
        ...,
        description="Match log")


class TeamPlayerStatLeaderRow(BaseModel):
    """One player in a team leaderboard for a selected stat."""

    player_id: int = Field(..., description="Player ID")
    player_name: str = Field(..., description="Player display name")
    total: int = Field(..., description="Aggregated stat total")
    appearances: int = Field(..., description="Matches counted")
    average: float = Field(..., description="Average per appearance")


class TeamPlayerStatLeadersResponse(BaseModel):
    """Aggregated player leaders for a team and match set."""

    team_id: int = Field(..., description="Team ID")
    season_id: int = Field(..., description="Season ID")
    stat: str = Field(..., description="Aggregated statistic key")
    match_ids: list[int] = Field(..., description="Match IDs used")
    leaders: list[TeamPlayerStatLeaderRow] = Field(
        ...,
        description="Leaderboard rows")
