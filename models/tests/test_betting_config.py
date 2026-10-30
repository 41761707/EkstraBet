"""Contracts for betting candidates, decisions, and config files."""

from __future__ import annotations

import json
from datetime import datetime
from datetime import timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from models.pipeline.betting.config import load_betting_strategy_config
from models.pipeline.betting.config import load_betting_training_config
from models.pipeline.betting.domain import BettingCandidate
from models.pipeline.betting.domain import SelectionDecision


REPO_ROOT = Path(__file__).resolve().parents[2]
TRAINING_CONFIG = (
    REPO_ROOT
    / "models"
    / "configs"
    / "training"
    / "football_betting_meta_v1.json")
STRATEGY_CONFIG = (
    REPO_ROOT
    / "models"
    / "configs"
    / "prediction"
    / "football_betting_strategy_v1.json")


def _candidate(**overrides: object) -> BettingCandidate:
    payload = {
        "prediction_id": 10,
        "odds_id": 20,
        "match_id": 30,
        "event_id": 1,
        "model_id": 8,
        "bookmaker_id": 4,
        "league_id": 12,
        "kickoff": datetime(2026, 8, 1, 18, 0, tzinfo=timezone.utc),
        "value_pct": 55.0,
        "odds": 1.9
    }
    payload.update(overrides)
    return BettingCandidate(**payload)


def _training_payload() -> dict[str, object]:
    return {
        "model_name": "FOOTBALL_BETTING_META_V1",
        "algorithm": "LogisticRegression",
        "class_weight": "balanced",
        "calibration_methods": ["sigmoid", "isotonic"],
        "random_state": 42,
        "train_fraction": 0.6,
        "calibration_fraction": 0.2,
        "test_fraction": 0.2
    }


def _strategy_payload() -> dict[str, object]:
    return {
        "probability_threshold": 0.5,
        "football_sport_name": "Piłka nożna",
        "excluded_model_names": [
            "FOOTBALL_PLAYED_BETTER_V1",
            "FOOTBALL_PLAYED_BETTER_NOXG_V1"
        ],
        "max_brier": 0.25,
        "max_reliability_error": 0.05,
        "min_roi": 0.0
    }


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_repo_training_config_loads_and_round_trips() -> None:
    config = load_betting_training_config(TRAINING_CONFIG)
    restored = type(config).model_validate(config.model_dump())
    assert restored == config
    assert config.algorithm == "LogisticRegression"
    assert config.calibration_methods == ("sigmoid", "isotonic")
    assert config.train_fraction == 0.6


def test_repo_strategy_config_loads_and_round_trips() -> None:
    config = load_betting_strategy_config(STRATEGY_CONFIG)
    restored = type(config).model_validate(config.model_dump())
    assert restored == config
    assert config.probability_threshold == 0.5
    assert config.football_sport_name == "Piłka nożna"
    assert config.excluded_model_names == (
        "FOOTBALL_PLAYED_BETTER_V1",
        "FOOTBALL_PLAYED_BETTER_NOXG_V1")
    assert config.max_brier == 0.24
    assert config.max_brier < 0.25
    assert config.max_reliability_error == 0.05
    assert config.min_roi == 0.0
    assert config.min_odds == 1.5


def test_training_config_rejects_missing_field(tmp_path: Path) -> None:
    payload = _training_payload()
    del payload["test_fraction"]
    path = _write_json(tmp_path / "missing.json", payload)
    with pytest.raises(ValidationError, match="test_fraction"):
        load_betting_training_config(path)


def test_strategy_config_rejects_unknown_key(tmp_path: Path) -> None:
    payload = _strategy_payload()
    payload["stake"] = 10
    path = _write_json(tmp_path / "unknown.json", payload)
    with pytest.raises(ValidationError, match="stake"):
        load_betting_strategy_config(path)


def test_training_config_rejects_fraction_range(tmp_path: Path) -> None:
    payload = _training_payload()
    payload["train_fraction"] = 1.0
    payload["calibration_fraction"] = 0.0
    payload["test_fraction"] = 0.0
    path = _write_json(tmp_path / "range.json", payload)
    with pytest.raises(ValidationError, match="split fractions"):
        load_betting_training_config(path)


