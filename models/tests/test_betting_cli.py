"""Parser and command tests for the EB-18 model runner commands."""

from __future__ import annotations

import io
import json
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from backend.config import REPO_ROOT
from models.pipeline.betting import commands
from models.pipeline.betting.config import load_betting_strategy_config
from models.pipeline.betting.domain import BettingCandidate
from models.pipeline.betting.domain import SelectionDecision
from models.pipeline.betting.predictor import BettingMetaPredictor
from models.pipeline.betting.recommendation import PredictReport
from models.pipeline.core.cli import build_parser
from models.pipeline.core.cli import main
from models.pipeline.data.betting_candidate_repository import (
    BETTING_CANDIDATE_COLUMNS)


_TRAINING = (
    REPO_ROOT / "models" / "configs" / "training"
    / "football_betting_meta_v1.json")
_STRATEGY = (
    REPO_ROOT / "models" / "configs" / "prediction"
    / "football_betting_strategy_v1.json")
_SETTLEMENT = (
    "result",
    "home_team_goals",
    "away_team_goals",
    "event_name")


def _choices() -> dict[str, object]:
    parser = build_parser()
    action = next(
        item
        for item in parser._actions
        if getattr(item, "choices", None))
    return action.choices


def _history(matches: int = 10) -> pd.DataFrame:
    rows = []
    for match_id in range(1, matches + 1):
        rows.append({
            "prediction_id": match_id,
            "odds_id": 100 + match_id,
            "match_id": match_id,
            "event_id": 1,
            "model_id": 8,
            "bookmaker_id": 4,
            "league_id": 12,
            "kickoff": datetime(2026, 1, match_id, 18, 0),
            "value_pct": 55.0,
            "odds": 2.0,
            "devig_probability": None,
            "result": "1",
            "home_team_goals": 2,
            "away_team_goals": 1,
            "event_name": "1"})
    return pd.DataFrame(rows)


def _empty_frame() -> pd.DataFrame:
    columns = list(BETTING_CANDIDATE_COLUMNS) + list(_SETTLEMENT)
    return pd.DataFrame(columns=columns)


def _run(argv: list[str]) -> tuple[int, dict[str, object], str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(argv)
    raw = stdout.getvalue() if code == 0 else stderr.getvalue()
    return code, json.loads(raw), raw


def _dataset_argv() -> list[str]:
    return [
        "build-betting-dataset",
        "--training-config",
        str(_TRAINING),
        "--strategy-config",
        str(_STRATEGY)]


def _artifact_argv(command: str, artifact: Path) -> list[str]:
    return [
        command,
        "--training-config",
        str(_TRAINING),
        "--strategy-config",
        str(_STRATEGY),
        "--artifact-dir",
        str(artifact)]


def _fake_decide(
        self: BettingMetaPredictor,
        frame: pd.DataFrame) -> list[SelectionDecision]:
    del self
    decisions = []
    for row in frame.itertuples(index=False):
        kickoff = row.kickoff
        if not isinstance(kickoff, datetime):
            kickoff = pd.Timestamp(kickoff).to_pydatetime()
        decisions.append(SelectionDecision(
            decision="no_bet",
            candidate=BettingCandidate(
                prediction_id=int(row.prediction_id),
                odds_id=int(row.odds_id),
                match_id=int(row.match_id),
                event_id=int(row.event_id),
                model_id=int(row.model_id),
                bookmaker_id=int(row.bookmaker_id),
                league_id=int(row.league_id),
                kickoff=kickoff,
                value_pct=float(row.value_pct),
                odds=float(row.odds)),
            calibrated_probability=0.4,
            reason="mock score"))
    return decisions


def test_parser_accepts_the_five_betting_commands(tmp_path: Path) -> None:
    choices = _choices()
    for name in (
            "build-betting-dataset",
            "train-betting-meta",
            "evaluate-betting-meta",
            "backtest-betting-strategy",
            "predict-betting-meta"):
        assert name in choices
    assert "settle-betting-strategy" not in choices
    assert "snapshot-odds" not in choices
    dataset = build_parser().parse_args(_dataset_argv())
    assert dataset.training_config == _TRAINING
    assert dataset.strategy_config == _STRATEGY
    assert dataset.verbose is False
    trained = build_parser().parse_args(
        _artifact_argv("train-betting-meta", tmp_path))
    assert trained.artifact_dir == tmp_path
    predict = build_parser().parse_args([
        "predict-betting-meta",
        "--strategy-config",
        str(_STRATEGY),
        "--artifact-dir",
        str(tmp_path),
        "--as-of",
        "2026-08-01"])
    assert predict.as_of == datetime(2026, 8, 1, 0, 0)
    stamped = build_parser().parse_args([
        "predict-betting-meta",
        "--strategy-config",
        str(_STRATEGY),
        "--artifact-dir",
        str(tmp_path),
        "--as-of",
        "2026-08-01T15:30:00",
        "--verbose"])
    assert stamped.as_of == datetime(2026, 8, 1, 15, 30)
    assert stamped.verbose is True


def test_parser_rejects_missing_flags_and_aware_as_of(
        tmp_path: Path) -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["build-betting-dataset"])
    with pytest.raises(SystemExit):
        parser.parse_args([
            "train-betting-meta",
            "--training-config",
            str(_TRAINING),
            "--strategy-config",
            str(_STRATEGY)])
    with pytest.raises(SystemExit):
        parser.parse_args([
            "predict-betting-meta",
            "--strategy-config",
            str(_STRATEGY),
            "--artifact-dir",
            str(tmp_path),
            "--as-of",
            "2026-08-01T12:00:00+02:00"])


