"""Tests for shared model runner CLI dispatch."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

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


GOALS_PREDICTION_CONFIG = str(
    REPO_ROOT
    / "models"
    / "configs"
    / "prediction"
    / "football_goals_poisson_v1.json")


def test_cli_simulate_season_parser_and_dispatch() -> None:
    payload = {
        "run_id": 9,
        "league_id": 1,
        "season_id": 13,
        "mode": "from_now",
        "n_trials": 100,
        "seed": 42,
        "teams": 2
    }
    with patch(
            "models.pipeline.core.cli.run_simulate_season",
            return_value=payload) as mocked:
        code = main([
            "simulate-season",
            "--goals-config",
            GOALS_PREDICTION_CONFIG,
            "--league-id",
            "1",
            "--season-id",
            "13",
            "--mode",
            "from_now",
            "--trials",
            "100",
            "--seed",
            "42"
        ])
    assert code == 0
    mocked.assert_called_once()
    args = mocked.call_args.args[0]
    assert args.league_id == 1
    assert args.season_id == 13
    assert args.mode == "from_now"
    assert args.trials == 100
    assert args.seed == 42


def test_cli_simulate_season_rejects_invalid_mode() -> None:
    with pytest.raises(SystemExit):
        main([
            "simulate-season",
            "--goals-config",
            GOALS_PREDICTION_CONFIG,
            "--league-id",
            "1",
            "--season-id",
            "13",
            "--mode",
            "invalid"
        ])


def test_cli_simulate_season_marks_failed_on_error() -> None:
    from models.pipeline.core.config import FutureEventsRunConfig
    from models.pipeline.simulation.config import SeasonSimulationConfig
    from models.pipeline.simulation.config import SimulationMode

    goals_config = FutureEventsRunConfig.model_validate({
        "model_name": "FOOTBALL_GOALS_POISSON_V1",
        "sport_id": 1,
        "task_type": "goals_poisson",
        "model_version": "1.0.0",
        "artifact_dir": str(
            REPO_ROOT
            / "models"
            / "artifacts"
            / "release"
            / "football_goals_poisson_v1"),
        "feature_builder": "FutureEventsFeatureBuilder",
        "labeler": "FootballGoalsPoissonLabeler",
        "trainer": "PoissonTrainer",
        "output_columns": ["lambda_home", "lambda_away"],
        "feature_config": {}
    })
    fake_predictor = MagicMock()
    fake_simulator = MagicMock()
    fake_simulator.run.side_effect = ValueError("incomplete schedule")

    with patch(
            "models.pipeline.core.cli.load_model_config",
            return_value=goals_config), patch(
            "models.pipeline.core.cli.compute_artifact_hash",
            return_value="hash"), patch(
            "models.pipeline.core.cli.start_projection_run",
            return_value=44) as start_mock, patch(
            "models.pipeline.core.cli.FutureEventsPredictor",
            return_value=fake_predictor), patch(
            "models.pipeline.core.cli.DynamicSeasonSimulator",
            return_value=fake_simulator), patch(
            "models.pipeline.core.cli.fail_projection_run") as fail_mock, patch(
            "models.pipeline.core.cli.write_projection") as write_mock:
        code = main([
            "simulate-season",
            "--goals-config",
            GOALS_PREDICTION_CONFIG,
            "--league-id",
            "1",
            "--season-id",
            "13",
            "--mode",
            "from_season_start",
            "--trials",
            "100"
        ])
    assert code == 1
    start_mock.assert_called_once()
    fail_mock.assert_called_once()
    assert fail_mock.call_args.args[0] == 44
    assert "incomplete schedule" in fail_mock.call_args.args[1]
    write_mock.assert_not_called()
    run_config = fake_simulator.run.call_args.args[0]
    assert isinstance(run_config, SeasonSimulationConfig)
    assert run_config.mode is SimulationMode.FROM_SEASON_START


def test_cli_simulate_season_preserves_original_error_if_fail_write_breaks(
        capsys: pytest.CaptureFixture[str]
) -> None:
    from models.pipeline.core.config import FutureEventsRunConfig

    goals_config = FutureEventsRunConfig.model_validate({
        "model_name": "FOOTBALL_GOALS_POISSON_V1",
        "sport_id": 1,
        "task_type": "goals_poisson",
        "model_version": "1.0.0",
        "artifact_dir": str(
            REPO_ROOT
            / "models"
            / "artifacts"
            / "release"
            / "football_goals_poisson_v1"),
        "feature_builder": "FutureEventsFeatureBuilder",
        "labeler": "FootballGoalsPoissonLabeler",
        "trainer": "PoissonTrainer",
        "output_columns": ["lambda_home", "lambda_away"],
        "feature_config": {}
    })
    fake_simulator = MagicMock()
    fake_simulator.run.side_effect = ValueError("incomplete schedule")

    with patch(
            "models.pipeline.core.cli.load_model_config",
            return_value=goals_config), patch(
            "models.pipeline.core.cli.compute_artifact_hash",
            return_value="hash"), patch(
            "models.pipeline.core.cli.start_projection_run",
            return_value=44), patch(
            "models.pipeline.core.cli.FutureEventsPredictor",
            return_value=MagicMock()), patch(
            "models.pipeline.core.cli.DynamicSeasonSimulator",
            return_value=fake_simulator), patch(
            "models.pipeline.core.cli.fail_projection_run",
            side_effect=RuntimeError("db down")), patch(
            "models.pipeline.core.cli.write_projection") as write_mock:
        code = main([
            "simulate-season",
            "--goals-config",
            GOALS_PREDICTION_CONFIG,
            "--league-id",
            "1",
            "--season-id",
            "13",
            "--mode",
            "from_now",
            "--trials",
            "100"
        ])
    assert code == 1
    write_mock.assert_not_called()
    err = capsys.readouterr().err
    assert "incomplete schedule" in err
    assert "db down" not in err


def test_cli_simulate_season_success_writes_projection() -> None:
    from models.pipeline.core.config import FutureEventsRunConfig
    from models.pipeline.simulation.aggregation import TeamSeasonProjection
    from models.pipeline.simulation.config import SeasonSimulationConfig
    from models.pipeline.simulation.config import SimulationMode
    from models.pipeline.simulation.season_simulator import (
        SeasonSimulationResult)

    goals_config = FutureEventsRunConfig.model_validate({
        "model_name": "FOOTBALL_GOALS_POISSON_V1",
        "sport_id": 1,
        "task_type": "goals_poisson",
        "model_version": "1.0.0",
        "artifact_dir": str(
            REPO_ROOT
            / "models"
            / "artifacts"
            / "release"
            / "football_goals_poisson_v1"),
        "feature_builder": "FutureEventsFeatureBuilder",
        "labeler": "FootballGoalsPoissonLabeler",
        "trainer": "PoissonTrainer",
        "output_columns": ["lambda_home", "lambda_away"],
        "feature_config": {}
    })
    result = SeasonSimulationResult(
        config=SeasonSimulationConfig(
            league_id=1,
            season_id=13,
            mode=SimulationMode.FROM_NOW,
            n_trials=100,
            seed=42),
        projections=[TeamSeasonProjection(
            team_id=1,
            current_position=1,
            current_points=3,
            expected_position=1.0,
            most_likely_position=1,
            position_min=1,
            position_max=1,
            expected_points=10.0,
            points_variance=0.0,
            points_stddev=0.0,
            points_p05=10.0,
            points_p50=10.0,
            points_p95=10.0,
            points_min=10.0,
            points_max=10.0,
            expected_goal_difference=1.0,
            position_probabilities=[1.0])],
        input_fingerprint="fp-success",
        fixed_matches=2,
        simulated_matches=4,
        processed_schedule_ids=(1, 2, 3, 4, 5, 6))
    fake_simulator = MagicMock()
    fake_simulator.run.return_value = result

    with patch(
            "models.pipeline.core.cli.load_model_config",
            return_value=goals_config), patch(
            "models.pipeline.core.cli.compute_artifact_hash",
            return_value="hash-ok"), patch(
            "models.pipeline.core.cli.start_projection_run",
            return_value=91) as start_mock, patch(
            "models.pipeline.core.cli.FutureEventsPredictor",
            return_value=MagicMock()), patch(
            "models.pipeline.core.cli.DynamicSeasonSimulator",
            return_value=fake_simulator), patch(
            "models.pipeline.core.cli.fail_projection_run") as fail_mock, patch(
            "models.pipeline.core.cli.write_projection",
            return_value=91) as write_mock:
        code = main([
            "simulate-season",
            "--goals-config",
            GOALS_PREDICTION_CONFIG,
            "--league-id",
            "1",
            "--season-id",
            "13",
            "--mode",
            "from_now",
            "--trials",
            "100",
            "--seed",
            "42"
        ])
    assert code == 0
    start_mock.assert_called_once()
    fail_mock.assert_not_called()
    write_mock.assert_called_once()
    write_args = write_mock.call_args
    assert write_args.args[0] is result
    assert write_args.args[1] == "fp-success"
    assert write_args.kwargs["run_id"] == 91
    assert write_args.kwargs["model_name"] == "FOOTBALL_GOALS_POISSON_V1"
    assert write_args.kwargs["artifact_hash"] == "hash-ok"
    run_kwargs = fake_simulator.run.call_args.kwargs
    assert run_kwargs["round_progress"] is not None
    run_config = fake_simulator.run.call_args.args[0]
    assert run_config.mode is SimulationMode.FROM_NOW


def test_cli_simulate_season_no_progress_disables_tqdm() -> None:
    from models.pipeline.core.config import FutureEventsRunConfig
    from models.pipeline.simulation.aggregation import TeamSeasonProjection
    from models.pipeline.simulation.config import SeasonSimulationConfig
    from models.pipeline.simulation.config import SimulationMode
    from models.pipeline.simulation.season_simulator import (
        SeasonSimulationResult)

    goals_config = FutureEventsRunConfig.model_validate({
        "model_name": "FOOTBALL_GOALS_POISSON_V1",
        "sport_id": 1,
        "task_type": "goals_poisson",
        "model_version": "1.0.0",
        "artifact_dir": str(
            REPO_ROOT
            / "models"
            / "artifacts"
            / "release"
            / "football_goals_poisson_v1"),
        "feature_builder": "FutureEventsFeatureBuilder",
        "labeler": "FootballGoalsPoissonLabeler",
        "trainer": "PoissonTrainer",
        "output_columns": ["lambda_home", "lambda_away"],
        "feature_config": {}
    })
    result = SeasonSimulationResult(
        config=SeasonSimulationConfig(
            league_id=1,
            season_id=13,
            mode=SimulationMode.FROM_NOW,
            n_trials=100,
            seed=42),
        projections=[TeamSeasonProjection(
            team_id=1,
            current_position=1,
            current_points=0,
            expected_position=1.0,
            most_likely_position=1,
            position_min=1,
            position_max=1,
            expected_points=1.0,
            points_variance=0.0,
            points_stddev=0.0,
            points_p05=1.0,
            points_p50=1.0,
            points_p95=1.0,
            points_min=1.0,
            points_max=1.0,
            expected_goal_difference=0.0,
            position_probabilities=[1.0])],
        input_fingerprint="fp",
        fixed_matches=0,
        simulated_matches=1,
        processed_schedule_ids=(1,))
    fake_simulator = MagicMock()
    fake_simulator.run.return_value = result

    with patch(
            "models.pipeline.core.cli.load_model_config",
            return_value=goals_config), patch(
            "models.pipeline.core.cli.compute_artifact_hash",
            return_value="hash"), patch(
            "models.pipeline.core.cli.start_projection_run",
            return_value=1), patch(
            "models.pipeline.core.cli.FutureEventsPredictor",
            return_value=MagicMock()), patch(
            "models.pipeline.core.cli.DynamicSeasonSimulator",
            return_value=fake_simulator), patch(
            "models.pipeline.core.cli.write_projection",
            return_value=1):
        code = main([
            "simulate-season",
            "--goals-config",
            GOALS_PREDICTION_CONFIG,
            "--league-id",
            "1",
            "--season-id",
            "13",
            "--mode",
            "from_now",
            "--trials",
            "100",
            "--no-progress"
        ])
    assert code == 0
    assert fake_simulator.run.call_args.kwargs["round_progress"] is None
