"""Skater counting-stat labels and Poisson over-probabilities.

Each dressed skater gets seven beta lines: shots 1.5/2.5/3.5, goals
0.5, assists 0.5 and points 0.5/1.5. A half-point line ``n + 0.5``
is ``P(X >= n + 1)`` under a Poisson with mean lambda.
"""

from __future__ import annotations

import math

import pandas as pd

from models.pipeline.core.config import LabelerConfig
from models.pipeline.core.registry import register_labeler


TARGET_COLUMNS = ["sog", "goals", "assists", "points"]
LINES_PER_SKATER = 7
# Klucz zdarzenia jest „Powyżej X” z player_props_lines (190/192/194/196).
PROP_LINES = (
    ("sog", 1.5, "sog_over"),
    ("sog", 2.5, "sog_over"),
    ("sog", 3.5, "sog_over"),
    ("goals", 0.5, "goals_over"),
    ("assists", 0.5, "assists_over"),
    ("points", 0.5, "points_over"),
    ("points", 1.5, "points_over"))


def poisson_over_probability(rate: float, line: float) -> float:
    """Return ``P(X > line)`` in percent for one Poisson mean.

    ``line`` is a half-point total. A larger line never raises the
    probability of the same mean.
    """
    if not math.isfinite(rate) or rate < 0.0:
        raise ValueError("Poisson rate must be finite and non-negative")
    if not math.isfinite(line) or line <= 0.0:
        raise ValueError("Prop line must be a positive finite number")
    threshold = math.floor(line)
    half_point = threshold + 0.5
    if not math.isclose(line, half_point):
        raise ValueError("Prop line must sit on a half-point")
    survival = _poisson_survival(int(threshold), rate)
    return max(0.0, min(100.0, survival * 100.0))


def _poisson_survival(threshold: int, rate: float) -> float:
    """Return ``P(X > threshold)`` for a non-negative integer cutoff."""
    if threshold < 0:
        return 1.0
    if rate == 0.0:
        return 0.0
    # Skumulowana masa od 0 do progu. Przy λ < 40 i małym progu jest stabilna.
    term = math.exp(-rate)
    cumulative = term
    for count in range(1, threshold + 1):
        term *= rate / count
        cumulative += term
    return max(0.0, min(1.0, 1.0 - cumulative))


@register_labeler("HockeyPlayerPropsLabeler")
class HockeyPlayerPropsLabeler:
    """Read shots, goals, assists and points from a skater frame."""

    def __init__(self, config: LabelerConfig | None = None) -> None:
        del config

    def build_labels(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Return the four counting targets, aligned to ``frame``."""
        missing = [
            column for column in TARGET_COLUMNS
            if column not in frame.columns]
        if missing:
            raise KeyError(f"Missing player-prop labels: {missing}")
        labels = frame.loc[:, TARGET_COLUMNS].apply(
            pd.to_numeric, errors="coerce")
        return labels
