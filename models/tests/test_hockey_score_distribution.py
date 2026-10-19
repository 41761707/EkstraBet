"""Score-grid tests for NHL markets, including overtime."""

from __future__ import annotations

import math

import numpy as np
import pytest

from models.pipeline.persistence.prediction_writer import (
    map_hockey_chart_to_rows)
from models.pipeline.prediction.hockey_markets import HOCKEY_MARKET_FAMILIES
from models.pipeline.prediction.hockey_markets import HOCKEY_MARKET_KEYS
from models.pipeline.prediction.hockey_markets import HockeyScoreDistribution
from models.pipeline.prediction.hockey_markets import build_score_distribution
from models.pipeline.prediction.hockey_markets import derive_hockey_markets
from models.pipeline.prediction.hockey_markets import derive_hockey_score_chart
from models.pipeline.prediction.hockey_markets import exact_score_event_id
from models.pipeline.prediction.hockey_markets import select_hockey_finals


COMPLEMENTARY_PAIRS = (
    ("ml_home", "ml_away"),
    ("over_55", "under_55"),
    ("over_65", "under_65"),
    ("pl_home_minus_15", "pl_away_plus_15"),
    ("pl_away_minus_15", "pl_home_plus_15"),
    ("home_over_25", "home_under_25"),
    ("home_over_35", "home_under_35"),
    ("away_over_25", "away_under_25"),
    ("away_over_35", "away_under_35"))


def _truncated_poisson(rate: float, max_goals: int) -> np.ndarray:
    goals = np.arange(max_goals + 1, dtype=float)
    log_factorial = np.zeros(max_goals + 1, dtype=float)
    log_factorial[1:] = np.cumsum(np.log(goals[1:]))
    return np.exp(-rate + goals * math.log(rate) - log_factorial)


def test_matrices_sum_to_one_and_cover_zero_through_twelve() -> None:
    distribution = build_score_distribution(3.1, 2.8, 1.25, 0.54)

    assert distribution.regulation_matrix.shape == (13, 13)
    assert distribution.final_matrix.shape == (13, 13)
    assert np.isclose(distribution.regulation_matrix.sum(), 1.0)
    assert np.isclose(distribution.final_matrix.sum(), 1.0)
    assert np.all(distribution.regulation_matrix >= 0.0)
    assert np.all(distribution.final_matrix >= 0.0)
    assert np.allclose(np.diag(distribution.final_matrix), 0.0)


def test_tie_inflation_of_one_is_independent_poisson() -> None:
    distribution = build_score_distribution(2.2, 1.8, 1.0, 0.51, max_goals=8)
    home = _truncated_poisson(2.2, 8)
    away = _truncated_poisson(1.8, 8)
    expected = np.outer(home, away)
    expected /= expected.sum()

    assert np.allclose(distribution.regulation_matrix, expected)


def test_tie_inflation_raises_the_diagonal() -> None:
    plain = build_score_distribution(2.6, 2.4, 1.0, 0.5)
    inflated = build_score_distribution(2.6, 2.4, 1.45, 0.5)

    assert np.trace(inflated.regulation_matrix) > np.trace(
        plain.regulation_matrix)


def test_overtime_moves_ties_using_p_ot_home() -> None:
    distribution = build_score_distribution(
        2.5, 2.5, 1.2, 0.6, max_goals=6)
    expected = distribution.regulation_matrix.copy()
    ties = np.diag(expected).copy()
    np.fill_diagonal(expected, 0.0)
    movable = np.arange(expected.shape[0] - 1)
    expected[movable + 1, movable] += ties[movable] * 0.6
    expected[movable, movable + 1] += ties[movable] * 0.4
    last = expected.shape[0] - 1
    expected[last, last - 1] += ties[last] * 0.6
    expected[last - 1, last] += ties[last] * 0.4

    assert np.allclose(distribution.final_matrix, expected)


def test_market_pairs_sum_to_100_percent() -> None:
    distribution = build_score_distribution(3.0, 2.7, 1.3, 0.53)
    markets = derive_hockey_markets(distribution)

    assert list(markets) == list(HOCKEY_MARKET_KEYS)
    assert markets["ml_home"] + markets["ml_away"] == pytest.approx(100.0)
    for left, right in COMPLEMENTARY_PAIRS:
        assert markets[left] + markets[right] == pytest.approx(100.0)
    assert 0.0 <= markets["ml_home"] <= 100.0


def test_home_overtime_edge_lifts_moneyline() -> None:
    neutral = build_score_distribution(2.4, 2.4, 1.2, 0.5)
    home_edge = build_score_distribution(2.4, 2.4, 1.2, 0.7)
    neutral_markets = derive_hockey_markets(neutral)
    edge_markets = derive_hockey_markets(home_edge)

    assert edge_markets["ml_home"] > neutral_markets["ml_home"]


def test_select_hockey_finals_picks_the_higher_side() -> None:
    probabilities = {key: 40.0 for key in HOCKEY_MARKET_KEYS}
    probabilities["ml_home"] = 61.0
    probabilities["ml_away"] = 39.0
    probabilities["over_55"] = 55.0
    probabilities["under_55"] = 45.0

    selected = select_hockey_finals(probabilities, HOCKEY_MARKET_FAMILIES)

    assert len(selected) == len(HOCKEY_MARKET_FAMILIES)
    assert selected[0] == "ml_home"
    assert "over_55" in selected
    assert "ml_away" not in selected


