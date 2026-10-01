"""Tests for shared model runner CLI dispatch."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from models.pipeline.core.cli import main
from models.pipeline.core.registry import RegistryError
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


HOCKEY_PREDICTION_CONFIG = (
    REPO_ROOT
    / "models"
    / "configs"
    / "prediction"
    / "hockey_ratings_poisson_v1.json")


def _hockey_ratings_model():
    from models.pipeline.training.hockey_ratings_trainer import (
        HockeyRatingsModel)

    return HockeyRatingsModel(
        attack={10: 0.12, 20: -0.04},
        defense={10: -0.02, 20: 0.03},
        home_adv=0.08,
        tie_inflation=1.12,
        p_ot_home=0.54,
        max_goals=12,
        mean_defense=0.005)


def _hockey_goalie_history():
    import pandas as pd

    return pd.DataFrame([{
        "match_id": 1,
        "game_date": pd.Timestamp("2026-01-01"),
        "home_team": 10,
        "away_team": 20,
        "home_goalie_save_pct": 0.91,
        "away_goalie_save_pct": 0.90}])


def _hockey_upcoming(*rows: tuple[int, int, int]):
    import pandas as pd

    return pd.DataFrame([
        {"match_id": match_id, "home_team": home, "away_team": away}
        for match_id, home, away in rows])


def _changing_goalie_history():
    """Two starts per club, so the carried average is not the last save."""
    import pandas as pd

    return pd.DataFrame([
        {
            "match_id": 1,
            "game_date": pd.Timestamp("2026-01-01"),
            "home_team": 10,
            "away_team": 20,
            "home_goalie_save_pct": 0.80,
            "away_goalie_save_pct": 0.70
        },
        {
            "match_id": 2,
            "game_date": pd.Timestamp("2026-01-02"),
            "home_team": 10,
            "away_team": 20,
            "home_goalie_save_pct": 0.95,
            "away_goalie_save_pct": 0.92
        }])


def _ratings_model_only(name: str) -> int:
    """Keep predict-hockey tests on the ratings artifact they mock."""
    if name != "HOCKEY_RATINGS_POISSON_V1":
        raise RegistryError(f"{name} is inactive in this test")
    return 21


def _run_predict_hockey(
        argv: list[str],
        predictable: list[int],
        upcoming,
        write,
        history=None,
        model=None,
        resolver=None,
        rosters=None,
        stats=None):
    from contextlib import ExitStack

    goalie_history = (
        _hockey_goalie_history() if history is None else history)
    artifact = _hockey_ratings_model() if model is None else model
    with ExitStack() as stack:
        selected = stack.enter_context(patch(
            "models.pipeline.core.cli.select_predictable_matches",
            return_value=predictable))
        stack.enter_context(patch(
            "models.pipeline.core.cli.fetch_upcoming_hockey_matches",
            return_value=upcoming))
        stack.enter_context(patch(
            "models.pipeline.core.cli.resolve_model_id",
            side_effect=_ratings_model_only))
        stack.enter_context(patch(
            "models.pipeline.core.cli.load_model_artifact",
            return_value=artifact))
        stack.enter_context(patch(
            "models.pipeline.core.cli.load_training_frame",
            return_value=goalie_history))
        writer = stack.enter_context(patch(
            "models.pipeline.core.cli.write_predictions",
            side_effect=write))
        if resolver is not None:
            stack.enter_context(patch(
                "models.pipeline.core.cli._resolve_club_lineup",
                side_effect=resolver))
        else:
            stack.enter_context(patch(
                "models.pipeline.core.cli._lineup_stage_resolver",
                return_value=None))
        if rosters is not None:
            stack.enter_context(patch(
                "models.pipeline.core.cli.fetch_hockey_match_rosters",
                return_value=rosters))
        if stats is not None:
            stack.enter_context(patch(
                "models.pipeline.core.cli.fetch_hockey_player_stats",
                return_value=stats))
        code = main(argv)
    return code, selected, writer


def test_cli_predict_hockey_writes_18_predictions_and_9_finals(
        capsys: pytest.CaptureFixture[str]) -> None:
    from models.pipeline.core.config import load_model_config
    from models.pipeline.prediction.hockey_markets import (
        HOCKEY_MARKET_FAMILIES)

    captured: list = []

    def _capture(rows, conn=None, *, values_are_percent=False):
        assert values_are_percent is True
        materialized = list(rows)
        captured.extend(materialized)
        return len(materialized)

    code, _selected, writer = _run_predict_hockey(
        [
            "predict-hockey",
            "--league-id",
            "45",
            "--write-db",
            "--select-finals"],
        [501],
        _hockey_upcoming((501, 10, 20)),
        _capture)
    assert code == 0
    writer.assert_called_once()
    assert len(captured) == 18
    assert sum(row.is_final for row in captured) == 9
    assert {row.event_id for row in captured} == set(range(234, 252))
    assert all(0.0 <= row.value <= 100.0 for row in captured)
    config = load_model_config(HOCKEY_PREDICTION_CONFIG)
    by_event = {row.event_id: row for row in captured}
    for keys in HOCKEY_MARKET_FAMILIES.values():
        left = by_event[int(config.events[keys[0]])]
        right = by_event[int(config.events[keys[1]])]
        assert left.value + right.value == pytest.approx(100.0, abs=1e-6)
        assert left.is_final != right.is_final
    payload = json.loads(capsys.readouterr().out)
    match = payload["result"]["models"][0]["matches"][0]
    assert payload["result"]["dry_run"] is False
    assert match["predictions"] == 18
    assert match["finals"] == 9
    assert match["written"] == 18


def test_cli_predict_hockey_fallback_keeps_uncorrected_rates(
        capsys: pytest.CaptureFixture[str],
        caplog: pytest.LogCaptureFixture) -> None:
    """No lineup uses team-average save, so the goalie factor stays 1.

    Clubs 10 and 20 have a carried average that is not their last
    start. Clubs 30 and 40 have no save history. Both matches must
    stay, and both must match a distribution with no goalie correction.
    """
    from models.pipeline.core.config import load_model_config
    from models.pipeline.prediction.hockey_markets import (
        derive_hockey_markets)
    from models.pipeline.training.hockey_ratings_trainer import (
        hockey_params_from_config)
    from models.pipeline.training.hockey_ratings_trainer import (
        latest_team_save_rates)

    history = _changing_goalie_history()
    config = load_model_config(HOCKEY_PREDICTION_CONFIG)
    half_life = hockey_params_from_config(config).goalie_half_life_days
    carried = latest_team_save_rates(history, half_life)
    model = _hockey_ratings_model()
    # Ostatni start różni się od średniej — zła korekta ruszyłaby rynki.
    assert carried[10] != pytest.approx(0.95)
    assert carried[20] != pytest.approx(0.92)
    assert 30 not in carried
    assert 40 not in carried
    plain = derive_hockey_markets(model.score_distribution(10, 20))
    wrong = derive_hockey_markets(model.score_distribution(
        10,
        20,
        home_starter_save=0.95,
        away_starter_save=0.92,
        home_team_save=carried[10],
        away_team_save=carried[20]))
    assert plain["ml_home"] != pytest.approx(wrong["ml_home"])

    with caplog.at_level(
            logging.WARNING, logger="models.pipeline.core.cli"):
        code, _selected, writer = _run_predict_hockey(
            ["predict-hockey", "--league-id", "45"],
            [501, 502],
            _hockey_upcoming((501, 10, 20), (502, 30, 40)),
            MagicMock(),
            history=history)
    assert code == 0
    writer.assert_not_called()
    payload = json.loads(capsys.readouterr().out)
    reported = {
        item["match_id"]: item
        for item in payload["result"]["models"][0]["matches"]}
    assert set(reported) == {501, 502}
    _assert_markets_match(reported[501]["markets"], plain)
    unknown = derive_hockey_markets(model.score_distribution(30, 40))
    _assert_markets_match(reported[502]["markets"], unknown)
    warnings = [
        record.getMessage()
        for record in caplog.records
        if record.levelno >= logging.WARNING]
    assert any("match 501" in message for message in warnings)
    assert any("match 502" in message for message in warnings)
    assert any(
        "team-average goalie save percentage" in message
        for message in warnings)


def test_cli_predict_hockey_applies_two_resolved_lineups(
        capsys: pytest.CaptureFixture[str],
        caplog: pytest.LogCaptureFixture) -> None:
    """Both clubs dressed moves the price off the team-average rate."""
    home, away, model, rosters, stats, moment = _lineup_case()
    from models.pipeline.features.hockey.lineup_strength import (
        ratios_for_lineups)
    from models.pipeline.prediction.hockey_markets import (
        derive_hockey_markets)

    ratios = ratios_for_lineups(
        home, away, rosters, stats, moment, 12, 10)
    assert ratios is not None
    assert 0.0 < ratios["home_off_ratio"] < 1.0
    corrected = derive_hockey_markets(model.score_distribution(
        30,
        40,
        home_off_ratio=ratios["home_off_ratio"],
        away_off_ratio=ratios["away_off_ratio"],
        home_def_ratio=ratios["home_def_ratio"],
        away_def_ratio=ratios["away_def_ratio"]))
    plain = derive_hockey_markets(model.score_distribution(30, 40))
    assert corrected["ml_home"] != pytest.approx(plain["ml_home"])

    def _resolver(match_id, team_id, stage):
        assert stage == "initial"
        if match_id == 501 and team_id == 30:
            return home
        if match_id == 501 and team_id == 40:
            return away
        return None

    reported, warnings = _predict_lineup_matches(
        capsys,
        caplog,
        [501],
        _resolver,
        model,
        rosters,
        stats,
        moment)
    assert reported[501]["lineup_fallback"] is False
    _assert_markets_match(reported[501]["markets"], corrected)
    assert all("match 501" not in message for message in warnings)


def test_cli_predict_hockey_applies_one_resolved_side(
        capsys: pytest.CaptureFixture[str],
        caplog: pytest.LogCaptureFixture) -> None:
    """A missing club stays at ratio 1. The dressed club still moves."""
    home, _away, model, rosters, stats, moment = _lineup_case()
    from models.pipeline.features.hockey.lineup_strength import (
        ratios_for_lineups)
    from models.pipeline.prediction.hockey_markets import (
        derive_hockey_markets)

    one_side = ratios_for_lineups(
        home, None, rosters, stats, moment, 12, 10)
    assert one_side is not None

    def _resolver(match_id, team_id, stage):
        assert stage == "initial"
        if match_id == 503 and team_id == 30:
            return home
        return None

    reported, warnings = _predict_lineup_matches(
        capsys,
        caplog,
        [503],
        _resolver,
        model,
        rosters,
        stats,
        moment)
    assert reported[503]["lineup_fallback"] is False
    assert reported[503]["home_off_ratio"] == pytest.approx(
        one_side["home_off_ratio"])
    assert reported[503]["away_off_ratio"] == pytest.approx(1.0)
    assert reported[503]["away_def_ratio"] == pytest.approx(1.0)
    partial = derive_hockey_markets(model.score_distribution(
        30,
        40,
        home_off_ratio=one_side["home_off_ratio"],
        away_off_ratio=1.0,
        home_def_ratio=one_side["home_def_ratio"],
        away_def_ratio=1.0))
    _assert_markets_match(reported[503]["markets"], partial)
    assert any(
        "match 503" in message and "team 40" in message
        for message in warnings)


def test_cli_predict_hockey_scores_matches_in_date_order(
        capsys: pytest.CaptureFixture[str]) -> None:
    from datetime import datetime

    import pandas as pd

    upcoming = pd.DataFrame([
        {
            "match_id": 501,
            "home_team": 10,
            "away_team": 20,
            "game_date": datetime(2025, 10, 10),
            "season": 12
        },
        {
            "match_id": 502,
            "home_team": 30,
            "away_team": 40,
            "game_date": datetime(2025, 10, 8),
            "season": 12
        }])
    code, _selected, writer = _run_predict_hockey(
        ["predict-hockey", "--league-id", "45"],
        [501, 502],
        upcoming,
        MagicMock())
    assert code == 0
    writer.assert_not_called()
    payload = json.loads(capsys.readouterr().out)
    order = [
        item["match_id"]
        for item in payload["result"]["models"][0]["matches"]]
    assert order == [502, 501]


def _lineup_case():
    from datetime import datetime

    import pandas as pd

    from models.pipeline.features.hockey.lineup_strength import (
        ProbableLineup)
    from models.pipeline.training.hockey_ratings_trainer import (
        HockeyRatingsModel)

    start = datetime(2025, 10, 1)
    later = datetime(2025, 10, 3)
    moment = datetime(2025, 10, 10)
    rosters = pd.DataFrame([
        _club_roster(1, 100, 30, "C", 1, start),
        _club_roster(1, 101, 30, "C", 4, start),
        _club_roster(2, 100, 30, "C", 1, later),
        _club_roster(2, 101, 30, "C", 4, later)])
    stats = pd.DataFrame([
        _club_box(1, 100, 30, 3),
        _club_box(1, 101, 30, 1),
        _club_box(2, 100, 30, 2),
        _club_box(2, 101, 30, 1)])
    home = ProbableLineup(
        match_id=501,
        team_id=30,
        players=[_projected(101, "C", 4)])
    away = ProbableLineup(
        match_id=501,
        team_id=40,
        players=[_projected(200, "C", 1)])
    model = HockeyRatingsModel(
        attack={30: 0.0, 40: 0.0},
        defense={30: 0.0, 40: 0.0},
        home_adv=0.08,
        tie_inflation=1.12,
        p_ot_home=0.54,
        max_goals=12,
        mean_defense=0.0,
        beta_off=1.0,
        beta_def=0.0)
    return home, away, model, rosters, stats, moment


def _predict_lineup_matches(
        capsys,
        caplog,
        match_ids,
        resolver,
        model,
        rosters,
        stats,
        moment):
    import pandas as pd

    upcoming = pd.DataFrame([
        {
            "match_id": match_id,
            "home_team": 30,
            "away_team": 40,
            "game_date": moment,
            "season": 12
        }
        for match_id in match_ids])
    with caplog.at_level(
            logging.WARNING, logger="models.pipeline.core.cli"):
        code, _selected, writer = _run_predict_hockey(
            ["predict-hockey", "--league-id", "45"],
            match_ids,
            upcoming,
            MagicMock(),
            model=model,
            resolver=resolver,
            rosters=rosters,
            stats=stats)
    assert code == 0
    writer.assert_not_called()
    payload = json.loads(capsys.readouterr().out)
    reported = {
        item["match_id"]: item
        for item in payload["result"]["models"][0]["matches"]}
    warnings = [
        record.getMessage()
        for record in caplog.records
        if record.levelno >= logging.WARNING]
    return reported, warnings


def _projected(player_id: int, position: str, line: int):
    from models.pipeline.features.hockey.lineup_strength import (
        ProbableLineupPlayer)

    return ProbableLineupPlayer(
        player_id=player_id,
        position=position,
        line=line,
        pp_unit=None,
        is_starting_goalie=None,
        confidence=1.0,
        source="MODEL")


def _club_roster(
        match_id: int,
        player_id: int,
        team_id: int,
        position: str,
        line: int,
        when) -> dict[str, object]:
    return {
        "match_id": match_id,
        "player_id": player_id,
        "team_id": team_id,
        "position": position,
        "line": line,
        "game_date": when,
        "season": 12}


def _club_box(
        match_id: int,
        player_id: int,
        team_id: int,
        points: int) -> dict[str, object]:
    return {
        "match_id": match_id,
        "player_id": player_id,
        "team_id": team_id,
        "points": points,
        "sog": 2,
        "plus_minus": 0,
        "toi_seconds": 1200}


def _assert_markets_match(
        actual: dict[str, float],
        expected: dict[str, float]) -> None:
    assert set(actual) == set(expected)
    for key, value in expected.items():
        assert actual[key] == pytest.approx(value)


def test_cli_predict_hockey_dry_run_does_not_write(
        capsys: pytest.CaptureFixture[str]) -> None:
    code, _selected, writer = _run_predict_hockey(
        [
            "predict-hockey",
            "--league-id",
            "45",
            "--select-finals"],
        [501],
        _hockey_upcoming((501, 10, 20)),
        MagicMock())
    assert code == 0
    writer.assert_not_called()
    payload = json.loads(capsys.readouterr().out)
    match = payload["result"]["models"][0]["matches"][0]
    assert payload["result"]["dry_run"] is True
    assert match["predictions"] == 18
    assert match["finals"] == 9
    assert match["written"] == 0


def test_cli_predict_hockey_filters_match_ids_through_predictable(
        capsys: pytest.CaptureFixture[str]) -> None:
    captured: list = []

    def _capture(rows, conn=None, *, values_are_percent=False):
        captured.extend(list(rows))
        return len(captured)

    code, selected, _writer = _run_predict_hockey(
        [
            "predict-hockey",
            "--league-id",
            "45",
            "--match-ids",
            "502,999",
            "--write-db",
            "--select-finals"],
        [501, 502],
        _hockey_upcoming((501, 10, 20), (502, 30, 40)),
        _capture)
    assert code == 0
    assert selected.call_args.args[0] == 45
    payload = json.loads(capsys.readouterr().out)
    assert payload["result"]["match_ids"] == [502]
    assert payload["result"]["ignored_match_ids"] == [999]
    assert len(captured) == 18
    assert {row.match_id for row in captured} == {502}


def _gbm_model_only(name: str) -> int:
    """Keep this test on the GBM predict path."""
    if name != "HOCKEY_GOALS_GBM_V1":
        raise RegistryError(f"{name} is inactive in this test")
    return 12


def _run_predict_hockey_gbm(
        argv: list[str],
        write,
        lineup=None,
        *,
        resolver_available: bool = True):
    from contextlib import ExitStack

    from models.pipeline.prediction.hockey_markets import (
        build_score_distribution)

    model = MagicMock()
    model.score_distribution.side_effect = (
        lambda features: build_score_distribution(2.8, 2.4, 1.1, 0.52, 8))
    features = _gbm_feature_frame(501)
    with ExitStack() as stack:
        stack.enter_context(patch(
            "models.pipeline.core.cli.select_predictable_matches",
            return_value=[501]))
        stack.enter_context(patch(
            "models.pipeline.core.cli.fetch_upcoming_hockey_matches",
            return_value=_hockey_upcoming((501, 10, 20))))
        stack.enter_context(patch(
            "models.pipeline.core.cli.resolve_model_id",
            side_effect=_gbm_model_only))
        stack.enter_context(patch(
            "models.pipeline.core.cli._artifact_recommends_inactive",
            return_value=False))
        stack.enter_context(patch(
            "models.pipeline.core.cli._load_hockey_gbm_model",
            return_value=model))
        stack.enter_context(patch(
            "models.pipeline.core.cli.load_hockey_team_feature_frame",
            return_value=features))
        writer = stack.enter_context(patch(
            "models.pipeline.core.cli.write_predictions",
            side_effect=write))
        if resolver_available:
            stack.enter_context(patch(
                "models.pipeline.core.cli._lineup_stage_resolver",
                return_value=lambda *_args, **_kwargs: lineup))
        else:
            stack.enter_context(patch(
                "models.pipeline.core.cli._lineup_stage_resolver",
                return_value=None))
        code = main(argv)
    return code, writer


def _gbm_feature_frame(match_id: int):
    import pandas as pd

    from models.pipeline.features.hockey.team_features import (
        HOCKEY_GBM_FEATURE_COLUMNS)

    row = {column: 0.0 for column in HOCKEY_GBM_FEATURE_COLUMNS}
    row["match_id"] = match_id
    return pd.DataFrame([row])


def test_cli_predict_hockey_gbm_writes_markets_and_falls_back(
        capsys: pytest.CaptureFixture[str],
        caplog: pytest.LogCaptureFixture) -> None:
    from models.pipeline.core.config import load_model_config
    from models.pipeline.prediction.hockey_markets import (
        HOCKEY_MARKET_FAMILIES)

    captured: list = []

    def _capture(rows, conn=None, *, values_are_percent=False):
        assert values_are_percent is True
        materialized = list(rows)
        captured.extend(materialized)
        return len(materialized)

    with caplog.at_level(
            logging.WARNING, logger="models.pipeline.core.cli"):
        code, writer = _run_predict_hockey_gbm(
            [
                "predict-hockey",
                "--league-id",
                "45",
                "--write-db",
                "--select-finals"],
            _capture)
    assert code == 0
    writer.assert_called_once()
    assert len(captured) == 18
    assert sum(row.is_final for row in captured) == 9
    assert all(0.0 <= row.value <= 100.0 for row in captured)
    config = load_model_config(
        REPO_ROOT / "models" / "configs" / "prediction"
        / "hockey_goals_gbm_v1.json")
    by_event = {row.event_id: row for row in captured}
    for keys in HOCKEY_MARKET_FAMILIES.values():
        left = by_event[int(config.events[keys[0]])]
        right = by_event[int(config.events[keys[1]])]
        assert left.value + right.value == pytest.approx(100.0, abs=1e-6)
        assert left.is_final != right.is_final
    payload = json.loads(capsys.readouterr().out)
    match = payload["result"]["models"][0]["matches"][0]
    assert match["predictions"] == 18
    assert match["finals"] == 9
    assert match["written"] == 18
    assert match["lineup_fallback"] is True
    assert "team-average" in caplog.text


def test_cli_predict_hockey_gbm_uses_a_resolved_lineup(
        capsys: pytest.CaptureFixture[str]) -> None:
    code, writer = _run_predict_hockey_gbm(
        ["predict-hockey", "--league-id", "45"],
        MagicMock(),
        lineup=object())
    assert code == 0
    writer.assert_not_called()
    payload = json.loads(capsys.readouterr().out)
    match = payload["result"]["models"][0]["matches"][0]
    assert match["predictions"] == 18
    assert match["lineup_fallback"] is False


def test_cli_predict_hockey_gbm_scores_without_a_lineup_module(
        capsys: pytest.CaptureFixture[str]) -> None:
    def _write(rows, conn=None, *, values_are_percent=False):
        return len(list(rows))

    code, writer = _run_predict_hockey_gbm(
        ["predict-hockey", "--league-id", "45", "--write-db"],
        _write,
        resolver_available=False)
    assert code == 0
    writer.assert_called()
    payload = json.loads(capsys.readouterr().out)
    match = payload["result"]["models"][0]["matches"][0]
    assert match["lineup_fallback"] is True


def test_missing_lineup_module_keeps_the_gbm() -> None:
    from models.pipeline.core import cli

    def _both(name: str) -> int:
        if name == "HOCKEY_GOALS_GBM_V1":
            return 12
        if name == "HOCKEY_RATINGS_POISSON_V1":
            return 21
        raise RegistryError(name)

    with patch(
            "models.pipeline.core.cli.resolve_model_id",
            side_effect=_both), patch(
            "models.pipeline.core.cli._artifact_recommends_inactive",
            return_value=False), patch(
            "models.pipeline.core.cli._lineup_stage_resolver",
            return_value=None):
        loaded = cli._active_hockey_configs()
    names = [config.model_name for config, _model_id in loaded]
    assert "HOCKEY_GOALS_GBM_V1" in names
    assert "HOCKEY_RATINGS_POISSON_V1" in names


def test_predict_hockey_skips_recommended_inactive() -> None:
    from models.pipeline.core import cli

    def _meta(path: object) -> dict[str, int]:
        if "hockey_goals_gbm" in str(path):
            return {"recommended_active": 0}
        return {}

    with patch(
            "models.pipeline.core.cli.resolve_model_id",
            return_value=12), patch(
            "models.pipeline.core.cli.load_meta",
            side_effect=_meta):
        loaded = cli._active_hockey_configs()
    names = [config.model_name for config, _model_id in loaded]
    assert "HOCKEY_GOALS_GBM_V1" not in names
    assert "HOCKEY_RATINGS_POISSON_V1" in names


def test_cli_predict_hockey_requires_an_active_model(
        capsys: pytest.CaptureFixture[str]) -> None:
    from models.pipeline.core.registry import RegistryError

    with patch(
            "models.pipeline.core.cli.resolve_model_id",
            side_effect=RegistryError("inactive")):
        code = main(["predict-hockey", "--league-id", "45"])
    assert code == 1
    assert "No active hockey team-model configs" in capsys.readouterr().err


def test_cli_predict_hockey_requires_league_id() -> None:
    with pytest.raises(SystemExit):
        main(["predict-hockey"])
