"""Inference: calibrated probability, threshold, and the report gate."""

from __future__ import annotations

import inspect
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from models.pipeline.betting import predictor as predictor_module
from models.pipeline.betting.config import BettingStrategyConfig
from models.pipeline.betting.config import BettingTrainingConfig
from models.pipeline.betting.dataset_builder import BettingDataset
from models.pipeline.betting.domain import BettingCandidate
from models.pipeline.betting.features import FEATURE_COLUMNS
from models.pipeline.betting.features import NUMERIC_FEATURE_COLUMNS
from models.pipeline.betting.predictor import BettingMetaPredictor
from models.pipeline.betting.predictor import ScoredCandidate
from models.pipeline.betting.predictor import score_candidates
from models.pipeline.betting.predictor import select_candidates
from models.pipeline.betting.trainer import train_meta_model


_WRITE_WORDS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "REPLACE",
    "to_sql",
    "get_db_connection",
    "betting_recommendations")
_ARTIFACT_FILES = (
    "model.joblib",
    "feature_columns.json",
    "metrics.json",
    "meta.json")


def _strategy(**overrides: object) -> BettingStrategyConfig:
    payload: dict[str, object] = {
        "probability_threshold": 0.5,
        "football_sport_name": "Piłka nożna",
        "excluded_model_names": (
            "FOOTBALL_PLAYED_BETTER_V1",
            "FOOTBALL_PLAYED_BETTER_NOXG_V1"),
        "max_brier": 0.24,
        "max_reliability_error": 0.05,
        "min_roi": 0.0}
    payload.update(overrides)
    return BettingStrategyConfig(**payload)


def _training_config() -> BettingTrainingConfig:
    return BettingTrainingConfig(
        model_name="FOOTBALL_BETTING_META_V1",
        algorithm="LogisticRegression",
        class_weight="balanced",
        calibration_methods=("sigmoid",),
        random_state=42,
        train_fraction=0.6,
        calibration_fraction=0.2,
        test_fraction=0.2)


def _candidate(**overrides: object) -> BettingCandidate:
    payload: dict[str, object] = {
        "prediction_id": 10,
        "odds_id": 20,
        "match_id": 30,
        "event_id": 1,
        "model_id": 8,
        "bookmaker_id": 4,
        "league_id": 12,
        "kickoff": datetime(2026, 8, 1, 18, 0),
        "value_pct": 55.0,
        "odds": 1.9}
    payload.update(overrides)
    return BettingCandidate(**payload)


def _scored(probability: float, **overrides: object) -> ScoredCandidate:
    return ScoredCandidate(
        candidate=_candidate(**overrides),
        calibrated_probability=probability)


def _row(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "prediction_id": 10,
        "odds_id": 20,
        "match_id": 30,
        "event_id": 1,
        "model_id": 8,
        "bookmaker_id": 4,
        "league_id": 1,
        "kickoff": datetime(2026, 8, 1, 18, 30),
        "value_pct": 62.0,
        "odds": 1.9,
        "devig_probability": 0.5}
    payload.update(overrides)
    return payload


def _frame(*rows: dict[str, object]) -> pd.DataFrame:
    return pd.DataFrame(list(rows))


def _copy_artifact(source: Path, destination: Path) -> None:
    for name in _ARTIFACT_FILES:
        (destination / name).write_bytes((source / name).read_bytes())


def _write_metrics(directory: Path, **values: object) -> None:
    payload = {
        "brier": values["brier"],
        "reliability": values["reliability"],
        "roi": values["roi"]}
    (directory / "metrics.json").write_text(
        json.dumps(payload),
        encoding="utf-8")


def _default_label(match_id: int) -> int:
    return match_id % 2


def _default_league(match_id: int) -> object:
    if match_id == 1:
        return None
    return str((match_id % 3) + 1)


def _default_market(match_id: int) -> str:
    if match_id % 2 == 0:
        return "BTTS"
    return "REZULTAT"


