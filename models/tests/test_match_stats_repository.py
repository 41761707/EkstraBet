"""Tests for match stats repository SQL helpers and xG normalization."""

from __future__ import annotations

import pandas as pd
import pytest

from models.pipeline.core.config import FeatureConfig
from models.pipeline.data.match_stats_repository import (
    _normalize_zero_xg_as_missing,
    _xg_filter)


def test_xg_filter_none_by_default() -> None:
    assert _xg_filter() is None
    assert _xg_filter(False, False) is None


def test_xg_filter_require_positive() -> None:
    clause = _xg_filter(require_positive_xg=True)
    assert clause is not None
    assert "home_team_xg > 0" in clause
    assert "away_team_xg > 0" in clause


def test_xg_filter_exclude_positive() -> None:
    clause = _xg_filter(exclude_positive_xg=True)
    assert clause is not None
    assert clause.startswith("NOT (")
    assert "home_team_xg > 0" in clause


def test_xg_filter_rejects_both_flags() -> None:
    with pytest.raises(ValueError, match="mutually exclusive"):
        _xg_filter(require_positive_xg=True, exclude_positive_xg=True)


def test_normalize_zero_xg_as_missing() -> None:
    frame = pd.DataFrame({
        "home_team_xg": [1.2, 0.0, None],
        "away_team_xg": [0.8, 0.0, 1.1]
    })
    normalized = _normalize_zero_xg_as_missing(frame)
    assert normalized.loc[0, "home_team_xg"] == 1.2
    assert pd.isna(normalized.loc[1, "home_team_xg"])
    assert pd.isna(normalized.loc[1, "away_team_xg"])
    assert pd.isna(normalized.loc[2, "home_team_xg"])


def test_feature_config_rejects_both_xg_flags() -> None:
    with pytest.raises(ValueError, match="mutually exclusive"):
        FeatureConfig(require_positive_xg=True, exclude_positive_xg=True)
