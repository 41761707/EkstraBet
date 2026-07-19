"""Unit tests for sklearn trainer metric helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd

from models.pipeline.training.sklearn_trainer import (
    _brier_scores_per_class,
    _classification_metrics,
    _reliability_summary)


def test_brier_and_reliability_appear_in_metrics() -> None:
    y_true = pd.Series(["home_better", "draw", "away_better", "home_better"])
    y_pred = np.array(["home_better", "draw", "away_better", "draw"])
    y_proba = np.array([
        [0.7, 0.2, 0.1],
        [0.2, 0.6, 0.2],
        [0.1, 0.2, 0.7],
        [0.5, 0.4, 0.1]
    ])
    classes = ["home_better", "draw", "away_better"]

    metrics = _classification_metrics(y_true, y_pred, y_proba, classes)

    assert "brier_score_per_class" in metrics
    assert set(metrics["brier_score_per_class"]) == set(classes)
    assert metrics["brier_score_mean"] is not None
    assert "calibration_reliability" in metrics
    assert "home_better" in metrics["calibration_reliability"]


def test_reliability_summary_skips_empty_bins() -> None:
    y_true = pd.Series(["home_better", "home_better"])
    y_proba = np.array([
        [0.9, 0.05, 0.05],
        [0.85, 0.1, 0.05]
    ])
    classes = ["home_better", "draw", "away_better"]
    summary = _reliability_summary(y_true, y_proba, classes, n_bins=5)
    home_bins = summary["home_better"]
    assert home_bins
    assert all(bin_row["n"] > 0 for bin_row in home_bins)
    brier = _brier_scores_per_class(y_true, y_proba, classes)
    assert 0.0 <= brier["home_better"] <= 1.0
    assert 0.0 <= brier["away_better"] <= 1.0
