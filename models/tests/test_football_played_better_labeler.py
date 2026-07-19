"""Tests for football played-better weak labeler."""

from __future__ import annotations

import pandas as pd

from models.pipeline.core.config import LabelerConfig
from models.pipeline.labels.football_played_better import (
    CLASS_AWAY,
    CLASS_DRAW,
    CLASS_HOME,
    FootballPlayedBetterLabeler,
    build_labels,
    compute_dominance_score)


def _feature_row(**overrides: float) -> dict[str, float | int]:
    row: dict[str, float | int] = {
        "match_id": 1,
        "xg_diff": 0.0,
        "shots_diff": 0.0,
        "shots_on_goal_diff": 0.0,
        "possession_diff": 0.0,
        "corners_diff": 0.0,
        "free_kicks_diff": 0.0,
        "offsides_diff": 0.0,
        "fouls_diff": 0.0,
        "yellow_cards_diff": 0.0,
        "red_cards_diff": 0.0
    }
    row.update(overrides)
    return row


def test_labeler_home_dominance() -> None:
    frame = pd.DataFrame([_feature_row(xg_diff=2.5, shots_diff=8, shots_on_goal_diff=4)])
    labels = build_labels(frame)
    assert labels.iloc[0]["label"] == CLASS_HOME
    assert labels.iloc[0]["home_prob"] > labels.iloc[0]["away_prob"]
    assert abs(
        labels.iloc[0]["home_prob"]
        + labels.iloc[0]["draw_prob"]
        + labels.iloc[0]["away_prob"] - 1.0) < 1e-6


def test_labeler_away_dominance() -> None:
    frame = pd.DataFrame([_feature_row(xg_diff=-2.0, shots_diff=-6, corners_diff=-4)])
    labels = build_labels(frame)
    assert labels.iloc[0]["label"] == CLASS_AWAY
    assert labels.iloc[0]["away_prob"] > labels.iloc[0]["home_prob"]


def test_labeler_balanced_match_is_draw() -> None:
    frame = pd.DataFrame([_feature_row()])
    config = LabelerConfig(draw_threshold=0.15, temperature=1.0)
    labels = FootballPlayedBetterLabeler(config).build_labels(frame)
    assert labels.iloc[0]["label"] == CLASS_DRAW
    assert labels.iloc[0]["draw_prob"] >= labels.iloc[0]["home_prob"]
    assert labels.iloc[0]["draw_prob"] >= labels.iloc[0]["away_prob"]


def test_labeler_cards_penalty_reduces_home_score() -> None:
    base = pd.DataFrame([_feature_row(xg_diff=0.4)])
    with_cards = pd.DataFrame([_feature_row(xg_diff=0.4, red_cards_diff=2.0)])
    base_score = compute_dominance_score(base).iloc[0]
    cards_score = compute_dominance_score(with_cards).iloc[0]
    assert cards_score < base_score


def test_labeler_accepts_features_without_xg_diff() -> None:
    row = _feature_row(shots_diff=8, shots_on_goal_diff=4, possession_diff=20)
    del row["xg_diff"]
    frame = pd.DataFrame([row])
    config = LabelerConfig(
        weights={
            "shots_diff": 1.0,
            "shots_on_goal_diff": 1.2,
            "possession_diff": 0.8
        })
    labels = build_labels(frame, config)
    assert len(labels) == 1
    assert labels.iloc[0]["label"] == CLASS_HOME
    assert "match_id" in labels.columns