def test_build_dataset_prints_the_walk_forward_manifest() -> None:
    with patch.object(
            commands,
            "finished_candidate_frame",
            return_value=_history()):
        code, payload, _raw = _run(_dataset_argv())
    assert code == 0
    result = payload["result"]
    assert result["row_count"] == 10
    assert result["match_count"] == 10
    assert [item["role"] for item in result["splits"]] == [
        "train",
        "calibration",
        "test"]
    assert len(result["feature_schema_fingerprint"]) == 64


def test_history_window_starts_at_the_epoch() -> None:
    captured: dict[str, datetime] = {}

    def _fetch(
            as_of: datetime,
            horizon: datetime,
            filters: object) -> pd.DataFrame:
        del filters
        captured["as_of"] = as_of
        captured["horizon"] = horizon
        return _history()

    before = datetime.now().replace(microsecond=0)
    strategy = load_betting_strategy_config(_STRATEGY)
    with patch.object(commands, "fetch_candidates", side_effect=_fetch), \
            patch.object(
                commands,
                "attach_settlement_columns",
                side_effect=lambda frame: frame):
        frame = commands.finished_candidate_frame(strategy)
    after = datetime.now().replace(microsecond=0)
    assert captured["as_of"] == datetime(1970, 1, 1)
    assert before <= captured["horizon"] <= after
    assert len(frame) == 10


def test_missing_finished_pairs_exit_with_code_1() -> None:
    with patch.object(
            commands,
            "finished_candidate_frame",
            return_value=_empty_frame()):
        code, payload, _raw = _run(_dataset_argv())
    assert code == 1
    assert payload["ok"] is False
    assert payload["error"] == "no finished betting candidates"


def test_bad_training_config_exits_with_code_1(tmp_path: Path) -> None:
    config = tmp_path / "bad.json"
    config.write_text('{"model_name": "X"}', encoding="utf-8")
    code, payload, _raw = _run([
        "train-betting-meta",
        "--training-config",
        str(config),
        "--strategy-config",
        str(_STRATEGY),
        "--artifact-dir",
        str(tmp_path)])
    assert code == 1
    assert payload["ok"] is False
    assert "error" in payload


def test_train_uses_the_explicit_paths(tmp_path: Path) -> None:
    seen: dict[str, object] = {}

    def _train(
            dataset: object,
            config: object,
            artifact_dir: Path,
            strategy: object = None) -> dict[str, str]:
        seen["dataset"] = dataset
        seen["config"] = config
        seen["artifact_dir"] = artifact_dir
        seen["strategy"] = strategy
        return {"model_fingerprint": "ab" * 32}

    with patch.object(
            commands,
            "finished_candidate_frame",
            return_value=_history()), \
            patch.object(commands, "train_meta_model", side_effect=_train):
        code, payload, _raw = _run(
            _artifact_argv("train-betting-meta", tmp_path))
    assert code == 0
    assert payload["result"]["model_fingerprint"] == "ab" * 32
    assert seen["artifact_dir"] == tmp_path
    assert seen["config"].model_name == "FOOTBALL_BETTING_META_V1"
    assert seen["strategy"].football_sport_name == "Piłka nożna"
    assert len(seen["dataset"].features) == 10


def test_evaluate_scores_the_test_window(tmp_path: Path) -> None:
    with patch.object(
            commands,
            "finished_candidate_frame",
            return_value=_history()), \
            patch.object(BettingMetaPredictor, "decide", _fake_decide):
        code, payload, _raw = _run(
            _artifact_argv("evaluate-betting-meta", tmp_path))
    assert code == 0
    report = payload["result"]["report"]
    assert report["bet_count"] == 0
    assert report["no_bet_count"] == 2
    assert payload["result"]["calibration_method"] is None


