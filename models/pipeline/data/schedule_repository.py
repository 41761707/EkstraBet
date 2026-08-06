"""Read season schedule rows and build simulation input."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

import pandas as pd

from backend.database import get_db_connection
from models.pipeline.simulation.config import FOOTBALL_SPORT_ID
from models.pipeline.simulation.config import FixtureValidation
from models.pipeline.simulation.config import MAX_LEAGUE_ROUND
from models.pipeline.simulation.config import ResolvedFixture
from models.pipeline.simulation.config import ScheduleRow
from models.pipeline.simulation.config import SeasonSimulationInput
from models.pipeline.simulation.config import SimulationMode

logger = logging.getLogger(__name__)

_SCHEDULE_SELECT = """
    SELECT
        s.id,
        s.match_id,
        s.league AS league_id,
        s.season AS season_id,
        s.home_team AS home_team_id,
        s.away_team AS away_team_id,
        s.round
    FROM schedule s
    WHERE s.league = %s
      AND s.season = %s
      AND s.round < %s
    ORDER BY s.round, s.id
"""

_SCHEDULE_WITH_RESULTS_SELECT = """
    SELECT
        s.id,
        s.match_id,
        s.league AS league_id,
        s.season AS season_id,
        s.home_team AS home_team_id,
        s.away_team AS away_team_id,
        s.round,
        m.result AS match_result,
        m.home_team_goals AS home_goals,
        m.away_team_goals AS away_goals
    FROM schedule s
    LEFT JOIN matches m ON m.id = s.match_id
    WHERE s.league = %s
      AND s.season = %s
      AND s.round < %s
    ORDER BY s.round, s.id
"""

_LEAGUE_SPORT_SELECT = """
    SELECT l.sport_id
    FROM leagues l
    WHERE l.id = %s
"""

# roster niezależny od schedule — ten sam wzorzec co standings
_SEASON_ROSTER_SELECT = """
    SELECT team_id
    FROM (
        SELECT DISTINCT m.home_team AS team_id
        FROM matches m
        WHERE m.league = %s
          AND m.season = %s
          AND m.round < %s
        UNION
        SELECT DISTINCT m.away_team AS team_id
        FROM matches m
        WHERE m.league = %s
          AND m.season = %s
          AND m.round < %s
    ) AS season_teams
    ORDER BY team_id
