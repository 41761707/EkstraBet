"""Tests for football match feature extraction."""

from __future__ import annotations

import pandas as pd

from models.pipeline.core.config import FeatureConfig
from models.pipeline.features.football_match_stats import (
    FEATURE_COLUMNS,
    build_features,
    resolve_feature_columns)


def _base_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "id": 1,
        "sport_id": 1,
        "home_team_xg": 1.8,
        "away_team_xg": 0.9,
        "home_team_bp": 60,
        "away_team_bp": 40,
        "home_team_sc": 14,
        "away_team_sc": 8,
        "home_team_sog": 6,
        "away_team_sog": 3,
        "home_team_ck": 7,
        "away_team_ck": 2,
        "home_team_fk": 12,
        "away_team_fk": 10,
        "home_team_off": 2,
        "away_team_off": 1,
        "home_team_fouls": 9,
        "away_team_fouls": 11,
        "home_team_yc": 1,
        "away_team_yc": 2,
        "home_team_rc": 0,
        "away_team_rc": 0,
        "home_team_goals": 0,
        "away_team_goals": 1,
        "result": "2"
    }
    row.update(overrides)
    return row


def test_build_features_diffs_and_shares() -> None:
    frame = pd.DataFrame([_base_row()])
    features = build_features(frame)
    assert len(features) == 1
    row = features.iloc[0]
    assert row["xg_diff"] == 0.9
    assert row["possession_diff"] == 20
    assert row["shots_diff"] == 6
    assert row["shots_on_goal_diff"] == 3
    assert row["corners_diff"] == 5
    assert abs(row["home_xg_share"] - 1.8 / 2.7) < 1e-9
    assert abs(row["home_possession_share"] - 0.6) < 1e-9
    for column in FEATURE_COLUMNS:
        assert column in features.columns
    assert "home_team_goals" not in features.columns
    assert "result" not in features.columns


def test_build_features_handles_zero_division() -> None:
    frame = pd.DataFrame([_base_row(
        home_team_sc=0,
        away_team_sc=0,
        home_team_sog=0,
        away_team_sog=0)])
    features = build_features(frame)
    row = features.iloc[0]
    assert row["home_shots_share"] == 0.5
    assert row["home_sog_per_shot"] == 0.0
    assert row["xg_per_shot_home"] == 0.0


def test_build_features_skips_zero_xg_when_xg_required() -> None:
    frame = pd.DataFrame([
        _base_row(id=1),
        _base_row(id=2, home_team_xg=0.0, away_team_xg=0.0)
    ])
    features = build_features(frame)
    assert list(features["match_id"]) == [1]


def test_build_features_omits_xg_when_xg_not_required() -> None:
    frame = pd.DataFrame([_base_row(
        home_team_xg=0.0,
        away_team_xg=0.0)])
    config = FeatureConfig(
        required_columns=[
            "home_team_sc",
            "away_team_sc",
            "home_team_sog",
            "away_team_sog",
            "home_team_bp",
            "away_team_bp",
            "home_team_ck",
            "away_team_ck"
        ])
    features = build_features(frame, config)
    assert len(features) == 1
    assert "xg_diff" not in features.columns
    assert "possession_diff" in features.columns


def test_build_features_omits_xg_for_partial_xg_when_excluded() -> None:
    frame = pd.DataFrame([
        _base_row(id=1, home_team_xg=1.5, away_team_xg=0.0),
        _base_row(id=2, home_team_xg=0.0, away_team_xg=1.2)
    ])
    config = FeatureConfig(
        required_columns=[
            "home_team_sc",
            "away_team_sc",
            "home_team_sog",
            "away_team_sog",
            "home_team_bp",
            "away_team_bp",
            "home_team_ck",
            "away_team_ck"
        ],
        exclude_positive_xg=True)
    features = build_features(frame, config)
    assert list(features["match_id"]) == [1, 2]
    assert "xg_diff" not in features.columns
    assert "total_xg" not in features.columns
    assert "home_xg_share" not in features.columns
    assert "xg_per_shot_home" not in features.columns
    assert "possession_diff" in features.columns


def test_build_features_skips_missing_required_and_imputes_optional() -> None:
    frame = pd.DataFrame([
        _base_row(id=1),
        _base_row(id=2, home_team_xg=None),
        _base_row(id=3, home_team_fouls=None, home_team_yc=None)
    ])
    config = FeatureConfig(
        required_columns=[
            "home_team_xg",
            "away_team_xg",
            "home_team_sc",
            "away_team_sc",
            "home_team_sog",
            "away_team_sog",
            "home_team_bp",
            "away_team_bp",
            "home_team_ck",
            "away_team_ck"
        ],
        imputable_columns=[
            "home_team_fouls",
            "away_team_fouls",
            "home_team_yc",
            "away_team_yc",
            "home_team_rc",
            "away_team_rc"
        ])
    features = build_features(frame, config)
    assert list(features["match_id"]) == [1, 3]
    assert features.loc[features["match_id"] == 3, "fouls_diff"].iloc[0] == -11


def test_build_features_includes_goals_diff_when_flag_enabled() -> None:
    frame = pd.DataFrame([_base_row()])
    config = FeatureConfig(include_goals_as_features=True, sport_id=1)
    features = build_features(frame, config)
    assert "goals_diff" in features.columns
    assert features.iloc[0]["goals_diff"] == -1.0
    resolved = resolve_feature_columns(
        features.columns, include_goals=True)
    assert "goals_diff" in resolved


def test_build_features_filters_by_config_sport_id() -> None:
    frame = pd.DataFrame([
        _base_row(id=1, sport_id=1),
        _base_row(id=2, sport_id=2)
    ])
    config = FeatureConfig(sport_id=1)
    features = build_features(frame, config)
    assert list(features["match_id"]) == [1]
