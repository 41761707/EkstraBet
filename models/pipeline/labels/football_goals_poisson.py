"""Goal-count targets for independent football Poisson models."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd

from models.pipeline.core.config import LabelerConfig
from models.pipeline.core.registry import register_labeler


def _validated_goal(row: Mapping[str, Any], key: str) -> int:
    value = row.get(key)
    if value is None:
        raise ValueError(f"Missing goal value: {key}")
    try:
        goal = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid goal value for {key}: {value!r}") from exc
    if goal < 0:
        raise ValueError(f"Goal value cannot be negative: {key}")
    return goal


def label_goals_poisson(row: Mapping[str, Any]) -> tuple[int, int]:
    """Return observed home and away goals without class conversion."""
    return (
        _validated_goal(row, "home_team_goals"),
        _validated_goal(row, "away_team_goals"))


def label_goals(row: Mapping[str, Any]) -> tuple[int, int]:
    """Return the Poisson goal pair using a concise integration alias."""
    return label_goals_poisson(row)


@register_labeler("FootballGoalsPoissonLabeler")
class FootballGoalsPoissonLabeler:
    """Build paired home and away goal-count targets."""

    def __init__(self, config: LabelerConfig | None = None) -> None:
        del config

    def label(self, row: Mapping[str, Any]) -> tuple[int, int]:
        """Label one match."""
        return label_goals_poisson(row)

    def build_labels(self, frame: pd.DataFrame) -> np.ndarray:
        """Return an integer target matrix with home and away columns."""
        return np.asarray(
            [label_goals_poisson(row) for _, row in frame.iterrows()],
            dtype=np.int64)
