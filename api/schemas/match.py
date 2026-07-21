"""Pydantic schemas for match schedule and detail endpoints."""

from __future__ import annotations
from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, Field

from api.schemas.odds import OddsItem
from api.schemas.prediction import MatchPredictionItem

FormResult = Literal["W", "D", "L", "WPD", "PPD"]


class TeamInMatch(BaseModel):
    """Team reference embedded in a match response."""

    id: int = Field(..., description="Team ID")
    name: str = Field(..., description="Team name")
    shortcut: str | None = Field(None, description="Team shortcut")


class MatchScoreResolution(BaseModel):
    """Knockout match score metadata for extra time and penalties."""

    has_extra_time: bool = Field(
        ...,
        description="Whether the match went to extra time")
    has_penalties: bool = Field(
        ...,
        description="Whether the match was decided on penalties")
    post_ot_home_goals: int | None = Field(
        None,
        description="Home goals after extra time")
    post_ot_away_goals: int | None = Field(
        None,
        description="Away goals after extra time")
    penalties_home_goals: int | None = Field(
        None,
        description="Home penalty shootout goals")
    penalties_away_goals: int | None = Field(
        None,
        description="Away penalty shootout goals")
    overtime_winner: int | None = Field(
        None,
        description="Hockey OT winner (1=home, 2=away, 3=shootout)")
    shootout_winner: int | None = Field(
        None,
        description="Hockey SO winner (1=home, 2=away)")


class MatchSummary(BaseModel):
    """Summary data for a single match in a league schedule."""

    id: int = Field(..., description="Match ID")
    league_id: int = Field(..., description="League ID")
    season_id: int = Field(..., description="Season ID")
    round: int | None = Field(None, description="Round number")
    round_label: str | None = Field(
        None,
        description="User-facing round label with special round names resolved")
    game_date: datetime | date = Field(..., description="Match kick-off date")
    home_team: TeamInMatch = Field(..., description="Home team")
    away_team: TeamInMatch = Field(..., description="Away team")
    home_goals: int | None = Field(None, description="Home team goals")
    away_goals: int | None = Field(None, description="Away team goals")
    result: str = Field(..., description="Match result code")
    is_played: bool = Field(
        ...,
        description="Whether the match has been played")
    score_resolution: MatchScoreResolution | None = Field(
        None,
        description="Extra time and penalty metadata for cup matches")


class LeagueMatchesListResponse(BaseModel):
    """Response model for GET /leagues/{league_id}/matches."""

    matches: list[MatchSummary] = Field(..., description="Match list")
    total_count: int = Field(..., description="Total number of matches")
    league_id: int = Field(..., description="League ID")
    season_id: int = Field(..., description="Season ID")


class MatchBasicStats(BaseModel):
    """Aggregated in-match statistics stored on the match row."""

    home_goals: int | None = Field(None, description="Home team goals")
    away_goals: int | None = Field(None, description="Away team goals")
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
    home_free_kicks: int | None = Field(None, description="Home free kicks")
    away_free_kicks: int | None = Field(None, description="Away free kicks")
    home_corners: int | None = Field(None, description="Home corner kicks")
    away_corners: int | None = Field(None, description="Away corner kicks")
    home_offsides: int | None = Field(None, description="Home offsides")
    away_offsides: int | None = Field(None, description="Away offsides")
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


