"""Tests for model configuration loading and validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from models.pipeline.core.config import load_model_config

REPO_ROOT = Path(__file__).resolve().parents[2]


def _valid_payload() -> dict[str, object]:
    return {
        "model_name": "FOOTBALL_PLAYED_BETTER_V1",
        "sport_id": 1,
        "task_type": "match_assessment",
        "artifact_path": "models/artifacts/dev/football_played_better_v1",
        "feature_builder": "FootballMatchStatsFeatureBuilder",
        "labeler": "FootballPlayedBetterLabeler",
        "trainer": "SklearnTrainer",
        "output_columns": [
            "home_played_better_probability",
            "draw_probability",
            "away_played_better_probability"
        ],
        "feature_config": {
            "include_goals_as_features": False
        }
    }


def test_load_model_config_accepts_valid_file(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(_valid_payload()), encoding="utf-8")
    config = load_model_config(path)
    assert config.model_name == "FOOTBALL_PLAYED_BETTER_V1"
    assert config.artifact_dir == (
        REPO_ROOT / "models/artifacts/dev/football_played_better_v1"
    ).resolve()
    assert config.feature_config.include_goals_as_features is False
    assert config.feature_config.sport_id == 1
    assert len(config.output_columns) == 3


def test_load_model_config_rejects_missing_output_columns(tmp_path: Path) -> None:
    payload = _valid_payload()
    payload["output_columns"] = []
    path = tmp_path / "bad_output.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="output_columns"):
        load_model_config(path)


def test_load_model_config_rejects_missing_artifact_path(tmp_path: Path) -> None:
    payload = _valid_payload()
    payload["artifact_path"] = ""
    path = tmp_path / "bad_artifact.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="artifact_path"):
        load_model_config(path)


def test_repo_training_config_loads() -> None:
    path = (
        REPO_ROOT
        / "models"
        / "configs"
        / "training"
        / "football_played_better_v1.json")
    config = load_model_config(path)
    assert config.trainer == "SklearnTrainer"
    assert config.training_config is not None
    assert config.training_config.algorithm == "HistGradientBoostingClassifier"
    assert config.feature_config.require_positive_xg is True
    assert config.feature_config.exclude_positive_xg is False


def test_repo_noxg_training_config_loads() -> None:
    path = (
        REPO_ROOT
        / "models"
        / "configs"
        / "training"
        / "football_played_better_noxg_v1.json")
    config = load_model_config(path)
    assert config.model_name == "FOOTBALL_PLAYED_BETTER_NOXG_V1"
    assert config.feature_config.require_positive_xg is False
    assert config.feature_config.exclude_positive_xg is True
    assert "home_team_xg" not in config.feature_config.required_columns
    assert "xg_diff" not in config.labeler_config.weights
