"""Independent Poisson goal sampling for season simulation."""

from __future__ import annotations

import numpy as np


def sample_poisson_scores(
        rates: np.ndarray,
        rng: np.random.Generator) -> np.ndarray:
    """Sample independent home/away goals from Poisson rates.

    Does not fold the distribution into a 5+ bucket — high scores stay
    as exact integer goal counts.

    Args:
        rates: Array of shape ``(B, 2)`` with ``lambda_home``,
            ``lambda_away`` (finite and non-negative).
        rng: NumPy Generator used for all draws (deterministic when seeded).

    Returns:
        Integer array of shape ``(B, 2)`` with sampled ``[home, away]`` goals.
    """
    arr = np.asarray(rates, dtype=float)
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise ValueError("rates must have shape (B, 2)")
    if arr.shape[0] == 0:
        return np.zeros((0, 2), dtype=int)
    if not np.all(np.isfinite(arr)):
        raise ValueError("Poisson lambdas must be finite")
    if np.any(arr < 0.0):
        raise ValueError("Poisson lambdas must be non-negative")
    home = rng.poisson(arr[:, 0])
    away = rng.poisson(arr[:, 1])
    return np.stack([home, away], axis=1)
