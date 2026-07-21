"""Labels for the three-way football result classifier."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from models.pipeline.core.config import LabelerConfig
from models.pipeline.core.registry import register_labeler

RESULT_LABELS = {"1": 0, "X": 1, "2": 2}


def label_result(row: Mapping[str, Any]) -> int:
    """Map a database result value to home, draw, or away class."""
    result = str(row.get("result", "")).strip().upper()
    if result not in RESULT_LABELS:
        raise ValueError(f"Unsupported football result: {result!r}")
    return RESULT_LABELS[result]


@register_labeler("FootballResultLabeler")
class FootballResultLabeler:
    """Build integer labels for the result classifier."""

    def __init__(self, config: LabelerConfig | None = None) -> None:
        del config

    def label(self, row: Mapping[str, Any]) -> int:
        """Label one match."""
        return label_result(row)

    def build_labels(self, frame: pd.DataFrame) -> pd.Series:
        """Label all frame rows while preserving their index."""
        return frame.apply(label_result, axis=1).astype(int)
