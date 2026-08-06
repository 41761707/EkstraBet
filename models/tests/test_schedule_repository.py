"""Tests for schedule simulation input, completeness and fingerprint."""

from __future__ import annotations

from unittest.mock import MagicMock
from unittest.mock import patch

import pandas as pd
import pytest

from models.pipeline.data.schedule_repository import (
    compute_input_fingerprint)
from models.pipeline.data.schedule_repository import (
    fetch_season_simulation_input)
from models.pipeline.data.schedule_repository import (
    validate_fixture_completeness)
from models.pipeline.simulation.config import ResolvedFixture
from models.pipeline.simulation.config import ScheduleRow
from models.pipeline.simulation.config import SeasonSimulationConfig
from models.pipeline.simulation.config import SeasonSimulationInput
from models.pipeline.simulation.config import SimulationMode


def _schedule_row(
        row_id: int,
        home: int,
        away: int,
        round_no: int,
        match_id: int | None = None,
        league_id: int = 1,
        season_id: int = 13) -> ScheduleRow:
    return ScheduleRow(
        id=row_id,
        match_id=match_id,
        league_id=league_id,
        season_id=season_id,
        home_team_id=home,
        away_team_id=away,
        round=round_no)


def _fixture(
        row_id: int,
        home: int,
        away: int,
        round_no: int,
        *,
        match_id: int | None = None,
        result: str | None = None,
        home_goals: int | None = None,
        away_goals: int | None = None,
        is_fixed: bool = False) -> ResolvedFixture:
    return ResolvedFixture(
        schedule=_schedule_row(row_id, home, away, round_no, match_id),
        result=result,
        home_goals=home_goals,
        away_goals=away_goals,
        is_fixed=is_fixed)


def _complete_three_team_fixtures(
        *,
        with_results: bool) -> list[ResolvedFixture]:
    # kompletny dwurundowy terminarz dla N=3 -> 6 meczów
    pairs = [
        (1, 2),
        (1, 3),
        (2, 3),
        (2, 1),
        (3, 1),
        (3, 2)]
    fixtures: list[ResolvedFixture] = []
    for index, (home, away) in enumerate(pairs, start=1):
        round_no = 1 if index <= 3 else 2
        match_id = 100 + index if with_results else None
        if with_results and index == 1:
            fixtures.append(_fixture(
                index, home, away, round_no,
                match_id=match_id,
                result="1",
                home_goals=2,
                away_goals=1,
                is_fixed=True))
        elif with_results:
            fixtures.append(_fixture(
                index, home, away, round_no,
                match_id=match_id,
                result="0",
                home_goals=None,
                away_goals=None,
                is_fixed=False))
        else:
            fixtures.append(_fixture(
                index, home, away, round_no, match_id=match_id))
    return fixtures


def _input_from_fixtures(
        fixtures: list[ResolvedFixture],
        mode: SimulationMode,
        team_ids: list[int] | None = None) -> SeasonSimulationInput:
    if team_ids is None:
        team_ids = sorted({
            item.schedule.home_team_id
            for item in fixtures} | {
            item.schedule.away_team_id
            for item in fixtures})
    return SeasonSimulationInput(
        league_id=1,
        season_id=13,
        mode=mode,
        team_ids=team_ids,
        fixtures=fixtures,
        input_fingerprint=compute_input_fingerprint(fixtures, mode))


def test_season_simulation_config_rejects_non_football() -> None:
    with pytest.raises(ValueError, match="football only"):
        SeasonSimulationConfig(
            league_id=1,
            season_id=13,
            mode=SimulationMode.FROM_NOW,
            sport_id=2)


def test_season_simulation_config_rejects_trial_bounds() -> None:
    with pytest.raises(ValueError, match="n_trials"):
        SeasonSimulationConfig(
            league_id=1,
            season_id=13,
            mode=SimulationMode.FROM_NOW,
            n_trials=50)


def test_validate_complete_schedule() -> None:
    fixtures = _complete_three_team_fixtures(with_results=False)
    validation = validate_fixture_completeness(
        _input_from_fixtures(fixtures, SimulationMode.FROM_SEASON_START))
    assert validation.is_valid is True
    assert validation.expected_fixture_count == 6
    assert validation.actual_fixture_count == 6
    assert validation.error_message is None


def test_validate_incomplete_schedule() -> None:
    fixtures = _complete_three_team_fixtures(with_results=False)[:-1]
    validation = validate_fixture_completeness(
        _input_from_fixtures(fixtures, SimulationMode.FROM_SEASON_START))
    assert validation.is_valid is False
    assert validation.expected_fixture_count == 6
    assert validation.actual_fixture_count == 5
    assert validation.missing_pairs
    assert validation.error_message is not None
    assert "incomplete schedule" in validation.error_message


