"""Extract per-team seasonal rating progress from the ML timeline.

Uses ``compute_ratings_timeline`` as the single source of Elo values.
This module never reimplements rating updates — it only maps metric
columns and projects pre/post snapshots onto team DTOs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from typing import Literal
from typing import Mapping

import pandas as pd

from models.pipeline.features.ratings import compute_ratings_timeline

RatingMetric = Literal["elo"]
RatingParams = Mapping[str, Any] | None


@dataclass(frozen=True)
class RatingSeriesColumns:
    """Column names for pre-match and post-match ratings of one metric."""

    home_pre: str
    away_pre: str
    home_post: str
    away_post: str


@dataclass(frozen=True)
class RatingPoint:
    """One post-match rating observation for a team in the target season."""

    match_id: int
    round_number: int | None
    played_at: datetime
    rating: float


@dataclass(frozen=True)
class TeamRatingProgress:
    """Seasonal rating series and summary for one participating team."""

    team_id: int
    team_name: str
    team_shortcut: str | None
    start_rating: float
    current_rating: float
    change: float
    current_rank: int
    points: list[RatingPoint]


@dataclass(frozen=True)
class RatingProgressResult:
    """Full seasonal rating-progress payload for API, PNG and CLI."""

    league_id: int
    league_name: str
    season_id: int
    season_years: str
    metric: RatingMetric
    last_played_match_id: int | None
    last_played_at: datetime | None
    teams: list[TeamRatingProgress]
    biggest_rise: TeamRatingProgress | None
    biggest_fall: TeamRatingProgress | None


# Mapowanie miary na kolumny osi czasu — dziś tylko ELO, gotowe na GAP/Czech.
RATING_SERIES_COLUMNS: dict[RatingMetric, RatingSeriesColumns] = {
    "elo": RatingSeriesColumns(
        home_pre="home_elo",
        away_pre="away_elo",
        home_post="home_elo_post",
        away_post="away_elo_post")
}


def series_columns_for(metric: RatingMetric) -> RatingSeriesColumns:
    """Return timeline column mapping for the requested metric."""
    try:
        return RATING_SERIES_COLUMNS[metric]
    except KeyError as exc:
        raise ValueError(f"Unsupported rating metric: {metric}") from exc


def build_ratings_timeline(
        matches: pd.DataFrame,
        params: RatingParams = None) -> pd.DataFrame:
    """Return the canonical leakage-safe ratings timeline for ``matches``.

    Pass the full country warmup frame from the repository so early-season
    pre-match ratings already include prior finished games.
    """
    return compute_ratings_timeline(matches, params=params)


def extract_team_progress(
        timeline: pd.DataFrame,
        target_league_id: int | None,
        target_season_id: int,
        participants: pd.DataFrame,
        metric: RatingMetric = "elo") -> list[TeamRatingProgress]:
    """Build per-team progress from a ratings timeline DataFrame.

    Start rating is the first pre-match value in the filtered window.
    Points are successive post-match values. When ``target_league_id``
    is ``None``, all leagues in ``target_season_id`` are included
    (country-wide chart). Timeline row order is preserved.
    """
    columns = series_columns_for(metric)
    if timeline.empty or participants.empty:
        return []

    season_mask = timeline["season"] == target_season_id
    if target_league_id is None:
        season_matches = timeline[season_mask]
    else:
        season_matches = timeline[
            season_mask & (timeline["league"] == target_league_id)]
    if season_matches.empty:
        return []

    participant_meta = _participant_lookup(participants)
    teams: list[TeamRatingProgress] = []
    for team_id, meta in participant_meta.items():
        progress = _extract_one_team(
            season_matches=season_matches,
            team_id=team_id,
            team_name=meta["team_name"],
            team_shortcut=meta["team_shortcut"],
            columns=columns)
        if progress is not None:
            teams.append(progress)

    return _with_ranks(teams)


def compute_team_rating_progress(
        matches: pd.DataFrame,
        target_league_id: int | None,
        target_season_id: int,
        participants: pd.DataFrame,
        metric: RatingMetric = "elo",
        params: RatingParams = None) -> list[TeamRatingProgress]:
    """Compute timeline then extract seasonal progress for participants."""
    timeline = build_ratings_timeline(matches, params=params)
    return extract_team_progress(
        timeline=timeline,
        target_league_id=target_league_id,
        target_season_id=target_season_id,
        participants=participants,
        metric=metric)


def _participant_lookup(
        participants: pd.DataFrame) -> dict[int, dict[str, str | None]]:
    """Index participants by team id with display name and shortcut."""
    lookup: dict[int, dict[str, str | None]] = {}
    for _, row in participants.iterrows():
        team_id = int(row["team_id"])
        shortcut = row.get("team_shortcut")
        if shortcut is None or pd.isna(shortcut):
            shortcut_value: str | None = None
        else:
            shortcut_value = str(shortcut)
        lookup[team_id] = {
            "team_name": str(row["team_name"]),
            "team_shortcut": shortcut_value
        }
    return lookup


def _extract_one_team(
        *,
        season_matches: pd.DataFrame,
        team_id: int,
        team_name: str,
        team_shortcut: str | None,
        columns: RatingSeriesColumns) -> TeamRatingProgress | None:
    """Project one team's pre/post ratings onto a progress DTO."""
    points: list[RatingPoint] = []
    start_rating: float | None = None
    # Kolejność wierszy = kolejność osi czasu; bez ponownego sortowania.
    for _, row in season_matches.iterrows():
        home_id = int(row["home_team"])
        away_id = int(row["away_team"])
        if team_id == home_id:
            pre_rating = float(row[columns.home_pre])
            post_rating = float(row[columns.home_post])
        elif team_id == away_id:
            pre_rating = float(row[columns.away_pre])
            post_rating = float(row[columns.away_post])
        else:
            continue
        if start_rating is None:
            start_rating = pre_rating
        points.append(RatingPoint(
            match_id=int(row["id"]),
            round_number=_as_optional_int(row.get("round")),
            played_at=_as_datetime(row["game_date"]),
            rating=post_rating))

    if start_rating is None or not points:
        return None

    current_rating = points[-1].rating
    return TeamRatingProgress(
        team_id=team_id,
        team_name=team_name,
        team_shortcut=team_shortcut,
        start_rating=start_rating,
        current_rating=current_rating,
        change=current_rating - start_rating,
        current_rank=0,
        points=points)


def _with_ranks(
        teams: list[TeamRatingProgress]) -> list[TeamRatingProgress]:
    """Assign ranks by current rating (desc), then stable team_id."""
    ordered = sorted(
        teams,
        key=lambda team: (-team.current_rating, team.team_id))
    ranked: list[TeamRatingProgress] = []
    for index, team in enumerate(ordered, start=1):
        ranked.append(TeamRatingProgress(
            team_id=team.team_id,
            team_name=team.team_name,
            team_shortcut=team.team_shortcut,
            start_rating=team.start_rating,
            current_rating=team.current_rating,
            change=team.change,
            current_rank=index,
            points=team.points))
    return ranked


def _as_optional_int(value: object) -> int | None:
    """Convert round-like values to int, treating missing as ``None``."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_datetime(value: object) -> datetime:
    """Normalize pandas/DB timestamps to ``datetime``."""
    if isinstance(value, datetime):
        return value
    return pd.Timestamp(value).to_pydatetime()
