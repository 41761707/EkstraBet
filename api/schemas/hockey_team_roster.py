"""Response models for the current NHL team roster."""

from pydantic import BaseModel
from pydantic import Field


class HockeyPlayerCountingStats(BaseModel):
    """Counting stats for one player in one sample of games."""

    games_played: int = Field(..., description="Games in this sample")
    goals: int = Field(..., description="Goals in this sample")
    assists: int = Field(..., description="Assists in this sample")
    points: int = Field(..., description="Points in this sample")
    shots_on_goal: int = Field(..., description="Shots on goal in this sample")
    shots_per_game: float | None = Field(
        None,
        description="Shots on goal per game, or null when games played is 0")
    average_toi: str | None = Field(
        None,
        description="Average time on ice as M:SS")
    save_percentage: float | None = Field(
        None,
        description="Goalie save percentage, 0-100")
    goals_against_average: float | None = Field(
        None,
        description="Goalie goals against per 60 minutes")


class HockeyPlayerStatWindows(BaseModel):
    """Season totals and the player's own recent games."""

    season: HockeyPlayerCountingStats = Field(
        ...,
        description="Full regular season for this team")
    last_5: HockeyPlayerCountingStats = Field(
        ...,
        description="The player's newest 5 regular-season games")
    last_10: HockeyPlayerCountingStats = Field(
        ...,
        description="The player's newest 10 regular-season games")


class HockeyPlayerRosterResponse(BaseModel):
    """One player on the current hockey roster."""

    player_id: int = Field(..., description="Player ID")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    common_name: str = Field(..., description="Display name")
    country: str = Field(..., description="Country name")
    position: str = Field(..., description="Position (G/D/LW/C/RW)")
    number: int | None = Field(None, description="Jersey number")
    line: int | None = Field(
        None,
        description=(
            "Forward line, defence pair, or goalie depth "
            "(1 primary, 2 backup)"))
    pp_unit: int | None = Field(
        None,
        description="Power-play unit (1 or 2), or null when unassigned")
    is_injured: bool = Field(..., description="Whether the player is injured")
    injury_status: str | None = Field(None, description="Short injury status")
    injury_note: str | None = Field(None, description="Injury note")
    games_played: int = Field(..., description="Season games played")
    goals: int = Field(..., description="Season goals")
    assists: int = Field(..., description="Season assists")
    points: int = Field(..., description="Season points")
    shots_on_goal: int = Field(..., description="Season shots on goal")
    shots_per_game: float | None = Field(
        None,
        description="Season shots on goal per game")
    average_toi: str | None = Field(
        None,
        description="Average time on ice as M:SS")
    save_percentage: float | None = Field(
        None,
        description="Goalie save percentage, 0-100")
    goals_against_average: float | None = Field(
        None,
        description="Goalie goals against per 60 minutes")
    stat_windows: HockeyPlayerStatWindows = Field(
        ...,
        description="Season, last 5 and last 10 counting stats")
    in_last_lineup: bool = Field(
        ...,
        description="Whether the player dressed in the last played match")


class HockeyLineupMoveResponse(BaseModel):
    """One dressed player whose even-strength seat changed."""

    player_id: int = Field(..., description="Player ID")
    common_name: str = Field(..., description="Display name")
    previous_position: str = Field(
        ...,
        description="Position in the previous match (G/D/LW/C/RW)")
    previous_line: int = Field(
        ...,
        description="Line, pair or goalie depth in the previous match")
    position: str = Field(..., description="Position on the current sheet")
    line: int = Field(
        ...,
        description="Line, pair or goalie depth on the current sheet")


class HockeyLineupChangesResponse(BaseModel):
    """Seat changes versus the previous played match."""

    match_date: str | None = Field(
        None,
        description="Calendar date of the previous match, YYYY-MM-DD")
    moves: list[HockeyLineupMoveResponse] = Field(
        ...,
        description="Players who changed line, pair or goalie role")


class HockeyRosterGroupResponse(BaseModel):
    """Players sharing one roster section."""

    group_id: str = Field(
        ...,
        description="F1-F4, D1-D3, G, injured or outside")
    players: list[HockeyPlayerRosterResponse] = Field(
        ...,
        description="Players in this section")


class HockeyTeamRosterResponse(BaseModel):
    """Current hockey roster with season counting stats."""

    team_id: int = Field(..., description="Team ID")
    team_name: str = Field(..., description="Team name")
    goalkeepers: list[HockeyPlayerRosterResponse] = Field(
        ...,
        description="Goalkeepers")
    defensemen: list[HockeyPlayerRosterResponse] = Field(
        ...,
        description="Defensemen")
    forwards: list[HockeyPlayerRosterResponse] = Field(
        ...,
        description="Forwards")
    injured_players: int = Field(..., description="Number of injured players")
    groups: list[HockeyRosterGroupResponse] = Field(
        ...,
        description="Line, pair, goalie, injured and outside sections")
    lineup_changes: HockeyLineupChangesResponse = Field(
        ...,
        description="Internal seat changes since the previous match")
