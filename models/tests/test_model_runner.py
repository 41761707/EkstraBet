"""Tests for shared model runner CLI dispatch."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from models.pipeline.core.cli import main
from models.pipeline.core.config import (
    EvaluationReport,
    PredictionResult,
    TrainingReport)

REPO_ROOT = Path(__file__).resolve().parents[2]
TRAINING_CONFIG = str(
    REPO_ROOT
    / "models"
    / "configs"
    / "training"
    / "football_played_better_v1.json")
PREDICTION_CONFIG = str(
    REPO_ROOT
    / "models"
    / "configs"
    / "prediction"
    / "football_played_better_v1.json")


def test_cli_train_dispatches_to_train() -> None:
    report = TrainingReport(
        model_name="FOOTBALL_PLAYED_BETTER_V1",
        model_version="1.0.0",
        artifact_dir="models/artifacts/dev/football_played_better_v1",
        metrics={"accuracy": 0.9},
        feature_columns=["xg_diff"],
        n_train=10,
        n_test=2)
    with patch("models.pipeline.core.cli.train", return_value=report) as mocked:
        code = main([
            "train",
            "--config",
            TRAINING_CONFIG
        ])
    assert code == 0
    mocked.assert_called_once()
    assert mocked.call_args.args[0].model_name == "FOOTBALL_PLAYED_BETTER_V1"


def test_cli_evaluate_dispatches_to_evaluate() -> None:
    report = EvaluationReport(
        model_name="FOOTBALL_PLAYED_BETTER_V1",
        model_version="1.0.0",
        metrics={"accuracy": 0.8},
        n_samples=12)
    with patch(
            "models.pipeline.core.cli.evaluate", return_value=report) as mocked:
        code = main([
            "evaluate",
            "--config",
            TRAINING_CONFIG
        ])
    assert code == 0
    mocked.assert_called_once()


def test_cli_assess_match_dispatches_and_optional_write() -> None:
    result = PredictionResult(
        match_id=123,
        model_id=6,
        probabilities={
            "home_played_better_probability": 0.4,
            "draw_probability": 0.3,
            "away_played_better_probability": 0.3
        },
        final_event_key="HOME_PLAYED_BETTER")
    with patch(
            "models.pipeline.core.cli.predict_match",
            return_value=result) as mocked_predict, patch(
            "models.pipeline.core.cli.write_match_assessment") as mocked_write:
        code = main([
            "assess-match",
            "--config",
            PREDICTION_CONFIG,
            "--match-id",
            "123",
            "--write-db"
        ])
    assert code == 0
    mocked_predict.assert_called_once()
    assert mocked_predict.call_args.args[0] == 123
    mocked_write.assert_called_once_with(result)


def test_cli_assess_batch_requires_selector() -> None:
    code = main([
        "assess-batch",
        "--config",
        PREDICTION_CONFIG
    ])
    assert code == 1
