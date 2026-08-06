"""Assemble seasonal rating-progress DTOs for API, PNG and CLI.

Orchestrates repository context, canonical timeline extraction, rise/fall
leaders and shared team filtering. Does not import FastAPI or Matplotlib.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Literal
from typing import cast

from backend.repositories.rating_progress_repository import FOOTBALL_SPORT_ID
from backend.repositories.rating_progress_repository import (
    RatingProgressContext)
from backend.repositories.rating_progress_repository import (
    fetch_country_rating_progress_context)
from backend.repositories.rating_progress_repository import (
    fetch_rating_progress_context)
from backend.sports.football.rating_progress import RatingMetric
from backend.sports.football.rating_progress import RatingProgressResult
from backend.sports.football.rating_progress import TeamRatingProgress
from backend.sports.football.rating_progress import (
    compute_team_rating_progress)

MAX_SELECTED_TEAMS = 40
SUPPORTED_METRICS: frozenset[str] = frozenset({"elo"})


class RatingProgressError(Exception):
    """Base domain error for rating-progress orchestration."""


class NonFootballLeagueError(RatingProgressError):
    """Raised when rating progress is requested for a non-football league."""


class RatingProgressFilterError(RatingProgressError):
    """Raised when team selection filters are invalid."""


def get_rating_progress(
        league_id: int,
        season_id: int,
        metric: str = "elo") -> RatingProgressResult | None:
    """Return seasonal rating progress or ``None`` when data is missing.

    Returns ``None`` when the league/season does not exist or the season
    has no finished matches. Raises ``NonFootballLeagueError`` for a
    known non-football league. Raises ``ValueError`` for an unsupported
    metric. The router distinguishes missing league/season from an empty
    season via a separate context check when needed.
    """
    resolved_metric = _resolve_metric(metric)
    context = fetch_rating_progress_context(league_id, season_id)
    if context is None:
        return None
    _ensure_football_league(context)
    if context.last_played_match_id is None:
        return None
    return _build_result(
        context,
        resolved_metric,
        target_league_id=context.league_id)


def get_country_rating_progress(
        country_id: int,
        season_id: int,
        metric: str = "elo") -> RatingProgressResult | None:
    """Return country-wide football progress across all leagues in a season.

    Series include every finished match in the country for ``season_id``
    (e.g. tier 1 + tier 2). Returns ``None`` when the country/season is
    missing or has no finished football matches.
    """
    resolved_metric = _resolve_metric(metric)
    context = fetch_country_rating_progress_context(country_id, season_id)
    if context is None:
        return None
    if context.last_played_match_id is None:
        return None
    # None = wszystkie ligi kraju w sezonie.
    return _build_result(
        context,
        resolved_metric,
        target_league_id=None)


def classify_missing_progress(
        league_id: int,
        season_id: int) -> Literal["not_found", "empty_season"]:
    """Classify why ``get_rating_progress`` returned ``None``.

    Call only after a ``None`` result. ``not_found`` means the league or
    season row is missing; ``empty_season`` means both exist but there is
    no finished football match yet.
    """
    context = fetch_rating_progress_context(league_id, season_id)
    if context is None:
        return "not_found"
    return "empty_season"


def select_teams(
        result: RatingProgressResult,
        team_ids: list[int] | None = None,
        top: int | None = None) -> RatingProgressResult:
    """Filter a progress result by explicit team ids or current-rating top N.

    ``team_ids`` and ``top`` are mutually exclusive. At most
    ``MAX_SELECTED_TEAMS`` teams may be selected. League ranks on each
    team are preserved; rise/fall leaders are recomputed for the
    filtered subset.
    """
    if team_ids is not None and top is not None:
        raise RatingProgressFilterError(
            "Parameters team_ids and top are mutually exclusive")
    if team_ids is not None:
        filtered = _filter_by_team_ids(result.teams, team_ids)
    elif top is not None:
        filtered = _filter_by_top(result.teams, top)
    else:
        if len(result.teams) > MAX_SELECTED_TEAMS:
            raise RatingProgressFilterError(
                f"Too many teams ({len(result.teams)}); "
                f"pass top or team_ids (max {MAX_SELECTED_TEAMS})")
        return result
    biggest_rise, biggest_fall = _pick_leaders(filtered)
    return replace(
        result,
        teams=filtered,
        biggest_rise=biggest_rise,
        biggest_fall=biggest_fall)


def _build_result(
        context: RatingProgressContext,
        metric: RatingMetric,
        *,
        target_league_id: int | None) -> RatingProgressResult:
    """Run timeline extraction and assemble the domain DTO."""
    teams = compute_team_rating_progress(
        matches=context.matches,
        target_league_id=target_league_id,
        target_season_id=context.season_id,
        participants=context.participants,
        metric=metric)
    biggest_rise, biggest_fall = _pick_leaders(teams)
    return RatingProgressResult(
        league_id=context.league_id,
        league_name=context.league_name,
        season_id=context.season_id,
        season_years=context.season_years,
        metric=metric,
        last_played_match_id=context.last_played_match_id,
        last_played_at=context.last_played_at,
        teams=teams,
        biggest_rise=biggest_rise,
        biggest_fall=biggest_fall)


def _resolve_metric(metric: str) -> RatingMetric:
    """Validate and narrow a metric string to ``RatingMetric``."""
    if metric not in SUPPORTED_METRICS:
        raise ValueError(f"Unsupported rating metric: {metric}")
    return cast(RatingMetric, metric)


def _ensure_football_league(context: RatingProgressContext) -> None:
    """Reject leagues that are not football."""
    if context.sport_id != FOOTBALL_SPORT_ID:
        raise NonFootballLeagueError(
            f"League {context.league_id} is not a football league")


def _pick_leaders(
        teams: list[TeamRatingProgress]
) -> tuple[TeamRatingProgress | None, TeamRatingProgress | None]:
    """Return biggest seasonal rise and fall by start-to-current change."""
    if not teams:
        return None, None
    # Remisy: niższe team_id wygrywa dla stabilnego wyboru lidera.
    biggest_rise = max(
        teams,
        key=lambda team: (team.change, -team.team_id))
    biggest_fall = min(
        teams,
        key=lambda team: (team.change, team.team_id))
    return biggest_rise, biggest_fall


def _filter_by_top(
        teams: list[TeamRatingProgress],
        top: int) -> list[TeamRatingProgress]:
    """Keep the first ``top`` teams by current rank."""
    if top < 1 or top > MAX_SELECTED_TEAMS:
        raise RatingProgressFilterError(
            f"top must be between 1 and {MAX_SELECTED_TEAMS}")
    # teams są już posortowane po current_rank rosnąco.
    return teams[:top]


def _filter_by_team_ids(
        teams: list[TeamRatingProgress],
        team_ids: list[int]) -> list[TeamRatingProgress]:
    """Keep requested participant teams, preserving rank order."""
    if not team_ids:
        raise RatingProgressFilterError("team_ids must not be empty")
    unique_ids = list(dict.fromkeys(team_ids))
    if len(unique_ids) > MAX_SELECTED_TEAMS:
        raise RatingProgressFilterError(
            f"At most {MAX_SELECTED_TEAMS} team ids are allowed")
    by_id = {team.team_id: team for team in teams}
    missing = [team_id for team_id in unique_ids if team_id not in by_id]
    if missing:
        raise RatingProgressFilterError(
            f"Unknown or inactive team ids: {missing}")
    selected = [by_id[team_id] for team_id in unique_ids]
    return sorted(selected, key=lambda team: team.current_rank)
