"""Probability scores for champion and challenger comparison.

The functions are pure. They do not open a database connection and
they do not load a model.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np


_LOG_LOSS_CLIP = 1e-12
_BOOTSTRAP_LOW = 2.5
_BOOTSTRAP_HIGH = 97.5


def binary_log_loss(p: np.ndarray, outcomes: np.ndarray) -> float:
    """Return the mean binary log loss."""
    return float(np.mean(_binary_losses(p, outcomes)))


def multiclass_log_loss(
        probabilities: np.ndarray,
        labels: np.ndarray) -> float:
    """Return the mean log loss of the true class."""
    return float(np.mean(_multiclass_losses(probabilities, labels)))


def binary_brier(p: np.ndarray, outcomes: np.ndarray) -> float:
    """Return the mean squared error of binary probabilities."""
    vector = _vector(p, "p")
    results = _class_indexes(outcomes, len(vector), 2).astype(float)
    gap = vector - results
    return float(np.mean(gap * gap))


def multiclass_brier(
        probabilities: np.ndarray,
        labels: np.ndarray) -> float:
    """Return the mean of squared errors summed across classes."""
    matrix = _matrix(probabilities)
    indexes = _class_indexes(labels, matrix.shape[0], matrix.shape[1])
    target = np.zeros_like(matrix)
    target[np.arange(matrix.shape[0]), indexes] = 1.0
    gap = matrix - target
    return float(np.mean(np.sum(gap * gap, axis=1)))


def per_match_log_loss(
        probabilities: np.ndarray,
        labels: np.ndarray) -> np.ndarray:
    """Return one log loss per match.

    A vector is the probability of the positive class. Two columns
    are a binary distribution and wider rows are multiclass.
    ``labels`` are 0/1 outcomes or class indexes, in the same order.
    Probabilities are clipped at 1e-12 before the logarithm.
    """
    array = np.asarray(probabilities, dtype=float)
    if array.ndim == 1:
        return _binary_losses(array, labels)
    if array.ndim == 2:
        return _multiclass_losses(array, labels)
    raise ValueError("probabilities must be a vector or a matrix")


def expected_calibration_error(
        p: np.ndarray,
        outcomes: np.ndarray,
        bins: int = 10) -> float:
    """Return the count-weighted absolute calibration error.

    A matrix is scored one-vs-rest for every class and then averaged.
    That is the 1X2 case. A vector is one binary probability.
    """
    _positive_int(bins, "bins")
    array = np.asarray(p, dtype=float)
    if array.ndim == 1:
        vector = _vector(array, "p")
        results = _class_indexes(outcomes, len(vector), 2).astype(float)
        return _ece(vector, results, bins)
    if array.ndim == 2:
        matrix = _matrix(array)
        indexes = _class_indexes(
            outcomes, matrix.shape[0], matrix.shape[1])
        scores = [
            _ece(
                matrix[:, class_index],
                (indexes == class_index).astype(float),
                bins)
            for class_index in range(matrix.shape[1])]
        return float(np.mean(scores))
    raise ValueError("p must be a vector or a matrix")


def reliability_table(
        p: np.ndarray,
        outcomes: np.ndarray,
        edges: Sequence[float]) -> list[dict[str, str | int | float]]:
    """Return non-empty calibration bins.

    ``bin`` is the percent range, for example ``40-45``. ``n`` is
    the match count, ``mean_p`` the mean probability and ``actual``
    the observed rate. The last bin includes its right edge.
    """
    probabilities = _vector(p, "p")
    results = _class_indexes(outcomes, len(probabilities), 2).astype(float)
    bounds = _edges(edges)
    _require_inside(probabilities, bounds, "p")
    rows: list[dict[str, str | int | float]] = []
    last = len(bounds) - 2
    for bin_index in range(last + 1):
        chosen = _inside_bin(
            probabilities,
            float(bounds[bin_index]),
            float(bounds[bin_index + 1]),
            bin_index == last)
        count = int(np.sum(chosen))
        if count == 0:
            continue
        low = float(bounds[bin_index])
        high = float(bounds[bin_index + 1])
        rows.append({
            "bin": _bin_name(low, high),
            "n": count,
            "mean_p": float(np.mean(probabilities[chosen])),
            "actual": float(np.mean(results[chosen]))})
    return rows


def final_shares(finals: np.ndarray, classes: int) -> list[float]:
    """Return the share of matches assigned to each class."""
    _positive_int(classes, "classes")
    labels = np.asarray(finals)
    if labels.ndim != 1:
        raise ValueError("finals must be one class index per match")
    indexes = _class_indexes(labels, len(labels), classes)
    return [
        float(np.mean(indexes == class_index))
        for class_index in range(classes)]


def paired_bootstrap_diff(
        loss_a: np.ndarray,
        loss_b: np.ndarray,
        samples: int,
        seed: int) -> dict[str, float]:
    """Return the paired difference of two per-match losses.

    ``mean_diff`` is ``mean(loss_a) - mean(loss_b)``. Matches are
    drawn with replacement. ``ci_low`` and ``ci_high`` are the 2.5
    and 97.5 percentiles of that resample.
    """
    left = _vector(loss_a, "loss_a")
    right = _vector(loss_b, "loss_b")
    if len(left) != len(right):
        raise ValueError("loss vectors must have the same length")
    _positive_int(samples, "samples")
    _require_int(seed, "seed")
    observed = float(np.mean(left - right))
    generator = np.random.default_rng(seed)
    drawn = generator.integers(0, len(left), size=(samples, len(left)))
    resampled = np.mean(left[drawn] - right[drawn], axis=1)
    low, high = np.percentile(resampled, [_BOOTSTRAP_LOW, _BOOTSTRAP_HIGH])
    return {
        "mean_diff": observed,
        "ci_low": float(low),
        "ci_high": float(high)}


def _binary_losses(
        probabilities: np.ndarray,
        outcomes: np.ndarray) -> np.ndarray:
    vector = _vector(probabilities, "p")
    results = _class_indexes(outcomes, len(vector), 2).astype(float)
    positive = np.clip(vector, _LOG_LOSS_CLIP, 1.0)
    negative = np.clip(1.0 - vector, _LOG_LOSS_CLIP, 1.0)
    # Klip tylko przed logarytmem: 0 i 1 są dozwolone.
    return -(
        results * np.log(positive)
        + (1.0 - results) * np.log(negative))


def _multiclass_losses(
        probabilities: np.ndarray,
        labels: np.ndarray) -> np.ndarray:
    matrix = _matrix(probabilities)
    indexes = _class_indexes(labels, matrix.shape[0], matrix.shape[1])
    chosen = matrix[np.arange(matrix.shape[0]), indexes]
    clipped = np.clip(chosen, _LOG_LOSS_CLIP, 1.0)
    return -np.log(clipped)


def _ece(
        probabilities: np.ndarray,
        outcomes: np.ndarray,
        bins: int) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    _require_inside(probabilities, edges, "p")
    total = 0.0
    count = len(probabilities)
    for bin_index in range(bins):
        chosen = _inside_bin(
            probabilities,
            float(edges[bin_index]),
            float(edges[bin_index + 1]),
            bin_index == bins - 1)
        weight = int(np.sum(chosen))
        if weight == 0:
            continue
        gap = abs(
            float(np.mean(probabilities[chosen]))
            - float(np.mean(outcomes[chosen])))
        total += (weight / count) * gap
    return total


def _inside_bin(
        probabilities: np.ndarray,
        low: float,
        high: float,
        last: bool) -> np.ndarray:
    # Ostatni koszyk domyka się z prawej, żeby skrajne p nie wypadło.
    if last:
        return (probabilities >= low) & (probabilities <= high)
    return (probabilities >= low) & (probabilities < high)


def _bin_name(low: float, high: float) -> str:
    return f"{_percent(low)}-{_percent(high)}"


def _percent(value: float) -> str:
    scaled = value * 100.0
    nearest = round(scaled)
    if math.isclose(scaled, nearest, abs_tol=1e-6):
        return str(int(nearest))
    rendered = f"{scaled:.4f}".rstrip("0").rstrip(".")
    return rendered


def _edges(edges: Sequence[float]) -> np.ndarray:
    if isinstance(edges, (str, bytes)) or not isinstance(edges, Sequence):
        raise ValueError("edges must be a sequence of bounds")
    bounds = np.asarray(list(edges), dtype=float)
    if bounds.ndim != 1 or len(bounds) < 2:
        raise ValueError("edges must contain at least two bounds")
    if not np.isfinite(bounds).all() or np.any(np.diff(bounds) <= 0.0):
        raise ValueError("edges must be strictly increasing")
    return bounds


def _vector(values: np.ndarray, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if array.size == 0:
        raise ValueError(f"{name} must contain at least one value")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} must be finite")
    return array


def _matrix(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 2 or array.shape[1] < 2:
        raise ValueError(
            "probabilities must have one row per match "
            "and at least two classes")
    if array.shape[0] == 0:
        raise ValueError("probabilities must contain at least one match")
    if not np.isfinite(array).all():
        raise ValueError("probabilities must be finite")
    return array


def _class_indexes(
        labels: np.ndarray,
        count: int,
        class_count: int) -> np.ndarray:
    values = np.asarray(labels)
    if values.ndim != 1 or len(values) != count:
        raise ValueError("labels must have one class index per match")
    if count == 0:
        raise ValueError("labels must contain at least one match")
    if values.dtype == np.bool_ or not np.issubdtype(values.dtype, np.number):
        raise ValueError("labels must be class indexes")
    if not np.isfinite(values).all():
        raise ValueError("labels must be finite")
    indexes = values.astype(int)
    if not np.all(indexes == values):
        raise ValueError("labels must be class indexes")
    if np.any((indexes < 0) | (indexes >= class_count)):
        raise ValueError("labels must be class indexes")
    return indexes


def _require_inside(
        values: np.ndarray,
        edges: np.ndarray,
        name: str) -> None:
    if np.any(values < edges[0]) or np.any(values > edges[-1]):
        raise ValueError(f"{name} must lie inside the bin edges")


def _positive_int(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")


def _require_int(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
