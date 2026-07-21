"""Poisson score matrices and derived football goal markets."""

from __future__ import annotations

import math

import numpy as np


def _poisson_probability(goals: int, rate: float) -> float:
    return math.exp(-rate) * (rate ** goals) / math.factorial(goals)


def _folded_poisson(rate: float, max_goals: int) -> np.ndarray:
    probabilities = np.array([
        _poisson_probability(goals, rate)
        for goals in range(max_goals)
    ], dtype=float)
    tail = max(0.0, 1.0 - float(probabilities.sum()))
    return np.append(probabilities, tail)


def score_matrix_from_lambdas(
        lambda_home: float,
        lambda_away: float,
        max_goals: int = 5) -> np.ndarray:
    """Build a normalized matrix whose final row and column mean max_goals+."""
    if lambda_home < 0.0 or lambda_away < 0.0:
        raise ValueError("Poisson lambdas must be non-negative")
    if max_goals < 1:
        raise ValueError("max_goals must be at least one")
    home = _folded_poisson(float(lambda_home), max_goals)
    away = _folded_poisson(float(lambda_away), max_goals)
    matrix = np.outer(home, away)
    total = float(matrix.sum())
    if total <= 0.0 or not np.isfinite(total):
        raise ValueError("Score matrix could not be normalized")
    return matrix / total


def _bucket_markets_from_matrix(
        matrix: np.ndarray) -> dict[str, float]:
    buckets = {str(total): 0.0 for total in range(6)}
    buckets["6+"] = 0.0
    for home_goals in range(matrix.shape[0]):
        for away_goals in range(matrix.shape[1]):
            total = home_goals + away_goals
            key = str(total) if total <= 5 else "6+"
            buckets[key] += float(matrix[home_goals, away_goals])
    return buckets


def _bucket_markets_from_lambdas(
        lambda_home: float,
        lambda_away: float) -> dict[str, float]:
    total_rate = float(lambda_home + lambda_away)
    buckets = {
        str(goals): _poisson_probability(goals, total_rate)
        for goals in range(6)
    }
    buckets["6+"] = max(0.0, 1.0 - sum(buckets.values()))
    return buckets


def derive_goal_markets(
        matrix: np.ndarray,
        lambda_home: float | None = None,
        lambda_away: float | None = None
) -> dict[str, object]:
    """Derive 0..6+ total-goal buckets and over/under 2.5 markets."""
    score_matrix = np.asarray(matrix, dtype=float)
    if score_matrix.ndim != 2 or score_matrix.shape[0] != score_matrix.shape[1]:
        raise ValueError("Score matrix must be square")
    if np.any(score_matrix < 0.0):
        raise ValueError("Score matrix cannot contain negative values")
    total = float(score_matrix.sum())
    if not np.isclose(total, 1.0, atol=1e-8):
        raise ValueError("Score matrix must sum to one")
    if lambda_home is not None and lambda_away is not None:
        buckets = _bucket_markets_from_lambdas(
            lambda_home, lambda_away)
    else:
        buckets = _bucket_markets_from_matrix(score_matrix)
    under_25 = sum(buckets[str(goals)] for goals in range(3))
    over_25 = max(0.0, 1.0 - under_25)
    return {
        "total_buckets": buckets,
        "over_25": over_25,
        "under_25": under_25
    }


def exact_score_probabilities(
        matrix: np.ndarray,
        max_goals: int = 5) -> dict[str, float]:
    """Map every folded score cell to its dynamic event name."""
    score_matrix = np.asarray(matrix, dtype=float)
    expected_shape = (max_goals + 1, max_goals + 1)
    if score_matrix.shape != expected_shape:
        raise ValueError(
            f"Expected score matrix shape {expected_shape}, "
            f"got {score_matrix.shape}")
    labels = [
        str(goals) for goals in range(max_goals)
    ] + [f"{max_goals}+"]
    return {
        f"{home}:{away}": float(score_matrix[home_index, away_index])
        for home_index, home in enumerate(labels)
        for away_index, away in enumerate(labels)
    }


def top_exact_scores(
        matrix: np.ndarray,
        limit: int = 5,
        max_goals: int = 5) -> list[tuple[str, float]]:
    """Return exact score event names ordered by descending probability."""
    if limit < 1:
        raise ValueError("limit must be at least one")
    probabilities = exact_score_probabilities(matrix, max_goals)
    return sorted(
        probabilities.items(),
        key=lambda item: item[1],
        reverse=True)[:limit]
