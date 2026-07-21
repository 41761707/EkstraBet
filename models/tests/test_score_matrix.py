"""Focused tests for folded Poisson score markets."""

from __future__ import annotations

import math

import numpy as np

from models.pipeline.prediction.score_matrix import derive_goal_markets
from models.pipeline.prediction.score_matrix import exact_score_probabilities
from models.pipeline.prediction.score_matrix import score_matrix_from_lambdas


def test_score_matrix_folds_tail_and_normalizes() -> None:
    matrix = score_matrix_from_lambdas(1.7, 1.2, max_goals=5)

    assert matrix.shape == (6, 6)
    assert np.isclose(matrix.sum(), 1.0)
    assert np.all(matrix >= 0.0)

    explicit_home = sum(
        np.exp(-1.7) * (1.7 ** goals) / math.factorial(goals)
        for goals in range(5))
    assert np.isclose(matrix[-1, :].sum(), 1.0 - explicit_home)


def test_goal_markets_are_consistent_with_total_poisson() -> None:
    matrix = score_matrix_from_lambdas(1.4, 0.9)
    markets = derive_goal_markets(matrix, 1.4, 0.9)
    buckets = markets["total_buckets"]

    assert np.isclose(sum(buckets.values()), 1.0)
    assert np.isclose(
        markets["under_25"],
        buckets["0"] + buckets["1"] + buckets["2"])
    assert np.isclose(
        markets["over_25"] + markets["under_25"], 1.0)


def test_exact_scores_use_folded_5_plus_names() -> None:
    matrix = score_matrix_from_lambdas(2.0, 1.0)
    exact = exact_score_probabilities(matrix)

    assert len(exact) == 36
    assert "0:0" in exact
    assert "5+:5+" in exact
    assert np.isclose(sum(exact.values()), 1.0)