class HockeyMatchStats(BaseModel):
    """Hockey in-match statistics from matches and hockey_matches_add."""

    home_goals: int | None = Field(None, description="Home team goals")
    away_goals: int | None = Field(None, description="Away team goals")
    home_shots_on_goal: int | None = Field(
        None, description="Home shots on goal")
    away_shots_on_goal: int | None = Field(
        None, description="Away shots on goal")
    home_penalty_minutes: int | None = Field(
        None, description="Home penalty minutes")
    away_penalty_minutes: int | None = Field(
        None, description="Away penalty minutes")
    home_penalties: int | None = Field(
        None, description="Home penalties count")
    away_penalties: int | None = Field(
        None, description="Away penalties count")
    home_pp_goals: int | None = Field(
        None, description="Home power-play goals")
    away_pp_goals: int | None = Field(
        None, description="Away power-play goals")
    home_sh_goals: int | None = Field(
        None, description="Home short-handed goals")
    away_sh_goals: int | None = Field(
        None, description="Away short-handed goals")
    home_shots_accuracy: float | None = Field(
        None, description="Home shooting percentage")
    away_shots_accuracy: float | None = Field(
        None, description="Away shooting percentage")
    home_saves: int | None = Field(None, description="Home goalie saves")
    away_saves: int | None = Field(None, description="Away goalie saves")
    home_saves_accuracy: float | None = Field(
        None, description="Home save percentage")
    away_saves_accuracy: float | None = Field(
        None, description="Away save percentage")
    home_pp_accuracy: float | None = Field(
        None, description="Home power-play percentage")
    away_pp_accuracy: float | None = Field(
        None, description="Away power-play percentage")
    home_pk_accuracy: float | None = Field(
        None, description="Home penalty-kill percentage")
    away_pk_accuracy: float | None = Field(
        None, description="Away penalty-kill percentage")
    home_faceoffs_won: int | None = Field(
        None, description="Home faceoffs won")
    away_faceoffs_won: int | None = Field(
        None, description="Away faceoffs won")
    home_faceoffs_accuracy: float | None = Field(
        None, description="Home faceoff win percentage")
    away_faceoffs_accuracy: float | None = Field(
        None, description="Away faceoff win percentage")
    home_hits: int | None = Field(None, description="Home hits")
    away_hits: int | None = Field(None, description="Away hits")
    home_turnovers: int | None = Field(None, description="Home turnovers")
    away_turnovers: int | None = Field(None, description="Away turnovers")
    home_empty_net_goals: int | None = Field(
        None, description="Home empty-net goals")
    away_empty_net_goals: int | None = Field(
        None, description="Away empty-net goals")


class TeamSeasonMatchPoint(BaseModel):
    """Single played match used for team season charts."""

    match_id: int = Field(..., description="Match ID")
    match_date: date | datetime = Field(..., description="Match kick-off date")
    opponent_shortcut: str = Field(
        ...,
        description="Opponent shortcut for chart labels")
    opponent_name: str = Field(..., description="Opponent full name")
    total_goals: int = Field(..., description="Combined goals in the match")
    btts: bool = Field(
        ...,
        description="Whether both teams scored")
    result: FormResult = Field(
        ...,
        description="Match result from the team perspective")
    home_team_name: str = Field(..., description="Home team name")
    away_team_name: str = Field(..., description="Away team name")
    home_goals: int = Field(..., description="Home team goals")
    away_goals: int = Field(..., description="Away team goals")
    is_home: bool = Field(
        ...,
        description="Whether the profiled team played at home")
    team_cards: int = Field(
        ...,
        description="Yellow and red cards for the profiled team")
    opponent_cards: int = Field(
        ...,
        description="Yellow and red cards for the opponent")
    total_cards: int = Field(
        ...,
        description="Combined yellow and red cards in the match")
    team_offsides: int = Field(
        ...,
        description="Offsides for the profiled team")
    opponent_offsides: int = Field(
        ...,
        description="Offsides for the opponent")
    total_offsides: int = Field(
        ...,
        description="Combined offsides in the match")
    team_corners: int = Field(
        ...,
        description="Corner kicks for the profiled team")
    opponent_corners: int = Field(
        ...,
        description="Corner kicks for the opponent")
    total_corners: int = Field(
        ...,
        description="Combined corner kicks in the match")
    team_shots: int = Field(
        ...,
        description="Total shots for the profiled team")
    opponent_shots: int = Field(
        ...,
        description="Total shots for the opponent")
    total_shots: int = Field(
        ...,
        description="Combined shots in the match")
    team_shots_on_target: int = Field(
        ...,
        description="Shots on target for the profiled team")
    opponent_shots_on_target: int = Field(
        ...,
        description="Shots on target for the opponent")
    total_shots_on_target: int = Field(
        ...,
        description="Combined shots on target in the match")
    team_fouls: int = Field(
        ...,
        description="Fouls committed by the profiled team")
    opponent_fouls: int = Field(
        ...,
        description="Fouls committed by the opponent")
    total_fouls: int = Field(
        ...,
        description="Combined fouls in the match")
    team_penalty_minutes: int = Field(
        0,
        description="Penalty minutes for the profiled team")
    opponent_penalty_minutes: int = Field(
        0,
        description="Penalty minutes for the opponent")
    total_penalty_minutes: int = Field(
        0,
        description="Combined penalty minutes in the match")
    team_penalties: int = Field(
        0,
        description="Penalties count for the profiled team")
    opponent_penalties: int = Field(
        0,
        description="Penalties count for the opponent")
    total_penalties: int = Field(
        0,
        description="Combined penalties count in the match")
    first_period_goals: int | None = Field(
        None,
        description="Goals scored in the first period")