def _dataset(count: int = 15) -> BettingDataset:
    """Return a finished dataset with one row per match."""
    rows: list[dict[str, object]] = []
    labels: list[int] = []
    for match_id in range(1, count + 1):
        label = _default_label(match_id)
        probability = 0.8 if label == 1 else 0.25
        rows.append({
            "model_probability": probability,
            "implied_probability": 0.5,
            "devig_probability": float("nan"),
            "edge": probability - 0.5,
            "ev": probability * 2.0 - 1.0,
            "kickoff_weekday_sin": 0.0,
            "kickoff_weekday_cos": 1.0,
            "kickoff_hour_sin": 0.0,
            "kickoff_hour_cos": 1.0,
            "model_id": "8",
            "market_family": _default_market(match_id),
            "league_id": _default_league(match_id)})
        labels.append(label)
    features = pd.DataFrame(rows).loc[:, list(FEATURE_COLUMNS)]
    for name in NUMERIC_FEATURE_COLUMNS:
        features[name] = features[name].astype("float64")
    index = features.index
    return BettingDataset(
        features=features,
        labels=pd.Series(labels, index=index, dtype="int64", name="label"),
        prediction_id=_ids(count, 1, index, "prediction_id"),
        odds_id=_ids(count, 1000, index, "odds_id"),
        match_id=_ids(count, 1, index, "match_id"),
        kickoff=_kickoffs(count, index),
        odds=pd.Series(
            [2.0] * count,
            index=index,
            dtype="float64",
            name="odds"))


def _ids(
        count: int,
        start: int,
        index: pd.Index,
        name: str) -> pd.Series:
    values = [start + offset for offset in range(count)]
    return pd.Series(values, index=index, dtype="int64", name=name)


def _kickoffs(count: int, index: pd.Index) -> pd.Series:
    values = [
        datetime(2026, 1, match_id, 18, 0)
        for match_id in range(1, count + 1)]
    return pd.Series(values, index=index, dtype="object", name="kickoff")


@pytest.fixture(scope="module")
def artifact_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    directory = tmp_path_factory.mktemp("betting-meta")
    train_meta_model(
        _dataset(),
        _training_config(),
        directory,
        strategy=_strategy())
    return directory


def test_batch_keeps_input_order_and_drops_invalid_rows(
        artifact_dir: Path) -> None:
    frame = _frame(
        _row(
            prediction_id=3,
            odds_id=30,
            match_id=7,
            value_pct=70.0,
            odds=1.8),
        _row(prediction_id=1, odds_id=10, match_id=7, odds=1.0),
        _row(
            prediction_id=2,
            odds_id=20,
            match_id=8,
            league_id=99999,
            event_id=6,
            value_pct=55.0,
            odds=2.2),
        _row(
            prediction_id=4,
            odds_id=40,
            match_id=9,
            value_pct=120.0),
        _row(
            prediction_id=5,
            odds_id=50,
            match_id=9,
            league_id=None,
            value_pct=48.0,
            odds=1.7))
    scored = score_candidates(frame, artifact_dir)
    assert [item.candidate.prediction_id for item in scored] == [3, 2, 5]
    assert scored[0].candidate.value_pct == 70.0
    assert scored[0].candidate.odds == 1.8
    assert scored[1].candidate.league_id == 99999
    assert scored[2].candidate.league_id is None
    assert scored[1].candidate.event_id == 6


def test_unknown_league_still_scores(artifact_dir: Path) -> None:
    frame = _frame(_row(
        league_id=424242,
        prediction_id=77,
        odds_id=88))
    scored = score_candidates(frame, artifact_dir)
    assert len(scored) == 1
    assert scored[0].candidate.league_id == 424242
    probability = scored[0].calibrated_probability
    assert 0.0 <= probability <= 1.0


def test_probabilities_stay_inside_the_unit_interval(
        artifact_dir: Path) -> None:
    frame = _frame(
        _row(prediction_id=1, odds_id=1, value_pct=0.0, odds=1.01),
        _row(prediction_id=2, odds_id=2, value_pct=100.0, odds=15.0),
        _row(prediction_id=3, odds_id=3, league_id=424242))
    scored = score_candidates(frame, artifact_dir)
    assert len(scored) == 3
    for item in scored:
        assert 0.0 <= item.calibrated_probability <= 1.0


def test_repeated_scoring_is_deterministic(artifact_dir: Path) -> None:
    frame = _frame(
        _row(prediction_id=3, odds_id=30, match_id=7),
        _row(
            prediction_id=2,
            odds_id=20,
            match_id=8,
            league_id=99999,
            event_id=6))
    assert score_candidates(frame, artifact_dir) == score_candidates(
        frame,
        artifact_dir)