def test_validate_rejects_fixed_match_without_goals() -> None:
    fixtures = _complete_three_team_fixtures(with_results=True)
    broken = list(fixtures)
    broken[0] = _fixture(
        1, 1, 2, 1,
        match_id=101,
        result="1",
        home_goals=None,
        away_goals=1,
        is_fixed=True)
    validation = validate_fixture_completeness(
        _input_from_fixtures(broken, SimulationMode.FROM_NOW))
    assert validation.is_valid is False
    assert "missing goals" in (validation.error_message or "")


def test_validate_rejects_when_roster_team_missing_from_schedule() -> None:
    # pełny graf dla N-1 nie może przejść, gdy roster ma N drużyn
    fixtures = [
        _fixture(1, 1, 2, 1),
        _fixture(2, 2, 1, 2)]
    validation = validate_fixture_completeness(
        _input_from_fixtures(
            fixtures,
            SimulationMode.FROM_SEASON_START,
            team_ids=[1, 2, 3]))
    assert validation.is_valid is False
    assert validation.team_count == 3
    assert validation.expected_fixture_count == 6
    assert validation.missing_team_ids == (3,)
    assert "missing roster teams" in (validation.error_message or "")


def test_validate_rejects_schedule_teams_outside_roster() -> None:
    fixtures = _complete_three_team_fixtures(with_results=False)
    validation = validate_fixture_completeness(
        _input_from_fixtures(
            fixtures,
            SimulationMode.FROM_SEASON_START,
            team_ids=[1, 2]))
    assert validation.is_valid is False
    assert validation.unexpected_team_ids == (3,)
    assert "outside season roster" in (validation.error_message or "")


def test_fingerprint_changes_when_result_corrected() -> None:
    fixtures = _complete_three_team_fixtures(with_results=True)
    original = compute_input_fingerprint(
        fixtures, SimulationMode.FROM_NOW)
    corrected = list(fixtures)
    corrected[0] = _fixture(
        1, 1, 2, 1,
        match_id=101,
        result="2",
        home_goals=1,
        away_goals=2,
        is_fixed=True)
    updated = compute_input_fingerprint(
        corrected, SimulationMode.FROM_NOW)
    assert original != updated


def test_fingerprint_changes_when_schedule_row_changes() -> None:
    fixtures = _complete_three_team_fixtures(with_results=False)
    original = compute_input_fingerprint(
        fixtures, SimulationMode.FROM_SEASON_START)
    altered = list(fixtures)
    altered[0] = _fixture(1, 1, 2, 3)
    updated = compute_input_fingerprint(
        altered, SimulationMode.FROM_SEASON_START)
    assert original != updated


def test_fingerprint_ignores_game_date_notionally() -> None:
    # game_date nie wchodzi do kanonicznej linii fingerprintu
    fixtures = _complete_three_team_fixtures(with_results=True)
    first = compute_input_fingerprint(fixtures, SimulationMode.FROM_NOW)
    second = compute_input_fingerprint(fixtures, SimulationMode.FROM_NOW)
    assert first == second
    line = (
        f"{fixtures[0].schedule.home_team_id}:"
        f"{fixtures[0].schedule.away_team_id}:"
        f"{fixtures[0].schedule.round}:"
        f"{fixtures[0].schedule.match_id}"
        f"|r={fixtures[0].result};"
        f"hg={fixtures[0].home_goals};"
        f"ag={fixtures[0].away_goals}")
    assert "game_date" not in line


def test_from_season_start_fingerprint_omits_results() -> None:
    with_results = _complete_three_team_fixtures(with_results=True)
    without_results = [
        ResolvedFixture(schedule=item.schedule, is_fixed=False)
        for item in with_results]
    left = compute_input_fingerprint(
        with_results, SimulationMode.FROM_SEASON_START)
    right = compute_input_fingerprint(
        without_results, SimulationMode.FROM_SEASON_START)
    assert left == right


def _mock_db_frames(
        schedule_frame: pd.DataFrame,
        sport_id: int = 1,
        roster_team_ids: list[int] | None = None) -> tuple:
    league_frame = pd.DataFrame({"sport_id": [sport_id]})
    if roster_team_ids is None:
        if schedule_frame.empty:
            roster_team_ids = []
        else:
            roster_team_ids = sorted({
                *schedule_frame["home_team_id"].tolist(),
                *schedule_frame["away_team_id"].tolist()})
    roster_frame = pd.DataFrame({"team_id": roster_team_ids})
    connection = MagicMock()
    context = MagicMock()
    context.__enter__.return_value = connection
    context.__exit__.return_value = False

    def _read_sql(query: str, _conn: object, params: tuple = ()) -> pd.DataFrame:
        if "FROM leagues" in query:
            return league_frame
        if "season_teams" in query:
            return roster_frame
        return schedule_frame

    return context, _read_sql