def test_training_config_rejects_fraction_sum(tmp_path: Path) -> None:
    payload = _training_payload()
    payload["train_fraction"] = 0.5
    path = _write_json(tmp_path / "sum.json", payload)
    with pytest.raises(ValidationError, match="sum to 1"):
        load_betting_training_config(path)


def test_strategy_config_rejects_threshold_above_one(tmp_path: Path) -> None:
    payload = _strategy_payload()
    payload["probability_threshold"] = 1.1
    path = _write_json(tmp_path / "threshold.json", payload)
    with pytest.raises(ValidationError, match="probability_threshold"):
        load_betting_strategy_config(path)


def test_strategy_config_rejects_brier_gate(tmp_path: Path) -> None:
    payload = _strategy_payload()
    payload["max_brier"] = 0.0
    path = _write_json(tmp_path / "brier.json", payload)
    with pytest.raises(ValidationError, match="max_brier"):
        load_betting_strategy_config(path)


def test_strategy_config_rejects_reliability_gate(
        tmp_path: Path) -> None:
    for raw in (0.0, 1.1):
        payload = _strategy_payload()
        payload["max_reliability_error"] = raw
        path = _write_json(tmp_path / f"reliability_{raw}.json", payload)
        with pytest.raises(ValidationError, match="max_reliability_error"):
            load_betting_strategy_config(path)


def test_strategy_config_rejects_nan_threshold(tmp_path: Path) -> None:
    payload = _strategy_payload()
    payload["probability_threshold"] = float("nan")
    path = _write_json(tmp_path / "nan_threshold.json", payload)
    with pytest.raises(ValidationError, match="probability_threshold"):
        load_betting_strategy_config(path)


def test_strategy_config_rejects_nan_brier(tmp_path: Path) -> None:
    payload = _strategy_payload()
    payload["max_brier"] = float("nan")
    path = _write_json(tmp_path / "nan_brier.json", payload)
    with pytest.raises(ValidationError, match="max_brier"):
        load_betting_strategy_config(path)


def test_training_config_rejects_nan_fractions(tmp_path: Path) -> None:
    for field_name in (
            "train_fraction",
            "calibration_fraction",
            "test_fraction"):
        payload = _training_payload()
        payload[field_name] = float("nan")
        path = _write_json(tmp_path / f"{field_name}.json", payload)
        with pytest.raises(ValidationError, match=field_name):
            load_betting_training_config(path)


def test_config_sequences_reject_in_place_appends() -> None:
    training = load_betting_training_config(TRAINING_CONFIG)
    strategy = load_betting_strategy_config(STRATEGY_CONFIG)
    assert isinstance(training.calibration_methods, tuple)
    assert isinstance(strategy.excluded_model_names, tuple)
    with pytest.raises(AttributeError):
        training.calibration_methods.append("sigmoid")
    with pytest.raises(AttributeError):
        strategy.excluded_model_names.append("FOOTBALL_PLAYED_BETTER_V1")


def test_strategy_config_rejects_bool_thresholds(tmp_path: Path) -> None:
    cases = (
        ("probability_threshold", False),
        ("probability_threshold", True),
        ("max_brier", True),
        ("max_reliability_error", True),
        ("min_roi", False))
    for field_name, raw in cases:
        payload = _strategy_payload()
        payload[field_name] = raw
        path = _write_json(tmp_path / f"{field_name}.json", payload)
        with pytest.raises(ValidationError, match=field_name):
            load_betting_strategy_config(path)


def test_training_config_rejects_bool_numbers(tmp_path: Path) -> None:
    fields = (
        "random_state",
        "train_fraction",
        "calibration_fraction",
        "test_fraction")
    for field_name in fields:
        payload = _training_payload()
        payload[field_name] = True
        path = _write_json(tmp_path / f"{field_name}.json", payload)
        with pytest.raises(ValidationError, match=field_name):
            load_betting_training_config(path)


def test_strategy_config_stores_stripped_names(tmp_path: Path) -> None:
    payload = _strategy_payload()
    payload["football_sport_name"] = " Piłka nożna "
    payload["excluded_model_names"] = [
        " FOOTBALL_PLAYED_BETTER_V1",
        "FOOTBALL_PLAYED_BETTER_NOXG_V1 "
    ]
    path = _write_json(tmp_path / "spaces.json", payload)
    config = load_betting_strategy_config(path)
    assert config.football_sport_name == "Piłka nożna"
    assert config.excluded_model_names == (
        "FOOTBALL_PLAYED_BETTER_V1",
        "FOOTBALL_PLAYED_BETTER_NOXG_V1")