class HeadToHeadSummary(BaseModel):
    """Aggregated head-to-head statistics between two teams."""

    team_id: int = Field(..., description="Primary team ID")
    opponent_id: int = Field(..., description="Opponent team ID")
    played: int = Field(..., description="Head-to-head matches played")
    wins: int = Field(..., description="Wins for the primary team")
    draws: int = Field(..., description="Draws")
    losses: int = Field(..., description="Losses for the primary team")
    goals_for: int = Field(..., description="Goals scored by primary team")
    goals_conceded: int = Field(
        ...,
        description="Goals conceded by primary team")
    btts_count: int = Field(..., description="BTTS matches count")
    btts_percentage: float = Field(
        ...,
        description="BTTS occurrence percentage")
    avg_goals_per_match: float = Field(
        ...,
        description="Average total goals per H2H match")
    meetings: list[MatchSummary] = Field(
        ...,
        description="Recent head-to-head meetings")


class MatchPlayerStat(BaseModel):
    """Single player row in a football match boxscore."""

    player_id: int = Field(..., description="Player ID")
    player_name: str = Field(..., description="Player display name")
    team_id: int = Field(..., description="Team ID")
    team_name: str = Field(..., description="Team name")
    goals: int | None = Field(None, description="Goals scored")
    assists: int | None = Field(None, description="Assists")
    red_cards: int | None = Field(None, description="Red cards")
    yellow_cards: int | None = Field(None, description="Yellow cards")
    corners_won: int | None = Field(None, description="Corners won")
    shots: int | None = Field(None, description="Total shots")
    shots_on_target: int | None = Field(None, description="Shots on target")
    blocked_shots: int | None = Field(None, description="Blocked shots")
    passes: int | None = Field(None, description="Passes")
    crosses: int | None = Field(None, description="Crosses")
    tackles: int | None = Field(None, description="Tackles")
    offsides: int | None = Field(None, description="Offsides")
    fouls_conceded: int | None = Field(None, description="Fouls conceded")
    fouls_won: int | None = Field(None, description="Fouls won")
    saves: int | None = Field(None, description="Goalkeeper saves")


class HockeyGoalieBoxscoreRow(BaseModel):
    """Goalie row in a hockey match boxscore."""

    player_id: int = Field(..., description="Player ID")
    player_name: str = Field(..., description="Player display name")
    team_id: int = Field(..., description="Team ID")
    team_name: str = Field(..., description="Team name")
    points: int | None = Field(None, description="Points")
    penalty_minutes: int | None = Field(None, description="Penalty minutes")
    time_on_ice: str | None = Field(None, description="Time on ice")
    shots_against: int | None = Field(None, description="Shots against")
    shots_saved: int | None = Field(None, description="Saves")
    saves_accuracy: float | None = Field(None, description="Save percentage")


class HockeySkaterBoxscoreRow(BaseModel):
    """Skater row in a hockey match boxscore."""

    player_id: int = Field(..., description="Player ID")
    player_name: str = Field(..., description="Player display name")
    team_id: int = Field(..., description="Team ID")
    team_name: str = Field(..., description="Team name")
    goals: int | None = Field(None, description="Goals")
    assists: int | None = Field(None, description="Assists")
    points: int | None = Field(None, description="Points")
    plus_minus: int | None = Field(None, description="Plus/minus")
    penalty_minutes: int | None = Field(None, description="Penalty minutes")
    shots_on_goal: int | None = Field(None, description="Shots on goal")
    time_on_ice: str | None = Field(None, description="Time on ice")


