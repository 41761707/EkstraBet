"""Tests for season projection aggregation and ranking."""

from __future__ import annotations

import numpy as np
import pytest

from models.pipeline.simulation.aggregation import BaselineStanding
from models.pipeline.simulation.aggregation import aggregate_projection
from models.pipeline.simulation.aggregation import baseline_from_standings
from models.pipeline.simulation.aggregation import rank_teams


def test_rank_teams_uses_points_gd_and_team_id() -> None:
    team_ids = (10, 20, 30)
    points = np.asarray([6, 6, 3], dtype=int)
    gd = np.asarray([2, 4, 0], dtype=int)

    positions = rank_teams(team_ids, points, gd)

    # 20 ma lepsze GD przy remisie punktowym; 10 przed 30
    assert positions.tolist() == [2, 1, 3]


def test_rank_teams_breaks_ties_by_lower_team_id() -> None:
    team_ids = (5, 2, 9)
    points = np.asarray([3, 3, 3], dtype=int)
    gd = np.asarray([1, 1, 1], dtype=int)

    positions = rank_teams(team_ids, points, gd)

    assert positions.tolist() == [2, 1, 3]


def test_aggregate_projection_stats_and_probabilities() -> None:
    team_ids = (1, 2)
    # trial 0: team1 wygrywa tabelę; trial 1: remis punktów, GD rozstrzyga
    final_points = np.asarray([[6, 0], [3, 3]], dtype=float)
    final_gd = np.asarray([[4, -4], [1, -1]], dtype=float)
    baseline = [
        BaselineStanding(team_id=1, points=0, position=1),
        BaselineStanding(team_id=2, points=0, position=2)]

    projections = aggregate_projection(
        final_points, final_gd, team_ids, baseline)

    assert len(projections) == 2
    by_id = {row.team_id: row for row in projections}
    team1 = by_id[1]
    assert team1.current_points == 0
    assert team1.current_position == 1
    assert team1.expected_points == pytest.approx(4.5)
    assert team1.points_min == 3.0
    assert team1.points_max == 6.0
    assert team1.points_p50 == pytest.approx(4.5)
    assert team1.points_variance == pytest.approx(2.25)
    assert team1.points_stddev == pytest.approx(1.5)
    assert sum(team1.position_probabilities) == pytest.approx(1.0)
    assert team1.position_probabilities[0] == pytest.approx(1.0)
    assert team1.most_likely_position == 1
    team2 = by_id[2]
    assert sum(team2.position_probabilities) == pytest.approx(1.0)
    assert team2.position_probabilities[1] == pytest.approx(1.0)


def test_aggregate_projection_position_probabilities_sum_to_one() -> None:
    rng = np.random.default_rng(0)
    team_ids = (10, 20, 30, 40)
    final_points = rng.integers(0, 30, size=(50, 4))
    final_gd = rng.integers(-20, 20, size=(50, 4))
    baseline = baseline_from_standings(
        team_ids,
        np.zeros(4, dtype=int),
        np.zeros(4, dtype=int))

    projections = aggregate_projection(
        final_points, final_gd, team_ids, baseline)

    for row in projections:
        assert sum(row.position_probabilities) == pytest.approx(1.0)
        assert len(row.position_probabilities) == 4


def test_baseline_from_standings_positions() -> None:
    baseline = baseline_from_standings(
        (3, 1, 2),
        np.asarray([0, 6, 3], dtype=int),
        np.asarray([0, 2, 1], dtype=int))
    by_id = {row.team_id: row for row in baseline}
    assert by_id[1].position == 1
    assert by_id[1].points == 6
    assert by_id[2].position == 2
    assert by_id[3].position == 3
