"""Binary labels for both-teams-to-score football models."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from models.pipeline.core.config import LabelerConfig
from models.pipeline.core.registry import register_labeler


def _goal(row: Mapping[str, Any], key: str) -> int:
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


def label_btts(row: Mapping[str, Any]) -> int:
    """Return 1 when both teams scored and otherwise return 0."""
    home_goals = _goal(row, "home_team_goals")
    away_goals = _goal(row, "away_team_goals")
    return int(home_goals > 0 and away_goals > 0)


@register_labeler("FootballBttsLabeler")
class FootballBttsLabeler:
    """Build binary labels for the BTTS classifier."""

    def __init__(self, config: LabelerConfig | None = None) -> None:
        del config

    def label(self, row: Mapping[str, Any]) -> int:
        """Label one match."""
        return label_btts(row)

    def build_labels(self, frame: pd.DataFrame) -> pd.Series:
        """Label all frame rows while preserving their index."""
        return frame.apply(label_btts, axis=1).astype(int)