def test_strategy_config_rejects_names_equal_after_strip(
        tmp_path: Path) -> None:
    payload = _strategy_payload()
    payload["excluded_model_names"] = [
        "FOOTBALL_PLAYED_BETTER_V1",
        " FOOTBALL_PLAYED_BETTER_V1"
    ]
    path = _write_json(tmp_path / "strip_dupes.json", payload)
    with pytest.raises(ValidationError, match="unique"):
        load_betting_strategy_config(path)


def test_strategy_config_rejects_min_roi_below_minus_one(
        tmp_path: Path) -> None:
    payload = _strategy_payload()
    payload["min_roi"] = -1.01
    path = _write_json(tmp_path / "roi.json", payload)
    with pytest.raises(ValidationError, match="min_roi"):
        load_betting_strategy_config(path)


def test_strategy_config_accepts_min_roi_at_minus_one(
        tmp_path: Path) -> None:
    payload = _strategy_payload()
    payload["min_roi"] = -1
    path = _write_json(tmp_path / "roi_floor.json", payload)
    config = load_betting_strategy_config(path)
    assert config.min_roi == -1.0


def test_strategy_config_rejects_duplicate_excluded_names(
        tmp_path: Path) -> None:
    payload = _strategy_payload()
    payload["excluded_model_names"] = [
        "FOOTBALL_PLAYED_BETTER_V1",
        "FOOTBALL_PLAYED_BETTER_V1"
    ]
    path = _write_json(tmp_path / "dupes.json", payload)
    with pytest.raises(ValidationError, match="unique"):
        load_betting_strategy_config(path)


def test_candidate_and_decision_round_trip() -> None:
    candidate = _candidate()
    decision = SelectionDecision(
        decision="bet",
        candidate=candidate,
        calibrated_probability=0.62,
        reason="above threshold")
    restored_candidate = BettingCandidate(**{
        "prediction_id": candidate.prediction_id,
        "odds_id": candidate.odds_id,
        "match_id": candidate.match_id,
        "event_id": candidate.event_id,
        "model_id": candidate.model_id,
        "bookmaker_id": candidate.bookmaker_id,
        "league_id": candidate.league_id,
        "kickoff": candidate.kickoff,
        "value_pct": candidate.value_pct,
        "odds": candidate.odds
    })
    restored = SelectionDecision(
        decision=decision.decision,
        candidate=restored_candidate,
        calibrated_probability=decision.calibrated_probability,
        reason=decision.reason)
    assert restored == decision


def test_candidate_accepts_a_missing_league() -> None:
    candidate = _candidate(league_id=None)
    assert candidate.league_id is None


def test_candidate_rejects_a_non_positive_league() -> None:
    with pytest.raises(ValueError, match="league_id"):
        _candidate(league_id=0)
    with pytest.raises(ValueError, match="league_id"):
        _candidate(league_id=True)


def test_candidate_rejects_odds_at_one() -> None:
    with pytest.raises(ValueError, match="odds"):
        _candidate(odds=1.0)


def test_candidate_rejects_value_pct_above_100() -> None:
    with pytest.raises(ValueError, match="value_pct"):
        _candidate(value_pct=100.1)


def test_decision_rejects_unknown_kind() -> None:
    with pytest.raises(ValueError, match="decision"):
        SelectionDecision(
            decision="stake",
            candidate=_candidate(),
            calibrated_probability=0.4,
            reason="not a selection")


def test_decision_rejects_probability_above_one() -> None:
    with pytest.raises(ValueError, match="calibrated_probability"):
        SelectionDecision(
            decision="no_bet",
            candidate=_candidate(),
            calibrated_probability=1.01,
            reason="out of range")


def test_decision_has_no_stake_field() -> None:
    decision = SelectionDecision(
        decision="no_bet",
        candidate=_candidate(),
        calibrated_probability=0.4,
        reason="below threshold")
    assert not hasattr(decision, "stake")
