"""Shared conversion of DB probability percentages to API unit scale."""

from __future__ import annotations


def to_unit_probability(value: float) -> float:
    """Convert DB percentage (0-100) to unit probability [0, 1]."""
    probability = float(value)
    if probability < 0.0:
        return 0.0
    if probability > 100.0:
        return 1.0
    return probability / 100.0
