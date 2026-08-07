"""Tests for independent Poisson goal sampling."""

from __future__ import annotations

import numpy as np
import pytest

from models.pipeline.simulation.outcome_sampler import sample_poisson_scores


def test_sample_poisson_scores_shape_and_dtype() -> None:
    rates = np.asarray([[1.2, 0.8], [2.0, 1.5]], dtype=float)
    rng = np.random.default_rng(42)

    scores = sample_poisson_scores(rates, rng)

    assert scores.shape == (2, 2)
    assert scores.dtype == int or np.issubdtype(scores.dtype, np.integer)
    assert np.all(scores >= 0)


def test_sample_poisson_scores_deterministic_for_same_seed() -> None:
    rates = np.asarray([[1.5, 1.1], [0.7, 2.3], [3.0, 0.4]], dtype=float)

    first = sample_poisson_scores(rates, np.random.default_rng(7))
    second = sample_poisson_scores(rates, np.random.default_rng(7))
    third = sample_poisson_scores(rates, np.random.default_rng(8))

    assert np.array_equal(first, second)
    assert not np.array_equal(first, third)


def test_sample_poisson_scores_means_match_lambdas() -> None:
    lambda_home = 1.4
    lambda_away = 0.9
    rates = np.full((20000, 2), [lambda_home, lambda_away], dtype=float)
    rng = np.random.default_rng(123)

    scores = sample_poisson_scores(rates, rng)

    assert float(scores[:, 0].mean()) == pytest.approx(lambda_home, abs=0.05)
    assert float(scores[:, 1].mean()) == pytest.approx(lambda_away, abs=0.05)


def test_sample_poisson_scores_allows_tail_above_five() -> None:
    # wysoka lambda gwarantuje trafienia powyżej sztucznego progu 5+
    rates = np.full((5000, 2), [8.0, 7.0], dtype=float)
    rng = np.random.default_rng(99)

    scores = sample_poisson_scores(rates, rng)

    assert int(scores[:, 0].max()) > 5
    assert int(scores[:, 1].max()) > 5


def test_sample_poisson_scores_rejects_nan_lambdas() -> None:
    rates = np.asarray([[1.0, np.nan]], dtype=float)
    rng = np.random.default_rng(1)

    with pytest.raises(ValueError, match="finite"):
        sample_poisson_scores(rates, rng)


def test_sample_poisson_scores_rejects_negative_lambdas() -> None:
    rates = np.asarray([[1.0, -0.1]], dtype=float)
    rng = np.random.default_rng(1)

    with pytest.raises(ValueError, match="non-negative"):
        sample_poisson_scores(rates, rng)


def test_sample_poisson_scores_rejects_wrong_shape() -> None:
    rng = np.random.default_rng(1)

    with pytest.raises(ValueError, match="shape"):
        sample_poisson_scores(np.asarray([1.0, 2.0], dtype=float), rng)


def test_sample_poisson_scores_empty_batch() -> None:
    rates = np.zeros((0, 2), dtype=float)
    rng = np.random.default_rng(1)

    scores = sample_poisson_scores(rates, rng)

    assert scores.shape == (0, 2)