class HockeyMatchBoxscore(BaseModel):
    """Hockey player stats grouped by goalies and skaters."""

    goalies: list[HockeyGoalieBoxscoreRow] = Field(
        default_factory=list,
        description="Goalie stats")
    skaters: list[HockeySkaterBoxscoreRow] = Field(
        default_factory=list,
        description="Skater stats")


PlayedBetterFinalAssessment = Literal[
    "HOME_PLAYED_BETTER",
    "DRAW",
    "AWAY_PLAYED_BETTER"]


class MatchModelAssessment(BaseModel):
    """Post-match quality assessment from an ML assessment model."""

    model_id: int = Field(..., description="Model ID")
    model_name: str = Field(..., description="Model name from models table")
    model_version: str = Field(..., description="Artifact / config version")
    assessment_type: str = Field(
        ...,
        description="Assessment family, e.g. PLAYED_BETTER")
    home_played_better_probability: float = Field(
        ...,
        description="Probability that the home team played better")
    draw_probability: float = Field(
        ...,
        description="Probability of quality draw")
    away_played_better_probability: float = Field(
        ...,
        description="Probability that the away team played better")
    final_assessment: PlayedBetterFinalAssessment = Field(
        ...,
        description="Chosen final assessment label")
    confidence: float | None = Field(
        None,
        description="Gap between top and second probability")
    dominance_score: float | None = Field(
        None,
        description="Raw home dominance score from the labeler")
    feature_snapshot: dict[str, float] | None = Field(
        None,
        description="Feature values used for the assessment")
    updated_at: datetime | None = Field(
        None,
        description="Last upsert timestamp")


class MatchDetails(BaseModel):
    """Full match payload for the match detail page."""

    id: int = Field(..., description="Match ID")
    league_id: int = Field(..., description="League ID")
    season_id: int = Field(..., description="Season ID")
    sport_id: int | None = Field(None, description="Sport ID")
    round: int | None = Field(None, description="Round number")
    round_label: str | None = Field(
        None,
        description="User-facing round label with special round names resolved")
    game_date: datetime | date = Field(..., description="Match kick-off date")
    home_team: TeamInMatch = Field(..., description="Home team")
    away_team: TeamInMatch = Field(..., description="Away team")
    home_goals: int | None = Field(None, description="Home team goals")
    away_goals: int | None = Field(None, description="Away team goals")
    result: str = Field(..., description="Match result code")
    is_played: bool = Field(
        ...,
        description="Whether the match has been played")
    score_resolution: MatchScoreResolution | None = Field(
        None,
        description="Extra time and penalty metadata for cup matches")
    final_predictions: list[MatchPredictionItem] = Field(
        ...,
        description="Final model predictions")
    odds: list[OddsItem] = Field(..., description="Bookmaker odds")
    stats: MatchBasicStats | None = Field(
        None,
        description="Football match statistics when available")
    hockey_stats: HockeyMatchStats | None = Field(
        None,
        description="Hockey match statistics when available")
    has_player_stats: bool = Field(
        ...,
        description="Whether the league exposes player boxscore data")
    head_to_head: HeadToHeadSummary = Field(
        ...,
        description="Head-to-head summary from the home team perspective")
    home_team_history: list[TeamSeasonMatchPoint] = Field(
        ...,
        description="Home team matches before this kick-off")
    away_team_history: list[TeamSeasonMatchPoint] = Field(
        ...,
        description="Away team matches before this kick-off")
    boxscore: list[MatchPlayerStat] | None = Field(
        None,
        description="Player stats when available for a played match")
    hockey_boxscore: HockeyMatchBoxscore | None = Field(
        None,
        description="Hockey player stats when available for a played match")
    model_assessments: list[MatchModelAssessment] = Field(
        default_factory=list,
        description="Post-match model assessments (e.g. PLAYED_BETTER)")
