"""Point adjustments applied to season simulation standings."""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pytest

from backend.repositories.football_point_adjustments_repository import (
    PointAdjustment)
from models.pipeline.simulation.aggregation import apply_point_adjustments
from models.pipeline.simulation.config import SimulationMode
from models.pipeline.simulation.season_simulator import (
    DynamicSeasonSimulator)
from models.tests.test_season_simulator import _config
from models.tests.test_season_simulator import _mock_predictor
from models.tests.test_season_simulator import _two_team_input
from models.tests.test_season_simulator import _warm_state


_FETCH = (
    "backend.repositories.football_point_adjustments_repository"
    ".fetch_point_adjustments")


def test_apply_point_adjustments_adds_delta_for_one_team() -> None:
    points = np.asarray([20, 18, 10], dtype=int)
    adjusted = apply_point_adjustments(
        points, (73, 10, 20), {73: -4, 99: 7})

    assert adjusted.tolist() == [16, 18, 10]
    assert points.tolist() == [20, 18, 10]
    assert adjusted.shape == points.shape
    assert adjusted.dtype == points.dtype


def test_apply_point_adjustments_rejects_mismatched_length() -> None:
    points = np.asarray([1, 2], dtype=int)
    with pytest.raises(ValueError, match="points length must match"):
        apply_point_adjustments(points, (1,), {})


def test_penalty_lowers_current_and_expected_points() -> None:
    mode = SimulationMode.FROM_NOW
    plain = _run(mode, fix_first=True)
    penalized = _run(mode, fix_first=True, adjustments={10: -4})
    plain_rows = _by_team(plain)
    penalized_rows = _by_team(penalized)

    assert plain_rows[10].current_points == 3
    assert penalized_rows[10].current_points == -1
    assert plain_rows[10].current_position == 1
    assert penalized_rows[10].current_position == 2
    point_gap = (
        plain_rows[10].expected_points
        - penalized_rows[10].expected_points)
    assert point_gap == pytest.approx(4.0)
    assert plain_rows[20].current_points == 0
    assert penalized_rows[20].current_points == 0
    assert plain_rows[20].expected_points == pytest.approx(
        penalized_rows[20].expected_points)


def test_empty_adjustments_match_a_run_without_the_argument() -> None:
    mode = SimulationMode.FROM_SEASON_START
    omitted = _run(mode)
    empty = _run(mode, adjustments={})
    assert _signature(omitted) == _signature(empty)


def test_simulation_input_without_adjustments_skips_database() -> None:
    with patch(_FETCH) as fetch:
        _run(SimulationMode.FROM_SEASON_START)
    fetch.assert_not_called()


def test_omitted_adjustments_load_deltas_from_repository() -> None:
    loaded = _two_team_input(SimulationMode.FROM_NOW, fix_first=True)

    def loader(league_id: int, season_id: int, mode: SimulationMode):
        assert (league_id, season_id, mode) == (
            1, 13, SimulationMode.FROM_NOW)
        return loaded

    adjustment = PointAdjustment(
        team_id=10,
        points_delta=-4,
        reason="Decyzja związku")
    simulator = DynamicSeasonSimulator(
        _mock_predictor(), input_loader=loader)
    with patch(_FETCH, return_value={10: adjustment}) as fetch:
        result = simulator.run(
            _config(SimulationMode.FROM_NOW),
            base_state=_warm_state([10, 20]))
    fetch.assert_called_once_with(1, 13)
    rows = _by_team(result)
    assert rows[10].current_points == -1
    assert rows[20].current_points == 0


def test_explicit_dict_skips_database_without_simulation_input() -> None:
    loaded = _two_team_input(SimulationMode.FROM_NOW, fix_first=True)

    def loader(
            _league_id: int,
            _season_id: int,
            _mode: SimulationMode):
        return loaded

    simulator = DynamicSeasonSimulator(
        _mock_predictor(), input_loader=loader)
    with patch(_FETCH) as fetch:
        result = simulator.run(
            _config(SimulationMode.FROM_NOW),
            point_adjustments={10: -4},
            base_state=_warm_state([10, 20]))
    fetch.assert_not_called()
    assert _by_team(result)[10].current_points == -1


def _run(
        mode: SimulationMode,
        *,
        fix_first: bool = False,
        adjustments: dict[int, int] | None = None):
    kwargs: dict = {
        "simulation_input": _two_team_input(mode, fix_first=fix_first),
        "base_state": _warm_state([10, 20])}
    if adjustments is not None:
        kwargs["point_adjustments"] = adjustments
    return DynamicSeasonSimulator(_mock_predictor()).run(
        _config(mode, seed=42), **kwargs)


def _by_team(result):
    return {row.team_id: row for row in result.projections}


def _signature(result):
    return [
        (
            row.team_id,
            row.current_points,
            row.expected_points,
            row.current_position,
            tuple(row.position_probabilities))
        for row in sorted(
            result.projections, key=lambda row: row.team_id)]
