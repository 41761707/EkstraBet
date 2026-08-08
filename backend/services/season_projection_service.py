"""Read-only season projection orchestration for the HTTP API.

Loads the latest SUCCEEDED cache entry, compares its fingerprint with the
current schedule snapshot, and never runs the Monte Carlo simulator.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from backend.repositories import league_repository
from backend.repositories import season_projection_repository as repository
from backend.repositories.season_projection_repository import (
    SeasonProjectionTeamRowRecord)
from models.pipeline.data.schedule_repository import (
    fetch_season_simulation_input)
from models.pipeline.simulation.config import FOOTBALL_SPORT_ID
from models.pipeline.simulation.config import SimulationMode

logger = logging.getLogger(__name__)


class SeasonProjectionError(Exception):
    """Base domain error for season projection reads."""


class NonFootballLeagueError(SeasonProjectionError):
    """Raised when projection is requested for a non-football league."""


class UnsupportedSeasonProjectionModeError(SeasonProjectionError, ValueError):
    """Raised when ``mode`` is not a known SimulationMode value."""


@dataclass(frozen=True)
class SeasonProjectionPayload:
    """API-ready season projection assembled from cache."""

    league_id: int
    season_id: int
    mode: SimulationMode
    generated_at: datetime
    model_name: str
    model_version: str
    n_trials: int
    fixed_matches: int
    simulated_matches: int
    is_stale: bool
    standings: list[SeasonProjectionTeamRowRecord]


def get_season_projection(
        league_id: int,
        season_id: int,
        mode: SimulationMode | str = SimulationMode.FROM_NOW
) -> SeasonProjectionPayload | None:
    """Return the latest succeeded projection or ``None`` when missing.

    Raises ``NonFootballLeagueError`` for a known non-football league.
    Raises ``UnsupportedSeasonProjectionModeError`` for an unsupported
    mode. Does not import or invoke the season simulator / TensorFlow.

    When the schedule fingerprint cannot be computed, the cached run is
    still returned with ``is_stale=True`` (freshness unknown).
    """
    resolved_mode = _resolve_mode(mode)
    _ensure_football_league(league_id)
    run = repository.fetch_latest_succeeded_run(
        league_id,
        season_id,
        resolved_mode.value)
    if run is None:
        return None
    team_rows = repository.fetch_team_rows_for_run(run.id)
    is_stale = _is_fingerprint_stale(
        league_id,
        season_id,
        resolved_mode,
        run.input_fingerprint)
    return SeasonProjectionPayload(
        league_id=run.league_id,
        season_id=run.season_id,
        mode=resolved_mode,
        generated_at=run.completed_at,
        model_name=run.model_name,
        model_version=run.model_version,
        n_trials=run.n_trials,
        fixed_matches=run.fixed_matches,
        simulated_matches=run.simulated_matches,
        is_stale=is_stale,
        standings=team_rows)


def _resolve_mode(mode: SimulationMode | str) -> SimulationMode:
    if isinstance(mode, SimulationMode):
        return mode
    try:
        return SimulationMode(str(mode))
    except ValueError as exc:
        raise UnsupportedSeasonProjectionModeError(
            f"Unsupported season projection mode: {mode!r}") from exc


def _ensure_football_league(league_id: int) -> None:
    frame = league_repository.fetch_league_by_id(league_id)
    if frame.empty:
        # brak ligi -> 404 na poziomie routera (jak brak runu)
        return
    sport_id = frame.iloc[0]["sport_id"]
    if sport_id is None or int(sport_id) != FOOTBALL_SPORT_ID:
        raise NonFootballLeagueError(
            f"League {league_id} is not a football league")


def _is_fingerprint_stale(
        league_id: int,
        season_id: int,
        mode: SimulationMode,
        cached_fingerprint: str) -> bool:
    try:
        current = _current_input_fingerprint(league_id, season_id, mode)
    except Exception as exc:
        # poprawny request + gotowy cache: nie spadamy do 422/500
        logger.warning(
            "Season projection freshness check failed for "
            "league_id=%s season_id=%s mode=%s: %s",
            league_id,
            season_id,
            mode.value,
            exc)
        return True
    return current != cached_fingerprint


def _current_input_fingerprint(
        league_id: int,
        season_id: int,
        mode: SimulationMode) -> str:
    # ten sam kanoniczny fingerprint co przy zapisie runu (SZP-81)
    simulation_input = fetch_season_simulation_input(
        league_id,
        season_id,
        mode)
    return simulation_input.input_fingerprint