def _chart_from_matrix(matrix: np.ndarray):
    distribution = HockeyScoreDistribution(
        regulation_matrix=matrix,
        final_matrix=matrix,
        p_ot_home=0.5)
    return derive_hockey_score_chart(distribution)


def test_score_chart_buckets_match_the_final_grid() -> None:
    distribution = build_score_distribution(3.1, 2.8, 1.25, 0.54)
    chart = derive_hockey_score_chart(distribution)
    markets = derive_hockey_markets(distribution)
    matrix = distribution.final_matrix
    home_margin = matrix.sum(axis=1)
    size = matrix.shape[0]
    total = np.arange(size)[:, None] + np.arange(size)[None, :]

    for buckets in (
            chart.home_buckets,
            chart.away_buckets,
            chart.total_buckets):
        assert sum(buckets.values()) == pytest.approx(100.0)
    assert chart.home_buckets["5+"] == pytest.approx(
        100.0 * float(home_margin[5:13].sum()))
    assert chart.total_buckets["8+"] == pytest.approx(
        100.0 * float(matrix[total >= 8].sum()))
    assert markets["over_55"] == pytest.approx(
        chart.total_buckets["6"]
        + chart.total_buckets["7"]
        + chart.total_buckets["8+"])
    assert markets["home_over_25"] == pytest.approx(
        chart.home_buckets["3"]
        + chart.home_buckets["4"]
        + chart.home_buckets["5+"])


def test_exact_scores_are_five_descending_catalog_results() -> None:
    distribution = build_score_distribution(3.0, 2.7, 1.2, 0.53)
    chart = derive_hockey_score_chart(distribution)
    labels = [label for label, _percent in chart.exact_scores]
    percents = [percent for _label, percent in chart.exact_scores]

    assert len(labels) == 5
    assert percents == sorted(percents, reverse=True)
    for label in labels:
        home_text, away_text = label.split(":")
        home = int(home_text)
        away = int(away_text)
        assert 0 <= home <= 7
        assert 0 <= away <= 7
        assert home != away


def test_tied_exact_scores_prefer_the_lower_home_total() -> None:
    matrix = np.zeros((13, 13))
    for home in range(8):
        for away in range(8):
            if home != away:
                matrix[home, away] = 1.0
    matrix /= matrix.sum()
    chart = _chart_from_matrix(matrix)
    labels = [label for label, _percent in chart.exact_scores]

    assert labels == ["0:1", "0:2", "0:3", "0:4", "0:5"]


def test_exact_scores_ignore_mass_outside_the_catalog() -> None:
    matrix = np.zeros((13, 13))
    matrix[9, 1] = 0.9
    matrix[3, 2] = 0.02
    matrix[2, 3] = 0.02
    matrix[4, 1] = 0.02
    matrix[1, 4] = 0.02
    matrix[5, 2] = 0.02
    chart = _chart_from_matrix(matrix)
    labels = [label for label, _percent in chart.exact_scores]

    assert "9:1" not in labels
    assert "3:2" in labels
    assert exact_score_event_id(3, 2) == 296
    assert exact_score_event_id(0, 0) == 270
    assert exact_score_event_id(7, 7) == 333


def test_map_hockey_chart_rows_stay_off_the_final_table() -> None:
    matrix = np.zeros((13, 13))
    matrix[3, 2] = 0.40
    matrix[2, 3] = 0.20
    matrix[4, 3] = 0.15
    matrix[3, 4] = 0.10
    matrix[1, 2] = 0.15
    chart = _chart_from_matrix(matrix)
    event_ids = {
        "home_goals_0": 252,
        "home_goals_1": 253,
        "home_goals_2": 254,
        "home_goals_3": 255,
        "home_goals_4": 256,
        "home_goals_5_plus": 257,
        "away_goals_0": 258,
        "away_goals_1": 259,
        "away_goals_2": 260,
        "away_goals_3": 261,
        "away_goals_4": 262,
        "away_goals_5_plus": 263,
        "total_goals_le3": 264,
        "total_goals_4": 265,
        "total_goals_5": 266,
        "total_goals_6": 267,
        "total_goals_7": 268,
        "total_goals_8_plus": 269}
    rows = map_hockey_chart_to_rows(7, 21, chart, event_ids)
    markets = derive_hockey_markets(
        build_score_distribution(3.0, 2.7, 1.2, 0.53))
    selected = select_hockey_finals(markets, HOCKEY_MARKET_FAMILIES)

    assert len(rows) == 23
    assert all(row.is_final is False for row in rows)
    assert all(0.0 <= row.value <= 100.0 for row in rows)
    scored = [row for row in rows if row.event_id == 296]
    assert len(scored) == 1
    assert scored[0].value == pytest.approx(40.0)
    assert len(selected) == 9
    assert set(selected) <= set(HOCKEY_MARKET_KEYS)


def test_distribution_rejects_bad_inputs() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        build_score_distribution(-0.1, 2.0, 1.0, 0.5)
    with pytest.raises(ValueError, match="tie_inflation"):
        build_score_distribution(2.0, 2.0, 0.0, 0.5)
    with pytest.raises(ValueError, match="p_ot_home"):
        build_score_distribution(2.0, 2.0, 1.0, 1.2)
    with pytest.raises(ValueError, match="max_goals"):
        build_score_distribution(2.0, 2.0, 1.0, 0.5, max_goals=0)