def test_backtest_compares_baselines_and_the_model(tmp_path: Path) -> None:
    with patch.object(
            commands,
            "finished_candidate_frame",
            return_value=_history()), \
            patch.object(BettingMetaPredictor, "decide", _fake_decide):
        code, payload, _raw = _run(
            _artifact_argv("backtest-betting-strategy", tmp_path))
    assert code == 0
    result = payload["result"]
    assert result["pair_role"] == "test"
    assert result["pair_count"] == 2
    assert set(result["baselines"]) == {
        "no_bet",
        "confidence_single",
        "positive_ev_single"}
    assert result["baselines"]["no_bet"]["bet_count"] == 0
    assert result["baselines"]["confidence_single"]["bet_count"] == 2
    assert result["meta_model"]["no_bet_count"] == 2


def test_short_history_keeps_the_baseline_report(tmp_path: Path) -> None:
    with patch.object(
            commands,
            "finished_candidate_frame",
            return_value=_history(matches=1)):
        code, payload, _raw = _run(
            _artifact_argv("backtest-betting-strategy", tmp_path))
    assert code == 0
    result = payload["result"]
    assert result["pair_role"] == "finished"
    assert result["pair_count"] == 1
    assert result["baselines"]["no_bet"]["no_bet_count"] == 1
    assert "not enough matches" in result["meta_model"]["error"]


def test_unready_artifact_exits_without_inserting(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact"
    artifact.mkdir()
    (artifact / "metrics.json").write_text(
        json.dumps({"brier": 0.9, "reliability": 0.2, "roi": -0.5}),
        encoding="utf-8")

    def _refuse(*_args: object, **_kwargs: object) -> PredictReport:
        raise AssertionError("prediction wrote rows")

    with patch.object(commands, "run_betting_predict", side_effect=_refuse):
        code, payload, _raw = _run([
            "predict-betting-meta",
            "--strategy-config",
            str(_STRATEGY),
            "--artifact-dir",
            str(artifact),
            "--as-of",
            "2026-08-01T12:00:00"])
    assert code == 1
    assert payload["ok"] is False
    assert "not ready" in str(payload["error"])
    assert "wrote no recommendations" in str(payload["error"])


def test_allow_unready_predicts_when_the_gate_fails(
        tmp_path: Path) -> None:
    artifact = tmp_path / "artifact"
    artifact.mkdir()
    (artifact / "metrics.json").write_text(
        json.dumps({"brier": 0.9, "reliability": 0.2, "roi": -0.5}),
        encoding="utf-8")
    seen: dict[str, object] = {}

    def _predict(
            artifact_dir: Path,
            as_of: datetime,
            strategy: object = None,
            require_ready: bool = True) -> PredictReport:
        seen["require_ready"] = require_ready
        seen["artifact_dir"] = artifact_dir
        seen["as_of"] = as_of
        seen["strategy"] = strategy
        return PredictReport(
            inserted_count=1,
            skipped_existing_count=0,
            rejected_count=0)

    with patch.object(commands, "run_betting_predict", side_effect=_predict):
        code, payload, _raw = _run([
            "predict-betting-meta",
            "--strategy-config",
            str(_STRATEGY),
            "--artifact-dir",
            str(artifact),
            "--as-of",
            "2026-08-01T12:00:00",
            "--allow-unready"])
    assert code == 0
    assert payload["result"]["inserted_count"] == 1
    assert seen["require_ready"] is False
    assert seen["artifact_dir"] == artifact
    assert seen["as_of"] == datetime(2026, 8, 1, 12, 0)
    assert seen["strategy"].football_sport_name == "Piłka nożna"


def test_predict_reports_inserted_and_skipped_pairs(tmp_path: Path) -> None:
    seen: dict[str, object] = {}

    def _predict(
            artifact_dir: Path,
            as_of: datetime,
            strategy: object = None,
            require_ready: bool = True) -> PredictReport:
        seen["artifact_dir"] = artifact_dir
        seen["as_of"] = as_of
        seen["strategy"] = strategy
        seen["require_ready"] = require_ready
        return PredictReport(
            inserted_count=2,
            skipped_existing_count=1,
            rejected_count=0)

    with patch.object(
            BettingMetaPredictor,
            "check_model_ready",
            return_value=True), \
            patch.object(
                commands,
                "run_betting_predict",
                side_effect=_predict):
        code, payload, _raw = _run([
            "predict-betting-meta",
            "--strategy-config",
            str(_STRATEGY),
            "--artifact-dir",
            str(tmp_path),
            "--as-of",
            "2026-08-01T12:00:00"])
    assert code == 0
    assert payload["result"]["inserted_count"] == 2
    assert payload["result"]["skipped_existing_count"] == 1
    assert payload["result"]["rejected_count"] == 0
    assert seen["artifact_dir"] == tmp_path
    assert seen["as_of"] == datetime(2026, 8, 1, 12, 0)
    assert seen["strategy"].football_sport_name == "Piłka nożna"
    assert seen["require_ready"] is True