def test_fetch_from_now_joins_results_and_marks_fixed() -> None:
    schedule_frame = pd.DataFrame([
        {
            "id": 1,
            "match_id": 10,
            "league_id": 1,
            "season_id": 13,
            "home_team_id": 1,
            "away_team_id": 2,
            "round": 1,
            "match_result": "1",
            "home_goals": 2,
            "away_goals": 0
        },
        {
            "id": 2,
            "match_id": None,
            "league_id": 1,
            "season_id": 13,
            "home_team_id": 2,
            "away_team_id": 1,
            "round": 2,
            "match_result": None,
            "home_goals": None,
            "away_goals": None
        }
    ])
    context, read_sql = _mock_db_frames(schedule_frame)
    with patch(
            "models.pipeline.data.schedule_repository.get_db_connection",
            return_value=context), patch(
            "models.pipeline.data.schedule_repository.pd.read_sql",
            side_effect=read_sql):
        loaded = fetch_season_simulation_input(
            1, 13, SimulationMode.FROM_NOW)
    assert len(loaded.fixtures) == 2
    assert loaded.fixtures[0].is_fixed is True
    assert loaded.fixtures[0].home_goals == 2
    assert loaded.fixtures[1].is_fixed is False
    assert loaded.team_ids == [1, 2]
    assert len(loaded.input_fingerprint) == 64


def test_fetch_uses_independent_season_roster() -> None:
    schedule_frame = pd.DataFrame([
        {
            "id": 1,
            "match_id": None,
            "league_id": 1,
            "season_id": 13,
            "home_team_id": 1,
            "away_team_id": 2,
            "round": 1
        }
    ])
    context, read_sql = _mock_db_frames(
        schedule_frame, roster_team_ids=[1, 2, 3])
    with patch(
            "models.pipeline.data.schedule_repository.get_db_connection",
            return_value=context), patch(
            "models.pipeline.data.schedule_repository.pd.read_sql",
            side_effect=read_sql):
        loaded = fetch_season_simulation_input(
            1, 13, SimulationMode.FROM_SEASON_START)
    # roster z matches, nie z samego schedule
    assert loaded.team_ids == [1, 2, 3]
    assert len(loaded.fixtures) == 1


def test_fetch_from_season_start_ignores_match_results() -> None:
    schedule_frame = pd.DataFrame([
        {
            "id": 1,
            "match_id": 10,
            "league_id": 1,
            "season_id": 13,
            "home_team_id": 1,
            "away_team_id": 2,
            "round": 1
        },
        {
            "id": 2,
            "match_id": 11,
            "league_id": 1,
            "season_id": 13,
            "home_team_id": 2,
            "away_team_id": 1,
            "round": 2
        }
    ])
    context, read_sql = _mock_db_frames(schedule_frame)
    queries: list[str] = []

    def _tracking_read(
            query: str,
            _conn: object,
            params: tuple = ()) -> pd.DataFrame:
        queries.append(query)
        return read_sql(query, _conn, params)

    with patch(
            "models.pipeline.data.schedule_repository.get_db_connection",
            return_value=context), patch(
            "models.pipeline.data.schedule_repository.pd.read_sql",
            side_effect=_tracking_read):
        loaded = fetch_season_simulation_input(
            1, 13, SimulationMode.FROM_SEASON_START)
    assert all(item.is_fixed is False for item in loaded.fixtures)
    assert all(item.result is None for item in loaded.fixtures)
    schedule_queries = [q for q in queries if "FROM schedule" in q]
    assert schedule_queries
    assert all("LEFT JOIN matches" not in q for q in schedule_queries)


def test_fetch_filters_round_below_900() -> None:
    schedule_frame = pd.DataFrame([
        {
            "id": 1,
            "match_id": None,
            "league_id": 1,
            "season_id": 13,
            "home_team_id": 1,
            "away_team_id": 2,
            "round": 1
        }
    ])
    context, read_sql = _mock_db_frames(schedule_frame)
    captured_params: list[tuple] = []

    def _tracking_read(
            query: str,
            _conn: object,
            params: tuple = ()) -> pd.DataFrame:
        captured_params.append(params)
        return read_sql(query, _conn, params)

    with patch(
            "models.pipeline.data.schedule_repository.get_db_connection",
            return_value=context), patch(
            "models.pipeline.data.schedule_repository.pd.read_sql",
            side_effect=_tracking_read):
        fetch_season_simulation_input(
            1, 13, SimulationMode.FROM_SEASON_START)
    assert any(params[-1] == 900 for params in captured_params if params)


def test_fetch_rejects_non_football_league() -> None:
    context, read_sql = _mock_db_frames(
        pd.DataFrame(), sport_id=2)
    with patch(
            "models.pipeline.data.schedule_repository.get_db_connection",
            return_value=context), patch(
            "models.pipeline.data.schedule_repository.pd.read_sql",
            side_effect=read_sql):
        with pytest.raises(ValueError, match="football only"):
            fetch_season_simulation_input(
                1, 13, SimulationMode.FROM_NOW)