def test_decide_matches_score_and_select(artifact_dir: Path) -> None:
    frame = _frame(
        _row(),
        _row(prediction_id=11, odds_id=21, match_id=31))
    strategy = _strategy(probability_threshold=0.5)
    predictor = BettingMetaPredictor(artifact_dir, strategy)
    assert predictor.decide(frame) == select_candidates(
        score_candidates(frame, artifact_dir),
        strategy)


def test_missing_feature_column_raises(
        artifact_dir: Path,
        tmp_path: Path) -> None:
    _copy_artifact(artifact_dir, tmp_path)
    path = tmp_path / "feature_columns.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    names = list(payload["feature_columns"])
    names.append("season_id")
    payload["feature_columns"] = names
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="missing feature column: season_id"):
        score_candidates(_frame(_row()), tmp_path)


def test_missing_source_column_raises() -> None:
    frame = _frame(_row()).drop(columns=["devig_probability"])
    with pytest.raises(ValueError, match="devig_probability"):
        score_candidates(frame, Path("missing"))


def test_column_fingerprint_mismatch_raises(
        artifact_dir: Path,
        tmp_path: Path) -> None:
    _copy_artifact(artifact_dir, tmp_path)
    path = tmp_path / "meta.json"
    meta = json.loads(path.read_text(encoding="utf-8"))
    meta["feature_schema_fingerprint"] = "ab" * 32
    path.write_text(json.dumps(meta), encoding="utf-8")
    with pytest.raises(ValueError, match="fingerprint"):
        score_candidates(_frame(_row()), tmp_path)


def test_fingerprint_is_checked_when_no_row_remains(
        artifact_dir: Path,
        tmp_path: Path) -> None:
    _copy_artifact(artifact_dir, tmp_path)
    path = tmp_path / "meta.json"
    meta = json.loads(path.read_text(encoding="utf-8"))
    meta["feature_schema_fingerprint"] = "cd" * 32
    path.write_text(json.dumps(meta), encoding="utf-8")
    with pytest.raises(ValueError, match="fingerprint"):
        score_candidates(_frame(_row(odds=1.0)), tmp_path)


def test_model_file_fingerprint_mismatch_raises(
        artifact_dir: Path,
        tmp_path: Path) -> None:
    _copy_artifact(artifact_dir, tmp_path)
    model_path = tmp_path / "model.joblib"
    model_path.write_bytes(model_path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="model file fingerprint"):
        score_candidates(_frame(_row()), tmp_path)


def test_invalid_rows_only_return_no_scores(artifact_dir: Path) -> None:
    frame = _frame(
        _row(odds=1.0),
        _row(prediction_id=11, odds_id=11, value_pct=140.0))
    assert score_candidates(frame, artifact_dir) == []


def test_empty_frame_returns_no_scores(artifact_dir: Path) -> None:
    frame = _frame(_row()).iloc[0:0]
    assert score_candidates(frame, artifact_dir) == []


def test_duplicate_index_raises() -> None:
    frame = _frame(_row(), _row(prediction_id=11, odds_id=21))
    frame.index = [0, 0]
    with pytest.raises(ValueError, match="candidate index must be unique"):
        score_candidates(frame, Path("missing"))


def test_candidates_must_be_a_frame() -> None:
    with pytest.raises(ValueError, match="DataFrame"):
        score_candidates((), Path("missing"))  # type: ignore[arg-type]


def test_threshold_marks_bet_only_strictly_above() -> None:
    scored = (
        _scored(0.5, prediction_id=1, odds_id=1, value_pct=90.0),
        _scored(0.51, prediction_id=2, odds_id=2, value_pct=10.0),
        _scored(1.0, prediction_id=3, odds_id=3),
        _scored(0.0, prediction_id=4, odds_id=4))
    decisions = select_candidates(
        scored,
        _strategy(probability_threshold=0.5))
    assert [item.decision for item in decisions] == [
        "no_bet",
        "bet",
        "bet",
        "no_bet"]
    assert decisions[0].calibrated_probability == 0.5
    assert decisions[0].candidate.value_pct == 90.0
    assert decisions[0].reason == (
        "calibrated probability at or below threshold")
    assert decisions[1].reason == "calibrated probability above threshold"
    ceiling = select_candidates(
        (_scored(1.0, prediction_id=5, odds_id=5),),
        _strategy(probability_threshold=1.0))
    assert ceiling[0].decision == "no_bet"
    floor = select_candidates(
        (_scored(0.0, prediction_id=6, odds_id=6),),
        _strategy(probability_threshold=0.0))
    assert floor[0].decision == "no_bet"