"""


def fetch_season_simulation_input(
        league_id: int,
        season_id: int,
        mode: SimulationMode) -> SeasonSimulationInput:
    """Load schedule fixtures for a league season and optional results.

    Fixture list always comes from ``schedule``. Season roster comes from
    distinct teams in ``matches`` for the same league/season. Finished
    scores are joined from ``matches`` only in ``FROM_NOW`` mode.
    """
    _assert_football_league(league_id)
    team_ids = _fetch_season_roster(league_id, season_id)
    if mode is SimulationMode.FROM_NOW:
        frame = _read_schedule_with_results(league_id, season_id)
    else:
        frame = _read_schedule_only(league_id, season_id)
    fixtures = _frame_to_fixtures(frame, mode)
    fingerprint = compute_input_fingerprint(fixtures, mode)
    logger.info(
        "Loaded season simulation input league=%s season=%s mode=%s "
        "roster_teams=%s fixtures=%s fixed=%s",
        league_id,
        season_id,
        mode.value,
        len(team_ids),
        len(fixtures),
        sum(1 for item in fixtures if item.is_fixed))
    return SeasonSimulationInput(
        league_id=league_id,
        season_id=season_id,
        mode=mode,
        team_ids=team_ids,
        fixtures=fixtures,
        input_fingerprint=fingerprint)


def validate_fixture_completeness(
        simulation_input: SeasonSimulationInput) -> FixtureValidation:
    """Validate a double round-robin against the independent season roster."""
    team_ids = simulation_input.team_ids
    team_count = len(team_ids)
    actual = len(simulation_input.fixtures)
    fixture_teams = _team_ids_from_fixtures(simulation_input.fixtures)
    roster = set(team_ids)
    missing_team_ids = tuple(sorted(roster - fixture_teams))
    unexpected_team_ids = tuple(sorted(fixture_teams - roster))
    if team_count < 2:
        return FixtureValidation(
            is_valid=False,
            team_count=team_count,
            expected_fixture_count=0,
            actual_fixture_count=actual,
            missing_team_ids=missing_team_ids,
            unexpected_team_ids=unexpected_team_ids,
            error_message=(
                "season roster requires at least 2 teams, "
                f"found {team_count}"))
    expected = team_count * (team_count - 1)
    pair_counts: dict[tuple[int, int], int] = {}
    for fixture in simulation_input.fixtures:
        pair = (
            fixture.schedule.home_team_id,
            fixture.schedule.away_team_id)
        pair_counts[pair] = pair_counts.get(pair, 0) + 1
    expected_pairs = {
        (home, away)
        for home in team_ids
        for away in team_ids
        if home != away}
    missing = tuple(sorted(expected_pairs - pair_counts.keys()))
    duplicates = tuple(sorted(
        pair for pair, count in pair_counts.items() if count > 1))
    goals_error = _fixed_goals_error(simulation_input.fixtures)
    if goals_error is not None:
        return FixtureValidation(
            is_valid=False,
            team_count=team_count,
            expected_fixture_count=expected,
            actual_fixture_count=actual,
            missing_pairs=missing,
            duplicate_pairs=duplicates,
            missing_team_ids=missing_team_ids,
            unexpected_team_ids=unexpected_team_ids,
            error_message=goals_error)
    roster_error = _roster_mismatch_error(
        missing_team_ids=missing_team_ids,
        unexpected_team_ids=unexpected_team_ids)
    if roster_error is not None:
        return FixtureValidation(
            is_valid=False,
            team_count=team_count,
            expected_fixture_count=expected,
            actual_fixture_count=actual,
            missing_pairs=missing,
            duplicate_pairs=duplicates,
            missing_team_ids=missing_team_ids,
            unexpected_team_ids=unexpected_team_ids,
            error_message=roster_error)
    if actual != expected or missing or duplicates:
        return FixtureValidation(
            is_valid=False,
            team_count=team_count,
            expected_fixture_count=expected,
            actual_fixture_count=actual,
            missing_pairs=missing,
            duplicate_pairs=duplicates,
            missing_team_ids=missing_team_ids,
            unexpected_team_ids=unexpected_team_ids,
            error_message=_completeness_error(
                expected=expected,
                actual=actual,
                missing=missing,
                duplicates=duplicates))
    return FixtureValidation(
        is_valid=True,
        team_count=team_count,
        expected_fixture_count=expected,
        actual_fixture_count=actual)


def compute_input_fingerprint(
        fixtures: list[ResolvedFixture],
        mode: SimulationMode) -> str:
    """Return SHA-256 of the canonical schedule (+ results in FROM_NOW)."""
    lines = [
        _fingerprint_line(fixture, mode)
        for fixture in fixtures]
    payload = "\n".join(lines).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _assert_football_league(league_id: int) -> None:
    with get_db_connection() as connection:
        frame = pd.read_sql(
            _LEAGUE_SPORT_SELECT,
            connection,
            params=(league_id,))
    if frame.empty:
        raise ValueError(f"league_id={league_id} was not found")
    sport_id = int(frame.iloc[0]["sport_id"])
    if sport_id != FOOTBALL_SPORT_ID:
        raise ValueError(
            "season simulation supports football only "
            f"(league_id={league_id}, sport_id={sport_id})")


def _fetch_season_roster(league_id: int, season_id: int) -> list[int]:
    with get_db_connection() as connection:
        frame = pd.read_sql(
            _SEASON_ROSTER_SELECT,
            connection,
            params=(
                league_id,
                season_id,
                MAX_LEAGUE_ROUND,
                league_id,
                season_id,
                MAX_LEAGUE_ROUND))
    if frame.empty:
        return []
    return [int(value) for value in frame["team_id"].tolist()]


def _read_schedule_only(league_id: int, season_id: int) -> pd.DataFrame:
    with get_db_connection() as connection:
        return pd.read_sql(
            _SCHEDULE_SELECT,
            connection,
            params=(league_id, season_id, MAX_LEAGUE_ROUND))


def _read_schedule_with_results(
        league_id: int,
        season_id: int) -> pd.DataFrame:
    with get_db_connection() as connection:
        return pd.read_sql(
            _SCHEDULE_WITH_RESULTS_SELECT,
            connection,
            params=(league_id, season_id, MAX_LEAGUE_ROUND))


def _frame_to_fixtures(
        frame: pd.DataFrame,
        mode: SimulationMode) -> list[ResolvedFixture]:
    fixtures: list[ResolvedFixture] = []
    for row in frame.to_dict(orient="records"):
        fixtures.append(_row_to_fixture(row, mode))
    return fixtures


def _row_to_fixture(
        row: dict[str, Any],
        mode: SimulationMode) -> ResolvedFixture:
    schedule = ScheduleRow(
        id=int(row["id"]),
        match_id=_optional_int(row.get("match_id")),
        league_id=int(row["league_id"]),
        season_id=int(row["season_id"]),
        home_team_id=int(row["home_team_id"]),
        away_team_id=int(row["away_team_id"]),
        round=int(row["round"]))
    if mode is SimulationMode.FROM_SEASON_START:
        return ResolvedFixture(schedule=schedule, is_fixed=False)
    result = _optional_str(row.get("match_result"))
    home_goals = _optional_int(row.get("home_goals"))
    away_goals = _optional_int(row.get("away_goals"))
    is_fixed = _is_fixed_result(schedule.match_id, result)
    return ResolvedFixture(
        schedule=schedule,
        result=result,
        home_goals=home_goals,
        away_goals=away_goals,
        is_fixed=is_fixed)


def _is_fixed_result(match_id: int | None, result: str | None) -> bool:
    if match_id is None or result is None:
        return False
    return result != "0"


def _team_ids_from_fixtures(
        fixtures: list[ResolvedFixture]) -> set[int]:
    team_ids: set[int] = set()
    for fixture in fixtures:
        team_ids.add(fixture.schedule.home_team_id)
        team_ids.add(fixture.schedule.away_team_id)
    return team_ids


def _fingerprint_line(
        fixture: ResolvedFixture,
        mode: SimulationMode) -> str:
    schedule = fixture.schedule
    match_token = (
        "" if schedule.match_id is None else str(schedule.match_id))
    base = (
        f"{schedule.home_team_id}:{schedule.away_team_id}:"
        f"{schedule.round}:{match_token}")
    if mode is SimulationMode.FROM_SEASON_START:
        return base
    if schedule.match_id is None:
        return base
    # w FROM_NOW fingerprint obejmuje wynik podpiętego meczu, bez game_date
    result_token = "" if fixture.result is None else fixture.result
    home_token = (
        "" if fixture.home_goals is None else str(fixture.home_goals))
    away_token = (
        "" if fixture.away_goals is None else str(fixture.away_goals))
    return (
        f"{base}|r={result_token};hg={home_token};ag={away_token}")


def _fixed_goals_error(
        fixtures: list[ResolvedFixture]) -> str | None:
    for fixture in fixtures:
        if not fixture.is_fixed:
            continue
        if fixture.home_goals is None or fixture.away_goals is None:
            match_id = fixture.schedule.match_id
            return (
                "fixed match is missing goals "
                f"(schedule_id={fixture.schedule.id}, "
                f"match_id={match_id})")
    return None


def _roster_mismatch_error(
        *,
        missing_team_ids: tuple[int, ...],
        unexpected_team_ids: tuple[int, ...]) -> str | None:
    if not missing_team_ids and not unexpected_team_ids:
        return None
    parts: list[str] = []
    if missing_team_ids:
        parts.append(
            "schedule is missing roster teams "
            f"{list(missing_team_ids)}")
    if unexpected_team_ids:
        parts.append(
            "schedule contains teams outside season roster "
            f"{list(unexpected_team_ids)}")
    return "; ".join(parts)


def _completeness_error(
        *,
        expected: int,
        actual: int,
        missing: tuple[tuple[int, int], ...],
        duplicates: tuple[tuple[int, int], ...]) -> str:
    parts = [
        f"incomplete schedule: expected {expected} fixtures, "
        f"found {actual}"]
    if missing:
        parts.append(f"missing_pairs={len(missing)}")
    if duplicates:
        parts.append(f"duplicate_pairs={len(duplicates)}")
    return "; ".join(parts)


def _optional_int(value: Any) -> int | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if pd.isna(value):
        return None
    return int(value)


def _optional_str(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if pd.isna(value):
        return None
    text = str(value)
    return text if text else None