def test_selection_does_not_fold_a_match_into_a_coupon() -> None:
    decisions = select_candidates(
        (
            _scored(0.8, prediction_id=1, odds_id=1),
            _scored(0.9, prediction_id=2, odds_id=2)),
        _strategy(probability_threshold=0.5))
    assert [item.decision for item in decisions] == ["bet", "bet"]
    assert decisions[0].candidate.match_id == decisions[1].candidate.match_id
    for decision in decisions:
        assert not hasattr(decision, "stake")


def test_empty_scored_sequence_returns_no_decisions() -> None:
    assert select_candidates((), _strategy()) == []


def test_select_rejects_a_bare_candidate() -> None:
    with pytest.raises(ValueError, match="ScoredCandidate"):
        select_candidates(
            (_candidate(),),  # type: ignore[arg-type]
            _strategy())


def test_score_outside_the_unit_interval_is_rejected() -> None:
    _scored(0.0)
    _scored(1.0)
    with pytest.raises(ValueError, match="between 0 and 1"):
        _scored(1.01)
    with pytest.raises(ValueError, match="between 0 and 1"):
        _scored(float("nan"))
    with pytest.raises(ValueError, match="between 0 and 1"):
        ScoredCandidate(
            candidate=_candidate(),
            calibrated_probability=True)  # type: ignore[arg-type]


def test_report_at_the_caps_is_ready(tmp_path: Path) -> None:
    _write_metrics(tmp_path, brier=0.24, reliability=0.05, roi=0.0)
    assert BettingMetaPredictor(tmp_path, _strategy()).check_model_ready()


def test_report_outside_a_cap_is_not_ready(tmp_path: Path) -> None:
    predictor = BettingMetaPredictor(tmp_path, _strategy())
    assert predictor.check_model_ready() is False
    cases = (
        {"brier": 0.25, "reliability": 0.05, "roi": 0.0},
        {"brier": 0.24, "reliability": 0.06, "roi": 0.0},
        {"brier": 0.24, "reliability": 0.05, "roi": -0.01},
        {"brier": 0.24, "reliability": 0.05, "roi": None},
        {"brier": "0.2", "reliability": 0.05, "roi": 0.0})
    for case in cases:
        _write_metrics(tmp_path, **case)
        assert predictor.check_model_ready() is False


def test_total_loss_meets_a_floor_of_minus_one(tmp_path: Path) -> None:
    _write_metrics(tmp_path, brier=0.2, reliability=0.01, roi=-1.0)
    strategy = _strategy(min_roi=-1.0)
    assert BettingMetaPredictor(tmp_path, strategy).check_model_ready()


def test_roi_below_minus_one_is_not_ready(tmp_path: Path) -> None:
    _write_metrics(tmp_path, brier=0.2, reliability=0.01, roi=-1.01)
    strategy = _strategy(min_roi=-1.0)
    ready = BettingMetaPredictor(tmp_path, strategy).check_model_ready()
    assert ready is False


def test_failed_gate_still_returns_decisions(
        artifact_dir: Path,
        tmp_path: Path) -> None:
    _copy_artifact(artifact_dir, tmp_path)
    _write_metrics(tmp_path, brier=0.9, reliability=0.9, roi=-1.0)
    predictor = BettingMetaPredictor(tmp_path, _strategy())
    assert predictor.check_model_ready() is False
    decisions = predictor.decide(_frame(_row()))
    assert len(decisions) == 1
    assert decisions[0].decision in ("bet", "no_bet")


def test_predictor_rejects_a_foreign_strategy() -> None:
    with pytest.raises(ValueError, match="BettingStrategyConfig"):
        BettingMetaPredictor(Path("."), object())  # type: ignore[arg-type]


def test_predictor_does_not_touch_the_database() -> None:
    source = inspect.getsource(predictor_module)
    for word in _WRITE_WORDS:
        assert word not in source
    assert ".fit(" not in source
